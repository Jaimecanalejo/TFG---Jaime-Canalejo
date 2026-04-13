import pandas as pd
import ta
import yfinance as yf

def calcular_indicadores_individuales(df, periodo_sma=30): # Añadimos el parámetro con valor por defecto 30
    df = df.copy()
    # SMA dinámica
    df['SMA_30'] = df['Close'].rolling(window=periodo_sma).mean()
    
    # RSI (se suele mantener en 14, pero la SMA es la que define la etapa)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

def calcular_fuerza_relativa(df_accion, df_mercado):
    """Calcula el Mansfield comparando con el S&P 500."""
    ratio = df_accion['Close'] / df_mercado['Close']
    media_ratio = ratio.rolling(window=52).mean()
    fuerza_relativa = ((ratio / media_ratio) - 1) * 10
    return fuerza_relativa
