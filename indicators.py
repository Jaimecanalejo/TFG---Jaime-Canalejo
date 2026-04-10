import pandas as pd
import ta
import yfinance as yf

def calcular_indicadores_individuales(df_semanal):
    """Calcula SMA y RSI para el activo."""
    # Media Móvil de 30 semanas (Weinstein)
    df_semanal['SMA_30'] = ta.trend.sma_indicator(df_semanal['Close'], window=30)
    # RSI de 14 semanas (Murphy)
    df_semanal['RSI'] = ta.momentum.rsi(df_semanal['Close'], window=14)
    return df_semanal

def calcular_fuerza_relativa(df_accion, df_mercado):
    """Calcula el Mansfield comparando con el S&P 500."""
    ratio = df_accion['Close'] / df_mercado['Close']
    media_ratio = ratio.rolling(window=52).mean()
    fuerza_relativa = ((ratio / media_ratio) - 1) * 10
    return fuerza_relativa
if __name__ == "__main__":
    from data_loader import descargar_datos, preparar_datos_semanales
    
    # 1. Descargamos la Acción y el Mercado
    df_aapl_diario = descargar_datos("AAPL", "2023-01-01", "2025-01-01")
    df_sp500_diario = descargar_datos("^GSPC", "2023-01-01", "2025-01-01")
    
    if df_aapl_diario is not None and df_sp500_diario is not None:
        # 2. Pasamos ambos a semanal
        aapl_sem = preparar_datos_semanales(df_aapl_diario)
        sp500_sem = preparar_datos_semanales(df_sp500_diario)
        
        # 3. Calculamos SMA y RSI que ya teníamos
        import ta # Asegurar import
        aapl_sem['SMA_30'] = ta.trend.sma_indicator(aapl_sem['Close'], window=30)
        aapl_sem['RSI'] = ta.momentum.rsi(aapl_sem['Close'], window=14)
        
        # 4. NUEVO: Fuerza Relativa de Mansfield
        aapl_sem['Mansfield'] = calcular_fuerza_relativa(aapl_sem, sp500_sem)
        
        print("\n--- Fase III.b Completa: Indicadores Finales ---")
        print(aapl_sem[['Close', 'SMA_30', 'RSI', 'Mansfield']].tail())