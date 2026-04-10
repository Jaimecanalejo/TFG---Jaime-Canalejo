# En backtest_simple.py
def ejecutar_backtest_desde_df(df):
    """
    Versión adaptada para la App que usa el DataFrame ya descargado.
    """
    df = df.copy()
    # Tu lógica de Weinstein (Precio > SMA30 y Mansfield > 0)
    df['Signal'] = ((df['Close'] > df['SMA_30']) & (df['Mansfield'] > 0)).astype(int)
    df['Posicion'] = df['Signal'].diff()

    rendimientos = []
    precio_entrada = 0
    en_operacion = False

    for i in range(len(df)):
        if df['Posicion'].iloc[i] == 1 and not en_operacion:
            precio_entrada = df['Close'].iloc[i]
            en_operacion = True
        elif df['Posicion'].iloc[i] == -1 and en_operacion:
            rentabilidad = (df['Close'].iloc[i] - precio_entrada) / precio_entrada
            rendimientos.append(rentabilidad)
            en_operacion = False

    # Cálculos estadísticos
    num_ops = len(rendimientos)
    total_ret = sum(rendimientos) * 100 if num_ops > 0 else 0
    win_rate = (len([r for r in rendimientos if r > 0]) / num_ops * 100) if num_ops > 0 else 0
    bh_ret = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100

    return {
        "num_ops": num_ops,
        "win_rate": win_rate,
        "total_ret": total_ret,
        "bh_ret": bh_ret
    }