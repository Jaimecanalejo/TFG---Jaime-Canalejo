import pandas as pd
from data_loader import descargar_datos
from indicators import calcular_indicadores_individuales, calcular_fuerza_relativa

# Umbral de volatilidad anualizada mínima para considerar un activo apto para la estrategia Weinstein.
# Derivado empíricamente: activos con Vol >= 30% son líderes de alta beta (NVDA, META, AMD...),
# mientras que activos defensivos (AAPL, PEP, JNJ, WMT) tienen Vol < 28% consistentemente.
UMBRAL_VOL_ANUAL = 30.0

def ejecutar_escaneo(lista_tickers, periodo_sma, inicio=None, fin=None):
    """
    Analiza una lista de tickers y devuelve un resumen de sus etapas actuales.
    
    Además de la Etapa de Weinstein, calcula la volatilidad anualizada de cada activo,
    que actúa como proxy de la beta y permite descartar automáticamente activos defensivos
    (baja volatilidad) que generan falsas señales con la SMA30 (efecto whipsaw).
    
    Returns:
        DataFrame con columnas: Ticker, Precio, Etapa Actual, Mansfield, RSI, Vol.Anual%
    """
    resultados = []
    
    # Fechas por defecto: últimos 3 años para calcular volatilidad representativa
    if inicio is None:
        import datetime
        fin_dt = datetime.date.today()
        inicio_dt = fin_dt.replace(year=fin_dt.year - 3)
        inicio = str(inicio_dt)
        fin = str(fin_dt)
    
    # Descargamos el SP500 como referencia una sola vez para ahorrar tiempo
    df_mkt = descargar_datos("^GSPC", inicio, fin, interval="1wk")
    
    for ticker in lista_tickers:
        try:
            df_raw = descargar_datos(ticker, inicio, fin, interval="1wk")
            if df_raw is not None and not df_raw.empty and len(df_raw) >= 30:
                df = calcular_indicadores_individuales(df_raw, periodo_sma=periodo_sma)
                df['Mansfield'] = calcular_fuerza_relativa(df, df_mkt)
                
                ultima = df.iloc[-1]
                ant = df.iloc[-2]
                
                # Volatilidad anualizada (proxy de beta): std semanal * sqrt(52)
                vol_anual = df['Close'].pct_change().std() * (52 ** 0.5) * 100
                
                # Lógica de clasificación rápida de Etapa Weinstein
                etapa = "Indeterminada"
                if ultima['Close'] > ultima['SMA_30'] and ultima['SMA_30'] > ant['SMA_30'] and ultima['Mansfield'] > 0:
                    etapa = "Etapa 2 (Alcista)"
                elif ultima['Close'] < ultima['SMA_30'] and ultima['SMA_30'] < ant['SMA_30'] and ultima['Mansfield'] < 0:
                    etapa = "Etapa 4 (Bajista)"
                elif ultima['Close'] > ultima['SMA_30']:
                    etapa = "Etapa 1 (Suelo)"
                else:
                    etapa = "Etapa 3 (Techo)"
                
                resultados.append({
                    "Ticker": ticker,
                    "Precio": round(ultima['Close'], 2),
                    "Etapa Actual": etapa,
                    "Mansfield": round(ultima['Mansfield'], 2),
                    "RSI": round(ultima['RSI'], 2),
                    "Vol.Anual%": round(vol_anual, 1),
                })
        except:
            continue
            
    return pd.DataFrame(resultados)


def filtrar_candidatos_alta_beta(df_scan, min_vol=25.0):
    """
    Aplica el filtro cuantitativo para descartar activos defensivos.
    
    Filtra activos con volatilidad anualizada < 25% (defensivos como PEP, JNJ, WMT),
    reteniendo un universo robusto de activos de alta beta / crecimiento (NVDA, META, AMD, etc.)
    para que el optimizador de cartera evalúe su histórico y seleccione el Top N exacto.
    """
    if df_scan.empty:
        return []
    
    df_filtrado = df_scan[df_scan["Vol.Anual%"] >= min_vol]
    
    if len(df_filtrado) >= 5:
        return df_filtrado["Ticker"].tolist()
    else:
        # Fallback ordenado por volatilidad si hay pocos activos sobre el umbral
        return df_scan.sort_values(by="Vol.Anual%", ascending=False)["Ticker"].tolist()