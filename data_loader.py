import os
import yfinance as yf
import pandas as pd
import streamlit as st

CACHE_DIR = "data_cache"

def _ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def _get_cache_filepath(ticker, interval):
    _ensure_cache_dir()
    clean_ticker = ticker.strip().upper().replace("^", "INDEX_").replace("/", "_")
    return os.path.join(CACHE_DIR, f"{clean_ticker}_{interval}.csv")

def _cargar_desde_disco(ticker, interval):
    filepath = _get_cache_filepath(ticker, interval)
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            if not df.empty and all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume']):
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                else:
                    df.index = pd.to_datetime(df.index)
                return df
        except Exception as e:
            print(f"Aviso al leer caché de disco para {ticker}: {e}")
    return None

def _guardar_en_disco(ticker, interval, df):
    if df is None or df.empty:
        return
    try:
        filepath = _get_cache_filepath(ticker, interval)
        df_to_save = df.copy()
        if df_to_save.index.tz is not None:
            df_to_save.index = df_to_save.index.tz_localize(None)
        df_to_save = df_to_save[~df_to_save.index.duplicated(keep='last')]
        df_to_save.sort_index(inplace=True)
        df_to_save.to_csv(filepath)
    except Exception as e:
        print(f"Aviso al guardar en caché de disco para {ticker}: {e}")

def _descargar_de_yfinance(ticker, inicio, fin, interval):
    try:
        datos = yf.download(ticker, start=inicio, end=fin, interval=interval, progress=False)
        if datos.empty:
            return None

        if isinstance(datos.columns, pd.MultiIndex):
            datos.columns = datos.columns.get_level_values(0)

        columnas_necesarias = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in datos.columns for col in columnas_necesarias):
            return None

        if datos.index.tz is not None:
            datos.index = datos.index.tz_localize(None)

        return datos[columnas_necesarias]
    except Exception as e:
        print(f"Error descargando {ticker} de yfinance: {e}")
        return None

@st.cache_data(ttl=300)
def descargar_datos(ticker, inicio, fin, interval='1wk'):
    """
    Descarga y gestiona en caché persistente (disco) los datos de mercado de un activo.
    Solo descarga de Yahoo Finance el tramo de fechas nuevo o faltante para optimizar velocidad.
    """
    try:
        ticker_clean = ticker.strip().upper()
        
        inicio_dt = pd.to_datetime(inicio).tz_localize(None)
        fin_dt = pd.to_datetime(fin).tz_localize(None)
        hoy_dt = pd.Timestamp.now().tz_localize(None)

        # 1. Intentar cargar desde almacenamiento en disco
        df_cache = _cargar_desde_disco(ticker_clean, interval)

        if df_cache is not None and not df_cache.empty:
            cache_min = df_cache.index.min().tz_localize(None)
            cache_max = df_cache.index.max().tz_localize(None)

            necesita_historia_antigua = inicio_dt < (cache_min - pd.Timedelta(days=5))
            
            dias_diferencia = (fin_dt - cache_max).days if fin_dt <= hoy_dt else (hoy_dt - cache_max).days
            umbral_dias = 7 if interval == "1wk" else 1
            necesita_actualizacion_reciente = dias_diferencia > umbral_dias

            # Si la caché de disco ya cubre todo el rango pedido y está al día
            if not necesita_historia_antigua and not necesita_actualizacion_reciente:
                df_filtrado = df_cache.loc[(df_cache.index >= inicio_dt) & (df_cache.index <= fin_dt + pd.Timedelta(days=1))]
                if not df_filtrado.empty:
                    return df_filtrado

            # Si se requiere actualizar o ampliar rango, realizar descargas incrementales
            nuevos_dfs = [df_cache]

            # A) Descarga de datos antiguos si faltan
            if necesita_historia_antigua:
                inicio_descarga_ant = inicio_dt.strftime('%Y-%m-%d')
                fin_descarga_ant = (cache_min + pd.Timedelta(days=3)).strftime('%Y-%m-%d')
                df_ant = _descargar_de_yfinance(ticker_clean, inicio_descarga_ant, fin_descarga_ant, interval)
                if df_ant is not None and not df_ant.empty:
                    nuevos_dfs.append(df_ant)

            # B) Descarga incremental de los datos más recientes
            if necesita_actualizacion_reciente:
                inicio_descarga_rec = (cache_max - pd.Timedelta(days=5)).strftime('%Y-%m-%d')
                fin_descarga_rec = (fin_dt + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                df_rec = _descargar_de_yfinance(ticker_clean, inicio_descarga_rec, fin_descarga_rec, interval)
                if df_rec is not None and not df_rec.empty:
                    nuevos_dfs.append(df_rec)

            df_combined = pd.concat(nuevos_dfs)
            if df_combined.index.tz is not None:
                df_combined.index = df_combined.index.tz_localize(None)
            df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
            df_combined.sort_index(inplace=True)

            _guardar_en_disco(ticker_clean, interval, df_combined)

            df_final = df_combined.loc[(df_combined.index >= inicio_dt) & (df_combined.index <= fin_dt + pd.Timedelta(days=1))]
            return df_final if not df_final.empty else df_combined

        # 2. Si no hay nada en disco, descargar todo de yfinance
        df_descargado = _descargar_de_yfinance(ticker_clean, inicio, fin, interval)
        if df_descargado is not None and not df_descargado.empty:
            _guardar_en_disco(ticker_clean, interval, df_descargado)
            return df_descargado

        return None
    except Exception as e:
        print(f"Error en la descarga/gestión de caché para {ticker}: {e}")
        df_rescatado = _cargar_desde_disco(ticker, interval)
        if df_rescatado is not None:
            return df_rescatado
        return None

def preparar_datos_semanales(df):
    if df is None:
        return None
    return df.resample('W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})