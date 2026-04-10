import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_loader import descargar_datos, preparar_datos_semanales
from indicators import calcular_indicadores_individuales, calcular_fuerza_relativa
from exporter import generar_pdf 
# IMPORTANTE: Importamos desde tu archivo existente
from backtest_simple import ejecutar_backtest_desde_df 

# --- 1. LÓGICA DE CLASIFICACIÓN DE ETAPAS ---
def clasificar_historico(df):
    """Aplica la lógica de Stan Weinstein para clasificar cada vela en una de las 4 etapas."""
    df = df.copy()
    df['Etapa'] = "Indeterminado"
    for i in range(1, len(df)):
        act, ant = df.iloc[i], df.iloc[i-1]
        # Etapa 2: Alcista (Precio > SMA30, SMA30 subiendo, Mansfield > 0)
        if act['Close'] > act['SMA_30'] and act['SMA_30'] > ant['SMA_30'] and act['Mansfield'] > 0:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 2 (Alcista)"
        # Etapa 4: Bajista (Precio < SMA30, SMA30 bajando, Mansfield < 0)
        elif act['Close'] < act['SMA_30'] and act['SMA_30'] < ant['SMA_30'] and act['Mansfield'] < 0:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 4 (Bajista)"
        # Etapa 1: Suelo (Precio > SMA30 pero sin fuerza o tendencia plana)
        elif act['Close'] > act['SMA_30']:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 1 (Suelo)"
        # Etapa 3: Techo (Fase de distribución)
        else:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 3 (Techo)"
    return df

def obtener_texto_señal(ticker, df):
    """Auxiliar para el PDF y alertas: devuelve el texto de la señal."""
    ultima = df.iloc[-1]
    penultima = df.iloc[-2]
    c_p = ultima['Close'] > ultima['SMA_30']
    c_m = ultima['Mansfield'] > 0
    c_r = ultima['RSI'] > penultima['RSI']
    if c_p and c_m and c_r: return "SEÑAL DE COMPRA (Etapa 2)"
    elif not c_p and not c_m: return "SEÑAL DE VENTA / EVITAR (Etapa 4)"
    return "ESPERAR CONFIRMACIÓN (Señales mixtas)"

def mostrar_señal_weinstein(ticker, df):
    """Renderiza un cuadro visual con la recomendación del sistema."""
    texto = obtener_texto_señal(ticker, df)
    if "COMPRA" in texto:
        st.success(f"🎯 {texto}: {ticker}")
    elif "VENTA" in texto:
        st.error(f"🚨 {texto}: {ticker}")
    else:
        st.warning(f"⚖️ {ticker}: {texto}")

# --- 2. CONFIGURACIÓN DE LA INTERFAZ ---
st.set_page_config(page_title="Weinstein Pro Terminal Ultimate", layout="wide", page_icon="📈")

st.sidebar.header("🕹️ Panel de Control")
modo_analisis = st.sidebar.radio("Modo de Análisis:", ["Individual", "Comparativa Multiactivo"])

ticker_1 = st.sidebar.text_input("Ticker Principal", value="AAPL").upper()
ticker_2 = ""
if modo_analisis == "Comparativa Multiactivo":
    ticker_2 = st.sidebar.text_input("Ticker Comparativo", value="MSFT").upper()

temporalidad = st.sidebar.selectbox("Selecciona Temporalidad:", options=["1 Hora", "1 Día", "1 Semana"], index=2)
fecha_inicio_sel = st.sidebar.date_input("Fecha de inicio", value=pd.to_datetime("2020-01-01"))
boton_analizar = st.sidebar.button("🚀 Ejecutar Análisis")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ Configuración Visual")
mostrar_sombreado = st.sidebar.toggle("Mostrar sombreado de etapas", value=True)

# --- 3. LÓGICA DE PROCESAMIENTO ---
if boton_analizar or 'df1' in st.session_state:
    if boton_analizar:
        map_intervalo = {"1 Hora": "60m", "1 Día": "1d", "1 Semana": "1wk"}
        interval = map_intervalo[temporalidad]
        
        # Ajuste de seguridad para datos de 1 hora
        fecha_descarga = fecha_inicio_sel
        if interval == "60m":
            limite = pd.Timestamp.now().date() - pd.Timedelta(days=729)
            if fecha_inicio_sel < limite:
                st.sidebar.warning(f"⚠️ Yahoo solo permite 2 años para 1h. Ajustado a {limite}")
                fecha_descarga = limite

        # DESCARGA
        with st.spinner(f'Descargando datos de mercado...'):
            df1_raw = descargar_datos(ticker_1, str(fecha_descarga), "2026-01-01", interval=interval)
            df_mkt_raw = descargar_datos("^GSPC", str(fecha_descarga), "2026-01-01", interval=interval)
            if modo_analisis == "Comparativa Multiactivo" and ticker_2:
                df2_raw = descargar_datos(ticker_2, str(fecha_descarga), "2026-01-01", interval=interval)
            else:
                df2_raw = None

        # VALIDACIÓN POST-SPINNER
        if df1_raw is None or df1_raw.empty:
            st.error(f"❌ Error: El ticker '{ticker_1}' no es válido."); st.stop()
        if df_mkt_raw is None or df_mkt_raw.empty:
            st.error("❌ Error: No se pudo conectar con el índice (^GSPC)."); st.stop()
        if modo_analisis == "Comparativa Multiactivo" and df2_raw is None:
            st.error(f"❌ Error: El ticker comparativo '{ticker_2}' no es válido."); st.stop()

        # PROCESAMIENTO
        df1 = preparar_datos_semanales(df1_raw) if interval == "1wk" else df1_raw
        df_mkt = preparar_datos_semanales(df_mkt_raw) if interval == "1wk" else df_mkt_raw
        df1 = calcular_indicadores_individuales(df1)
        df1['Mansfield'] = calcular_fuerza_relativa(df1, df_mkt)
        
        st.session_state.df1 = clasificar_historico(df1)
        st.session_state.t1 = ticker_1
        st.session_state.temp_label = temporalidad
        st.session_state.interval_final = interval
        
        if df2_raw is not None:
            df2 = preparar_datos_semanales(df2_raw) if interval == "1wk" else df2_raw
            df2 = calcular_indicadores_individuales(df2)
            df2['Mansfield'] = calcular_fuerza_relativa(df2, df_mkt)
            st.session_state.df2 = clasificar_historico(df2)
            st.session_state.t2 = ticker_2
        else:
            st.session_state.df2 = None

    df1, t1 = st.session_state.df1, st.session_state.t1
    df2, t2 = st.session_state.get('df2'), st.session_state.get('t2')
    temp_act, interval_final = st.session_state.temp_label, st.session_state.interval_final

    # --- 4. RENDERIZADO DE INTERFAZ ---
    st.markdown(f"## { '🏢 ' + t1 if df2 is None else '⚔️ ' + t1 + ' vs ' + t2} ({temp_act})")
    
    u1, p1 = df1.iloc[-1], df1.iloc[-2]
    
    if df2 is None:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Precio Actual", f"{u1['Close']:.2f} $")
        c2.metric(f"SMA 30", f"{u1['SMA_30']:.2f} $", delta=f"{u1['SMA_30']-p1['SMA_30']:.2f}")
        c3.metric("Fuerza Mansfield", f"{u1['Mansfield']:.2f}")
        c4.metric("RSI (14)", f"{u1['RSI']:.2f}")
        st.markdown("### 🚦 Señal de Compra/Venta")
        mostrar_señal_weinstein(t1, df1)
    else:
        u2, p2 = df2.iloc[-1], df2.iloc[-2]
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.subheader(f"📊 {t1}")
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Precio", f"{u1['Close']:.2f} $")
            mc2.metric("SMA 30", f"{u1['SMA_30']:.2f} $", delta=f"{u1['SMA_30']-p1['SMA_30']:.2f}")
            mc3.metric("RSI", f"{u1['RSI']:.2f}")
            mostrar_señal_weinstein(t1, df1)
        with col_m2:
            st.subheader(f"📊 {t2}")
            mc4, mc5, mc6 = st.columns(3)
            mc4.metric("Precio", f"{u2['Close']:.2f} $")
            mc5.metric("SMA 30", f"{u2['SMA_30']:.2f} $", delta=f"{u2['SMA_30']-p2['SMA_30']:.2f}")
            mc6.metric("RSI", f"{u2['RSI']:.2f}")
            mostrar_señal_weinstein(t2, df2)

    st.markdown("---")
    st.write("🔧 **Configuración de paneles activos:**")
    cv1, cv2, cv3 = st.columns(3)
    ver_precio = cv1.toggle("📉 Ver Gráfico de Precios", value=True)
    ver_mansfield = cv2.toggle("📊 Ver Gráfico Mansfield", value=True)
    ver_rsi = cv3.toggle("🟪 Ver Gráfico RSI", value=True)

    tab1, tab2, tab3 = st.tabs(["📊 Gráfico Interactivo", "📜 Datos y Validación", "📖 Metodología"])

    with tab1:
        if sum([ver_precio, ver_mansfield, ver_rsi]) > 0:
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07, 
                                subplot_titles=(f'📉 Precio' if ver_precio else "", f'📊 Mansfield RS' if ver_mansfield else "", f'🟪 RSI' if ver_rsi else ""),
                                row_width=[0.25, 0.25, 0.5])
            if ver_precio:
                if df2 is None:
                    fig.add_trace(go.Candlestick(x=df1.index, open=df1['Open'], high=df1['High'], low=df1['Low'], close=df1['Close'], name=f"{t1}"), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df1.index, y=df1['SMA_30'], line=dict(color='orange', width=2), name="SMA 30w"), row=1, col=1)
                else:
                    fig.add_trace(go.Scatter(x=df1.index, y=df1['Close'], name=f"{t1}"), row=1, col=1)
                    df2_norm = (df2['Close'] / df2['Close'].iloc[0]) * df1['Close'].iloc[0]
                    fig.add_trace(go.Scatter(x=df2.index, y=df2_norm, name=f"{t2} (Norm.)", line=dict(dash='dot')), row=1, col=1)
            if ver_mansfield:
                fig.add_trace(go.Scatter(x=df1.index, y=df1['Mansfield'], name=f"MF {t1}", fill='tozeroy', fillcolor='rgba(135, 206, 250, 0.2)'), row=2, col=1)
                if df2 is not None: fig.add_trace(go.Scatter(x=df2.index, y=df2['Mansfield'], name=f"MF {t2}", line=dict(color='red')), row=2, col=1)
                fig.add_hline(y=0, line_dash="dot", row=2, col=1)
            if ver_rsi:
                fig.add_trace(go.Scatter(x=df1.index, y=df1['RSI'], name=f"RSI {t1}", line=dict(color='purple')), row=3, col=1)
                if df2 is not None: fig.add_trace(go.Scatter(x=df2.index, y=df2['RSI'], name=f"RSI {t2}", line=dict(color='red', dash='dot')), row=3, col=1)
                if df2 is None:
                    fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
                    fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)
            if mostrar_sombreado and ver_precio:
                y_min, y_max = df1['Low'].min()*0.95, df1['High'].max()*1.05
                for i in range(1, len(df1)):
                    e = df1.iloc[i]['Etapa']; color = "rgba(0, 255, 0, 0.04)" if "2" in e else "rgba(255, 0, 0, 0.04)" if "4" in e else "rgba(255, 165, 0, 0.05)" if "3" in e else "rgba(128, 128, 128, 0.02)"
                    if color: fig.add_shape(type="rect", xref="x", yref="y1", x0=df1.index[i-1], x1=df1.index[i], y0=y_min, y1=y_max, fillcolor=color, layer="below", line_width=0)
            u_f = df1.index[-1]; periodo = pd.DateOffset(months=1) if interval_final == "60m" else pd.DateOffset(years=1)
            fig.update_layout(height=950, dragmode='pan', hovermode='x unified', xaxis=dict(rangeslider=dict(visible=True, thickness=0.04), type="date", range=[u_f - periodo, u_f]))
            fig.update_yaxes(fixedrange=False); fig.update_xaxes(row=3, col=1, rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displaylogo': False})

    with tab2:
        # --- NUEVA SECCIÓN: BACKTESTING USANDO TU ARCHIVO ---
        st.subheader("🧪 Validación Científica (Backtesting)")
        res = ejecutar_backtest_desde_df(df1)
        
        c_b1, c_b2, c_b3, c_b4 = st.columns(4)
        c_b1.metric("Operaciones Realizadas", f"{res['num_ops']}")
        c_b2.metric("Tasa de Acierto", f"{res['win_rate']:.1f} %")
        c_b3.metric("Rentabilidad Weinstein", f"{res['total_ret']:.1f} %")
        c_b4.metric("Rentabilidad Buy & Hold", f"{res['bh_ret']:.1f} %")
        
        st.markdown("---")
        st.subheader("📂 Exportación y Reportes")
        c_exp1, c_exp2 = st.columns(2)
        pdf_bytes = generar_pdf(t1, temp_act, u1['Close'], u1['SMA_30'], u1['Mansfield'], u1['RSI'], obtener_texto_señal(t1, df1))
        c_exp1.download_button(f"📄 Informe PDF ({t1})", data=pdf_bytes, file_name=f"Informe_{t1}.pdf", mime="application/pdf")
        c_exp2.download_button(f"📥 CSV ({t1})", data=df1.to_csv().encode('utf-8'), file_name=f"{t1}_datos.csv", mime="text/csv")
        
        st.markdown("---")
        if df2 is None:
            st.subheader(f"📜 Tabla de datos: {t1}")
            st.dataframe(df1.style.format(precision=2), use_container_width=True)
        else:
            c_t1, c_t2 = st.columns(2)
            with c_t1:
                st.subheader(f"🏢 Activo: {t1}")
                st.download_button(f"📥 CSV {t1}", data=df1.to_csv().encode('utf-8'), file_name=f"{t1}_datos.csv")
                st.dataframe(df1.style.format(precision=2), use_container_width=True)
            with c_t2:
                st.subheader(f"🏢 Activo: {t2}")
                pdf_b2 = generar_pdf(t2, temp_act, u2['Close'], u2['SMA_30'], u2['Mansfield'], u2['RSI'], obtener_texto_señal(t2, df2))
                st.download_button(f"📄 Informe PDF ({t2})", data=pdf_b2, file_name=f"Informe_{t2}.pdf")
                st.dataframe(df2.style.format(precision=2), use_container_width=True)

    with tab3:
        st.header("📖 Metodología de Stan Weinstein")
        st.markdown("La estrategia se basa en el análisis de ciclos de mercado divididos en 4 fases críticas:")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.info("### 1️⃣ Etapa 1: Fase de Suelo\nConsolidación tras una caída. La Media 30 se aplana.")
            st.success("### 2️⃣ Etapa 2: Fase Alcista\nEl precio rompe al alza con fuerza. **Momento óptimo de compra.**")
        with col_m2:
            st.warning("### 3️⃣ Etapa 3: Fase de Techo\nEl impulso se agota. El activo empieza a distribuir.")
            st.error("### 4️⃣ Etapa 4: Fase Bajista\nCaída libre por debajo de la Media 30. **Evitar el activo.**")

# --- 6. BIENVENIDA ---
else:
    st.image("https://images.unsplash.com/photo-1611974717537-48358a602217?q=80&w=2070&auto=format&fit=crop", caption="Weinstein Pro Terminal")
    st.info("👈 Configura los parámetros en el panel lateral y pulsa 'Ejecutar Análisis' para comenzar.")
    st.markdown("""
    ### Bienvenido a la Terminal de Análisis de Etapas
    Esta herramienta permite aplicar la metodología de Stan Weinstein de forma automatizada:
    - **Análisis de Tendencia:** Media Móvil Simple de 30 periodos.
    - **Fuerza Relativa:** Cálculo del indicador Mansfield frente al S&P 500.
    - **Momentum:** Índice de Fuerza Relativa (RSI).
    """)