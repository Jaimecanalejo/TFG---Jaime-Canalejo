import pandas as pd
import numpy as np

def ejecutar_backtest_desde_df(df):
    """
    Backtesting avanzado con métricas de riesgo y serie temporal de beneficios.
    """
    df = df.copy()
    # Señal: Etapa 2 (Weinstein puro)
    df['Signal'] = ((df['Close'] > df['SMA_30']) & (df['Mansfield'] > 0)).astype(int)
    df['Posicion'] = df['Signal'].diff()

    rendimientos = []
    # Para la curva de equidad: empezamos con base 1 (100%)
    equity_curve = [1.0]
    fechas_equity = [df.index[0]]
    
    precio_entrada = 0
    en_operacion = False
    capital_acumulado = 1.0

    for i in range(1, len(df)):
        # Lógica de trades
        if df['Posicion'].iloc[i] == 1 and not en_operacion:
            precio_entrada = df['Close'].iloc[i]
            en_operacion = True
        elif df['Posicion'].iloc[i] == -1 and en_operacion:
            rentabilidad = (df['Close'].iloc[i] - precio_entrada) / precio_entrada
            rendimientos.append(rentabilidad)
            capital_acumulado *= (1 + rentabilidad)
            en_operacion = False
        
        # Guardar estado para el gráfico de rentabilidad
        equity_curve.append(capital_acumulado)
        fechas_equity.append(df.index[i])

    # Estadísticas básicas
    num_ops = len(rendimientos)
    total_ret = (capital_acumulado - 1) * 100
    win_rate = (len([r for r in rendimientos if r > 0]) / num_ops * 100) if num_ops > 0 else 0
    
    # --- CÁLCULO DEL MAX DRAWDOWN ---
    # Es la caída más grande desde un máximo previo
    equity_series = pd.Series(equity_curve)
    roll_max = equity_series.cummax()
    drawdowns = (equity_series - roll_max) / roll_max
    max_drawdown = drawdowns.min() * 100

    # Rentabilidad Buy & Hold
    bh_ret = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100

    return {
        "num_ops": num_ops,
        "win_rate": win_rate,
        "total_ret": total_ret,
        "bh_ret": bh_ret,
        "max_drawdown": max_drawdown,
        "equity_df": pd.DataFrame({'Fecha': fechas_equity, 'Equity': equity_curve})
    }
