import pandas as pd
import numpy as np
from data_loader import descargar_datos, preparar_datos_semanales
from indicators import calcular_indicadores_individuales, calcular_fuerza_relativa
from classifier import clasificar_historico
from backtest_simple import ejecutar_backtest_desde_df

def simular_cartera(lista_tickers, inicio, fin, interval, sensibilidad_sma, progress_callback=None, capital_inicial=10000.0, comision_por_op=1.0):
    """
    Realiza la simulación histórica de una cartera de activos basada en la estrategia de Weinstein Etapa 2.
    Pondera uniformemente el capital inicial entre cada activo y cobra una comisión por operación fija (broker).
    """
    valid_tickers = [t.strip().upper() for t in lista_tickers if t.strip()]
    if not valid_tickers:
        raise ValueError("No se especificaron activos válidos para la simulación.")
        
    capital_por_activo = float(capital_inicial) / len(valid_tickers)

    if progress_callback:
        progress_callback("Descargando índice de referencia (^GSPC)...")
        
    df_mkt_raw = descargar_datos("^GSPC", inicio, fin, interval=interval)
    if df_mkt_raw is None or df_mkt_raw.empty:
        raise ValueError("No se pudieron descargar los datos de mercado (^GSPC) para el rango seleccionado.")
        
    df_mkt = preparar_datos_semanales(df_mkt_raw) if interval == "1wk" else df_mkt_raw
    
    resultados_tickers = {}
    equity_dfs = []
    
    for ticker in valid_tickers:
        if progress_callback:
            progress_callback(f"Descargando y analizando {ticker}...")
            
        df_raw = descargar_datos(ticker, inicio, fin, interval=interval)
        if df_raw is None or df_raw.empty:
            continue
            
        df = preparar_datos_semanales(df_raw) if interval == "1wk" else df_raw
        df = calcular_indicadores_individuales(df, periodo_sma=sensibilidad_sma)
        df['Mansfield'] = calcular_fuerza_relativa(df, df_mkt)
        df = clasificar_historico(df)
        
        # Ejecutar el backtest con su fracción de capital y comisión por operación
        res_backtest = ejecutar_backtest_desde_df(df, capital_inicial=capital_por_activo, comision_por_op=comision_por_op)
        
        res_backtest['precio_cierre'] = df['Close'].iloc[-1]
        
        resultados_tickers[ticker] = res_backtest
        
        # Guardar curva de equidad
        eq_df = res_backtest['equity_df'].copy()
        eq_df = eq_df.rename(columns={'Equity': f'Equity_{ticker}'})
        eq_df.set_index('Fecha', inplace=True)
        equity_dfs.append(eq_df)
        
    if not resultados_tickers:
        raise ValueError("No se pudieron obtener datos válidos para ninguno de los tickers especificados.")
        
    # Unir curvas de equidad de todos los activos
    portfolio_df = pd.concat(equity_dfs, axis=1, join='outer')
    
    # Rellenar valores nulos (arrastrar el capital actual de cada activo en periodos sin cotización)
    portfolio_df = portfolio_df.ffill().bfill()
    
    # El capital agregado de la cartera es la suma de la equidad de cada activo
    portfolio_df['Equity_Portfolio'] = portfolio_df.sum(axis=1)
    portfolio_df.reset_index(inplace=True)
    
    # Calcular métricas del portafolio global
    equity_series = portfolio_df['Equity_Portfolio']
    roll_max = equity_series.cummax()
    drawdowns = np.where(roll_max > 0, (equity_series - roll_max) / roll_max, 0.0)
    portfolio_max_dd = float(drawdowns.min()) * 100.0 if len(drawdowns) > 0 else 0.0
    
    capital_final = float(equity_series.iloc[-1])
    ganancia_neta = capital_final - float(capital_inicial)
    portfolio_total_ret = (ganancia_neta / float(capital_inicial)) * 100.0 if capital_inicial > 0 else 0.0
    
    # Agregación de métricas
    tot_ops = sum(res['num_ops'] for res in resultados_tickers.values())
    tot_compras = sum(res['num_compras'] for res in resultados_tickers.values())
    tot_ventas = sum(res['num_ventas'] for res in resultados_tickers.values())
    tot_comisiones = sum(res['comisiones_totales'] for res in resultados_tickers.values())
    avg_win_rate = sum(res['win_rate'] for res in resultados_tickers.values()) / len(resultados_tickers)
    avg_bh_ret = sum(res['bh_ret'] for res in resultados_tickers.values()) / len(resultados_tickers)
    
    # DataFrame resumen para la tabla detallada y registro unificado de operaciones
    resumen_data = []
    todas_las_operaciones = []
    
    for ticker, res in resultados_tickers.items():
        resumen_data.append({
            "Activo": ticker,
            "Capital Inicial": f"${capital_por_activo:,.2f}",
            "Capital Final": f"${res['capital_final']:,.2f}",
            "Precio Actual": round(res['precio_cierre'], 2),
            "Rent. Sistema": f"{res['total_ret']:.2f}%",
            "Rent. B&H": f"{res['bh_ret']:.2f}%",
            "Win Rate": f"{res['win_rate']:.2f}%",
            "Max Drawdown": f"{res['max_drawdown']:.2f}%",
            "Comisiones": f"${res['comisiones_totales']:,.2f}",
            "Operaciones": res['num_ops'],
            "Compras": res['num_compras'],
            "Ventas": res['num_ventas']
        })
        
        if 'operaciones_df' in res and not res['operaciones_df'].empty:
            df_ops_t = res['operaciones_df'].copy()
            df_ops_t.insert(0, "Activo", ticker)
            todas_las_operaciones.append(df_ops_t)
            
    resumen_df = pd.DataFrame(resumen_data)
    
    if todas_las_operaciones:
        historial_ops_df = pd.concat(todas_las_operaciones, ignore_index=True)
        historial_ops_df = historial_ops_df.sort_values(by="Fecha Compra", ascending=True).reset_index(drop=True)
    else:
        historial_ops_df = pd.DataFrame()
    
    return {
        "resultados_tickers": resultados_tickers,
        "portfolio_equity_df": portfolio_df[['Fecha', 'Equity_Portfolio']],
        "resumen_tickers_df": resumen_df,
        "historial_operaciones_df": historial_ops_df,
        "metricas_globales": {
            "capital_inicial": capital_inicial,
            "capital_final": capital_final,
            "ganancia_neta": ganancia_neta,
            "total_ret": portfolio_total_ret,
            "bh_ret": avg_bh_ret,
            "max_drawdown": portfolio_max_dd,
            "num_ops": tot_ops,
            "num_compras": tot_compras,
            "num_ventas": tot_ventas,
            "win_rate": avg_win_rate,
            "tot_comisiones": tot_comisiones,
            "comision_por_op": comision_por_op
        }
    }

def optimizar_y_simular_cartera(lista_candidatos, top_n=3, inicio="2020-01-01", fin="2026-07-24", interval="1wk", sensibilidad_sma=30, progress_callback=None, capital_inicial=10000.0, comision_por_op=1.0):
    """
    Evalúa automáticamente mediante backtesting cuantitativo una lista de activos candidatos,
    selecciona los Top N activos con mejor rendimiento algorítmico y simula la cartera optimizada.
    """
    valid_candidates = [t.strip().upper() for t in lista_candidatos if t.strip()]
    if not valid_candidates:
        raise ValueError("No se especificaron activos candidatos válidos para la optimización.")

    if progress_callback:
        progress_callback("Descargando índice de referencia (^GSPC)...")
        
    df_mkt_raw = descargar_datos("^GSPC", inicio, fin, interval=interval)
    if df_mkt_raw is None or df_mkt_raw.empty:
        raise ValueError("No se pudieron descargar los datos de mercado (^GSPC) para el rango seleccionado.")
        
    df_mkt = preparar_datos_semanales(df_mkt_raw) if interval == "1wk" else df_mkt_raw

    evaluaciones = []
    
    # 1. Evaluación cuantitativa previa de cada candidato
    for idx, ticker in enumerate(valid_candidates):
        if progress_callback:
            progress_callback(f"Evaluando backtesting cuantitativo de {ticker} ({idx+1}/{len(valid_candidates)})...")
            
        df_raw = descargar_datos(ticker, inicio, fin, interval=interval)
        if df_raw is None or df_raw.empty:
            continue
            
        df = preparar_datos_semanales(df_raw) if interval == "1wk" else df_raw
        df = calcular_indicadores_individuales(df, periodo_sma=sensibilidad_sma)
        df['Mansfield'] = calcular_fuerza_relativa(df, df_mkt)
        df = clasificar_historico(df)
        
        # Ejecutar backtest individual base 1.0 sin comisiones para ranking justo
        res = ejecutar_backtest_desde_df(df, capital_inicial=1.0, comision_por_op=0.0)
        
        alpha = res['total_ret'] - res['bh_ret']
        # Score cuantitativo que equilibra la ganancia neta absoluta del sistema y el Alfa (exceso sobre Buy & Hold)
        score = res['total_ret'] + (alpha if alpha > 0 else alpha * 0.5)
        
        evaluaciones.append({
            "Activo": ticker,
            "Score": score,
            "Rent. Sistema": res['total_ret'],
            "Rent. B&H": res['bh_ret'],
            "Alfa vs B&H": alpha,
            "Win Rate": res['win_rate'],
            "Max Drawdown": res['max_drawdown'],
            "Operaciones": res['num_ops']
        })
        
    if not evaluaciones:
        raise ValueError("No se pudieron obtener datos válidos para ninguno de los activos candidatos.")
        
    # Ordenar por Score Combinado (Ganancia Absoluta + Alfa)
    eval_df = pd.DataFrame(evaluaciones)
    eval_df = eval_df.sort_values(by="Score", ascending=False).reset_index(drop=True)
    
    # Seleccionar Top N activos
    top_n_actual = min(int(top_n), len(eval_df))
    selected_tickers = eval_df['Activo'].iloc[:top_n_actual].tolist()

    # Análisis de Reasignación de Capital y Coste de Oportunidad
    coste_oportunidad_data = []
    top_score_min = eval_df['Score'].iloc[top_n_actual - 1]
    
    for idx in range(len(eval_df)):
        row = eval_df.iloc[idx]
        if idx < top_n_actual:
            dictamen = f"✅ Mantener en cartera (Dentro del Top {top_n_actual})"
        else:
            diff_score = top_score_min - row['Score']
            dictamen = f"⚠️ Vender / Reasignar capital hacia Top {top_n_actual} (Desventaja de {diff_score:.1f} pts de Score por Coste de Oportunidad)"
        coste_oportunidad_data.append(dictamen)
        
    eval_df['Dictamen de Reasignación'] = coste_oportunidad_data

    # Formatear columnas de la tabla de evaluación
    eval_df['Estado'] = eval_df['Activo'].apply(lambda x: "🏆 Seleccionado" if x in selected_tickers else "❌ Descartado")
    eval_df['Rent. Sistema'] = eval_df['Rent. Sistema'].apply(lambda x: f"{x:.2f}%")
    eval_df['Rent. B&H'] = eval_df['Rent. B&H'].apply(lambda x: f"{x:.2f}%")
    eval_df['Alfa vs B&H'] = eval_df['Alfa vs B&H'].apply(lambda x: f"{x:+.2f}% p.")
    eval_df['Win Rate'] = eval_df['Win Rate'].apply(lambda x: f"{x:.2f}%")
    eval_df['Max Drawdown'] = eval_df['Max Drawdown'].apply(lambda x: f"{x:.2f}%")
    eval_df['Score'] = eval_df['Score'].apply(lambda x: f"{x:.1f}")
    
    # Reorganizar columnas
    eval_df = eval_df[['Estado', 'Activo', 'Score', 'Rent. Sistema', 'Alfa vs B&H', 'Rent. B&H', 'Win Rate', 'Max Drawdown', 'Operaciones', 'Dictamen de Reasignación']]
    
    if progress_callback:
        progress_callback(f"Construyendo cartera optimizada con Top {top_n_actual} activos: {', '.join(selected_tickers)}...")
        
    # 2. Ejecutar la simulación de cartera con los activos seleccionados
    res_cartera = simular_cartera(
        lista_tickers=selected_tickers,
        inicio=inicio,
        fin=fin,
        interval=interval,
        sensibilidad_sma=sensibilidad_sma,
        progress_callback=progress_callback,
        capital_inicial=capital_inicial,
        comision_por_op=comision_por_op
    )
    
    res_cartera['evaluacion_candidatos_df'] = eval_df
    res_cartera['selected_tickers'] = selected_tickers
    
    return res_cartera
