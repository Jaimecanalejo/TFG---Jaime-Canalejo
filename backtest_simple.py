import pandas as pd
import numpy as np

def ejecutar_backtest_desde_df(df, capital_inicial=1.0, comision_por_op=0.0):
    """
    Backtesting avanzado con capital inicial, comisiones por operación,
    métricas de riesgo y serie temporal de equidad en tiempo real.
    Lógica de Weinstein:
    - Entrada (Etapa 2): Cierre > SMA_30 Y Mansfield > 0
    - Salida (Tendencia): Cierre < SMA_30
    """
    df = df.copy()
    
    # Generar señales respetando la disciplina de tendencia de Weinstein
    signals = []
    en_op = False
    for i in range(len(df)):
        c = df['Close'].iloc[i]
        sma = df['SMA_30'].iloc[i]
        mf = df['Mansfield'].iloc[i]
        
        if pd.isna(sma) or pd.isna(mf):
            signals.append(0)
            continue
            
        if not en_op:
            if c > sma and mf > 0:
                en_op = True
                signals.append(1)
            else:
                signals.append(0)
        else:
            if c < sma:
                en_op = False
                signals.append(0)
            else:
                signals.append(1)
                
    df['Signal'] = signals
    df['Posicion'] = df['Signal'].diff()

    num_compras = (df['Posicion'] == 1).sum()
    num_ventas = (df['Posicion'] == -1).sum()

    rendimientos = []
    capital_actual = float(capital_inicial)
    equity_curve = [capital_actual]
    fechas_equity = [df.index[0]]
    
    precio_entrada = 0.0
    en_operacion = False
    capital_invertido = 0.0
    comisiones_totales = 0.0

    # Registro detallado de operaciones (entradas, salidas, capital invertido, capital recuperado, rentabilidad)
    historial_ops = []
    fecha_entrada = None
    capital_entrada_monto = 0.0

    for i in range(1, len(df)):
        fecha_actual = df.index[i]
        fecha_str = str(fecha_actual).split("T")[0].split(" ")[0]
        precio_actual = df['Close'].iloc[i]
        pos = df['Posicion'].iloc[i]
        
        # Entrada en posición (Compra)
        if pos == 1 and not en_operacion:
            precio_entrada = precio_actual
            capital_actual -= comision_por_op
            comisiones_totales += comision_por_op
            if capital_actual < 0:
                capital_actual = 0.0
            capital_invertido = capital_actual
            capital_entrada_monto = capital_actual
            fecha_entrada = fecha_str
            en_operacion = True
            
        # Salida de posición (Venta)
        elif pos == -1 and en_operacion:
            if precio_entrada > 0 and capital_invertido > 0:
                valor_posicion = capital_invertido * (precio_actual / precio_entrada)
            else:
                valor_posicion = capital_invertido
                
            capital_actual = valor_posicion - comision_por_op
            comisiones_totales += comision_por_op
            if capital_actual < 0:
                capital_actual = 0.0
                
            rentabilidad = (capital_actual - capital_invertido) / capital_invertido if capital_invertido > 0 else 0
            ganancia_op = capital_actual - capital_invertido
            
            historial_ops.append({
                "Fecha Compra": fecha_entrada,
                "Precio Compra": round(precio_entrada, 2),
                "Capital Invertido": f"${capital_entrada_monto:,.2f}",
                "Fecha Venta": fecha_str,
                "Precio Venta": round(precio_actual, 2),
                "Capital Recaudado": f"${capital_actual:,.2f}",
                "Resultado ($)": f"${ganancia_op:+,.2f}",
                "Rentabilidad (%)": f"{rentabilidad * 100:+.2f}%",
                "Motivo Salida": "Ruptura Bajista SMA30 (Conversión a Liquidez)"
            })
            
            rendimientos.append(rentabilidad)
            en_operacion = False
            capital_invertido = 0.0

        # Valor actual flotante de la cartera / activo
        if en_operacion and precio_entrada > 0 and capital_invertido > 0:
            equidad_dia = capital_invertido * (precio_actual / precio_entrada)
        else:
            equidad_dia = capital_actual
            
        equity_curve.append(max(0.0, float(equidad_dia)))
        fechas_equity.append(df.index[i])

    # Si hay una posición abierta al final del periodo
    if en_operacion and precio_entrada > 0:
        precio_ultimo = df['Close'].iloc[-1]
        fecha_ultimo = str(df.index[-1]).split("T")[0].split(" ")[0]
        valor_final = capital_invertido * (precio_ultimo / precio_entrada)
        ganancia_op = valor_final - capital_invertido
        rentabilidad = (valor_final - capital_invertido) / capital_invertido if capital_invertido > 0 else 0
        historial_ops.append({
            "Fecha Compra": fecha_entrada,
            "Precio Compra": round(precio_entrada, 2),
            "Capital Invertido": f"${capital_entrada_monto:,.2f}",
            "Fecha Venta": f"{fecha_ultimo} (Abierta)",
            "Precio Venta": round(precio_ultimo, 2),
            "Capital Recaudado": f"${valor_final:,.2f}",
            "Resultado ($)": f"${ganancia_op:+,.2f}",
            "Rentabilidad (%)": f"{rentabilidad * 100:+.2f}%",
            "Motivo Salida": "Posición Mantenida en Cartera (En Etapa 2 Alcista)"
        })

    # Estadísticas básicas
    num_ops = len(rendimientos) + (1 if en_operacion else 0)
    capital_final = equity_curve[-1]
    total_ret = ((capital_final - capital_inicial) / capital_inicial * 100) if capital_inicial > 0 else 0.0
    win_rate = (len([r for r in rendimientos if r > 0]) / len(rendimientos) * 100) if rendimientos else (100.0 if en_operacion and (capital_final > capital_inicial) else 0.0)
    
    # --- CÁLCULO DEL MAX DRAWDOWN ---
    equity_series = pd.Series(equity_curve)
    roll_max = equity_series.cummax()
    drawdowns = np.where(roll_max > 0, (equity_series - roll_max) / roll_max, 0.0)
    max_drawdown = float(drawdowns.min()) * 100.0 if len(drawdowns) > 0 else 0.0

    # Rentabilidad Buy & Hold
    bh_ret = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100

    return {
        "num_ops": num_ops,
        "num_compras": num_compras,
        "num_ventas": num_ventas,
        "win_rate": win_rate,
        "total_ret": total_ret,
        "bh_ret": bh_ret,
        "max_drawdown": max_drawdown,
        "capital_inicial": capital_inicial,
        "capital_final": capital_final,
        "comisiones_totales": comisiones_totales,
        "equity_df": pd.DataFrame({'Fecha': fechas_equity, 'Equity': equity_curve}),
        "operaciones_df": pd.DataFrame(historial_ops),
        "df_signal": df
    }