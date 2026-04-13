import pandas as pd
from data_loader import descargar_datos
from indicators import calcular_indicadores_individuales, calcular_fuerza_relativa

def ejecutar_escaneo(lista_tickers, periodo_sma):
    """Analiza una lista de tickers y devuelve un resumen de sus etapas."""
    resultados = []
    
    # Descargamos el SP500 como referencia una sola vez para ahorrar tiempo
    df_mkt = descargar_datos("^GSPC", "2023-01-01", "2026-01-01", interval="1wk")
    
    for ticker in lista_tickers:
        try:
            df_raw = descargar_datos(ticker, "2023-01-01", "2026-01-01", interval="1wk")
            if df_raw is not None and not df_raw.empty:
                df = calcular_indicadores_individuales(df_raw, periodo_sma=periodo_sma)
                df['Mansfield'] = calcular_fuerza_relativa(df, df_mkt)
                
                ultima = df.iloc[-1]
                ant = df.iloc[-2]
                
                # Lógica de clasificación rápida
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
                    "RSI": round(ultima['RSI'], 2)
                })
        except:
            continue
            
    return pd.DataFrame(resultados)
