import yfinance as yf
import pandas as pd
import streamlit as st

def descargar_datos(ticker, inicio, fin, interval='1wk'):
    try:
        datos = yf.download(ticker, start=inicio, end=fin, interval=interval, progress=False)
        
        if datos.empty:
            return None

        # Si yfinance devuelve columnas dobles, nos quedamos solo con el nombre del indicador
        if isinstance(datos.columns, pd.MultiIndex):
            datos.columns = datos.columns.get_level_values(0)
        # -------------------------------------------------------
        
        # Validar que ahora sí existen las columnas
        columnas_necesarias = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in datos.columns for col in columnas_necesarias):
            return None
            
        return datos
    except Exception as e:
        print(f"Error técnico en la descarga: {e}")
        return None
    

def preparar_datos_semanales(df):
    if df is None:
        return None
    # Tu lógica actual de resampling...
    return df.resample('W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
