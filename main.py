from data_loader import descargar_datos, preparar_datos_semanales
from indicators import calcular_indicadores_individuales, calcular_fuerza_relativa
import pandas as pd

def clasificar_historico(df):
    """Procesa el dataframe para asignar etapas a cada semana."""
    df = df.copy()
    df['Etapa'] = "Indeterminado"
    for i in range(1, len(df)):
        act, ant = df.iloc[i], df.iloc[i-1]
        # Lógica de Clasificación de Weinstein
        if act['Close'] > act['SMA_30'] and act['SMA_30'] > ant['SMA_30'] and act['Mansfield'] > 0:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 2 (Alcista)"
        elif act['Close'] < act['SMA_30'] and act['SMA_30'] < ant['SMA_30'] and act['Mansfield'] < 0:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 4 (Bajista)"
        elif act['Close'] > act['SMA_30']:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 1 (Suelo)"
        else:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 3 (Techo)"
    return df

def ejecutar_analisis(ticker):
    # 1. Ingesta y Procesamiento
    df_raw = descargar_datos(ticker, "2023-01-01", "2026-01-01")
    df_mkt_raw = descargar_datos("^GSPC", "2023-01-01", "2026-01-01")
    
    if df_raw is None or df_mkt_raw is None: return

    df = preparar_datos_semanales(df_raw)
    df_mkt = preparar_datos_semanales(df_mkt_raw)
    df = calcular_indicadores_individuales(df)
    df['Mansfield'] = calcular_fuerza_relativa(df, df_mkt)
    
    # 2. Clasificación y Validación Histórica
    df = clasificar_historico(df)
    ultima = df.iloc[-1]
    
    # Cálculo de permanencia en la etapa actual
    cambios = df[df['Etapa'] != df['Etapa'].shift(1)]
    ultima_fecha_cambio = cambios.index[-1]
    semanas_en_etapa = len(df[df.index >= ultima_fecha_cambio])
    
    # 3. REPORTE EJECUTIVO INTEGRADO
    print(f"\n" + "╔" + "═"*48 + "╗")
    print(f"║ ANALISIS ESTRATÉGICO: {ticker:<24} ")
    print("╠" + "═"*48 + "╣")
    print(f"║ > PRECIO ACTUAL:  {ultima['Close']:>10.2f}                   ")
    print(f"║ > MEDIA 30 SEM:   {ultima['SMA_30']:>10.2f}                   ")
    print(f"║ > MANSFIELD:      {ultima['Mansfield']:>10.2f}                   ")
    print(f"║ > ESTADO ACTUAL:  {ultima['Etapa']:<26} ")
    print(f"║ > PERMANENCIA:    {semanas_en_etapa:>3} semanas (Desde {ultima_fecha_cambio.date()}) ")
    print("╠" + "═"*48 + "╣")
    print("║ RESUMEN HISTÓRICO (Semanas por Etapa):         ")
    resumen = df['Etapa'].value_counts()
    for etapa, count in resumen.items():
        if etapa != "Indeterminado":
            print(f"║   - {etapa:<20} : {count:>3} semanas      ")
    print("╚" + "═"*48 + "╝\n")

if __name__ == "__main__":
    t = input("Ticker a analizar: ").upper()
    ejecutar_analisis(t)
