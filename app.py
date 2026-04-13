import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_loader import descargar_datos, preparar_datos_semanales
from indicators import calcular_indicadores_individuales, calcular_fuerza_relativa
from exporter import generar_pdf 
from backtest_simple import ejecutar_backtest_desde_df 

# --- 1. LÓGICA DE CLASIFICACIÓN DE ETAPAS (ALGORITMO WEINSTEIN) ---
def clasificar_historico(df):
    """Clasifica cada vela en una de las 4 etapas de Weinstein basándose en SMA, Precio y Mansfield."""
    df = df.copy()
    df['Etapa'] = "Indeterminado"
    for i in range(1, len(df)):
        act, ant = df.iloc[i], df.iloc[i-1]
        # Etapa 2: Alcista (Precio > SMA, SMA subiendo, Mansfield > 0)
        if act['Close'] > act['SMA_30'] and act['SMA_30'] > ant['SMA_30'] and act['Mansfield'] > 0:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 2 (Alcista)"
        # Etapa 4: Bajista (Precio < SMA, SMA bajando, Mansfield < 0)
        elif act['Close'] < act['SMA_30'] and act['SMA_30'] < ant['SMA_30'] and act['Mansfield'] < 0:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 4 (Bajista)"
        # Etapa 1: Suelo (Precio > SMA pero sin momentum claro)
        elif act['Close'] > act['SMA_30']:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 1 (Suelo)"
        # Etapa 3: Techo (Fase de distribución)
        else:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 3 (Techo)"
    return df

def obtener_texto_señal(ticker, df):
    """Genera el dictamen técnico basado en indicadores actuales."""
    ultima = df.iloc[-1]
    penultima = df.iloc[-2]
    c_p = ultima['Close'] > ultima['SMA_30']
    c_m = ultima['Mansfield'] > 0
    c_r = ultima['RSI'] > penultima['RSI']
    if c_p and c_m and c_r: return "SEÑAL DE COMPRA (Etapa 2)"
    elif not c_p and not c_m: return "SEÑAL DE VENTA / EVITAR (Etapa 4)"
    return "ESPERAR CONFIRMACIÓN (Señales mixtas)"

def mostrar_señal_weinstein(ticker, df):
    """Muestra una alerta visual de Streamlit con la recomendación."""
    texto = obtener_texto_señal(ticker, df)
    if "COMPRA" in texto:
        st.success(f"🎯 {texto}: {ticker}")
    elif "VENTA" in texto:
        st.error(f"🚨 {texto}: {ticker}")
    else:
        st.warning(f"⚖️ {ticker}: {texto}")

# --- 2. CONFIGURACIÓN DE LA INTERFAZ Y SIDEBAR ---
st.set_page_config(page_title="Weinstein Pro Terminal Ultimate", layout="wide", page_icon="📈")

if 'mostrar_screener' not in st.session_state:
    st.session_state.mostrar_screener = False

st.sidebar.header("🕹️ Panel de Control")
modo_analisis = st.sidebar.radio("Modo de Análisis:", ["Individual", "Comparativa Multiactivo"])

ticker_1 = st.sidebar.text_input("Ticker Principal", value="AAPL").upper()
ticker_2 = ""
if modo_analisis == "Comparativa Multiactivo":
    ticker_2 = st.sidebar.text_input("Ticker Comparativo", value="MSFT").upper()

temporalidad = st.sidebar.selectbox("Selecciona Temporalidad:", options=["1 Hora", "1 Día", "1 Semana"], index=2)
fecha_inicio_sel = st.sidebar.date_input("Fecha de inicio", value=pd.to_datetime("2020-01-01"))

# --- SECCIÓN CONDICIONAL: SENSIBILIDAD (Solo en modo Individual) ---
sensibilidad_sma = 30 # Valor por defecto para cálculos internos
if modo_analisis == "Individual":
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Filtro de Sensibilidad")
    sensibilidad_sma = st.sidebar.slider("Periodo Media Móvil (SMA)", min_value=10, max_value=100, value=30)

boton_analizar = st.sidebar.button("🚀 Ejecutar Análisis")
if boton_analizar:
    st.session_state.mostrar_screener = False

st.sidebar.markdown("---")
st.sidebar.subheader("🕵️ Vigilancia de Mercado")
if st.sidebar.button("🔍 Escaneo Rápido Big Tech"):
    from screener import ejecutar_escaneo
    tickers_fijos = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "META", "AMZN"]
    with st.sidebar:
        with st.spinner("Escaneando..."):
            st.session_state.df_screener_result = ejecutar_escaneo(tickers_fijos, sensibilidad_sma)
            st.session_state.mostrar_screener = True 

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ Configuración Visual")
mostrar_sombreado = st.sidebar.toggle("Mostrar sombreado de etapas", value=True)

# --- 3. LÓGICA DE PROCESAMIENTO ---
if boton_analizar or ('df1' in st.session_state and not st.session_state.mostrar_screener):
    if boton_analizar:
        map_int = {"1 Hora": "60m", "1 Día": "1d", "1 Semana": "1wk"}
        interval = map_int[temporalidad]
        with st.spinner(f'Descargando datos...'):
            df1_raw = descargar_datos(ticker_1, str(fecha_inicio_sel), "2026-01-01", interval=interval)
            df_mkt_raw = descargar_datos("^GSPC", str(fecha_inicio_sel), "2026-01-01", interval=interval)
            df2_raw = descargar_datos(ticker_2, str(fecha_inicio_sel), "2026-01-01", interval=interval) if ticker_2 else None

        if df1_raw is not None and not df1_raw.empty:
            df1 = preparar_datos_semanales(df1_raw) if interval == "1wk" else df1_raw
            df_mkt = preparar_datos_semanales(df_mkt_raw) if interval == "1wk" else df_mkt_raw
            df1 = calcular_indicadores_individuales(df1, periodo_sma=sensibilidad_sma)
            df1['Mansfield'] = calcular_fuerza_relativa(df1, df_mkt)
            st.session_state.df1 = clasificar_historico(df1)
            st.session_state.t1, st.session_state.temp_label, st.session_state.current_sma = ticker_1, temporalidad, sensibilidad_sma
            if df2_raw is not None:
                df2 = preparar_datos_semanales(df2_raw) if interval == "1wk" else df2_raw
                df2 = calcular_indicadores_individuales(df2, periodo_sma=sensibilidad_sma)
                df2['Mansfield'] = calcular_fuerza_relativa(df2, df_mkt)
                st.session_state.df2 = clasificar_historico(df2); st.session_state.t2 = ticker_2
            else: st.session_state.df2 = None

# --- 4. RENDERIZADO ---
if st.session_state.mostrar_screener and 'df_screener_result' in st.session_state:
    st.markdown("# 🔍 Escáner Pro"); df_res = st.session_state.df_screener_result
    st.dataframe(df_res.style.map(lambda v: f'background-color: {"#d4edda" if "2" in str(v) else "#f8d7da" if "4" in str(v) else "#fff3cd" if "3" in str(v) else "#e2e3e5"}', subset=['Etapa Actual']), use_container_width=True)

elif 'df1' in st.session_state:
    df1, t1, df2, t2 = st.session_state.df1, st.session_state.t1, st.session_state.get('df2'), st.session_state.get('t2')
    st.markdown(f"## {t1} {'vs ' + t2 if df2 is not None else ''} ({st.session_state.temp_label})")
    
    u1 = df1.iloc[-1]
    if df2 is not None:
        u2 = df2.iloc[-1]
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric(f"Precio {t1}", f"{u1['Close']:.2f} $")
        col_m2.metric(f"SMA {st.session_state.current_sma} ({t1})", f"{u1['SMA_30']:.2f} $")
        col_m3.metric(f"Mansfield {t1}", f"{u1['Mansfield']:.2f}")
        col_m4.metric(f"RSI {t1}", f"{u1['RSI']:.2f}")
        col_n1, col_n2, col_n3, col_n4 = st.columns(4)
        col_n1.metric(f"Precio {t2}", f"{u2['Close']:.2f} $")
        col_n2.metric(f"SMA {st.session_state.current_sma} ({t2})", f"{u2['SMA_30']:.2f} $")
        col_n3.metric(f"Mansfield {t2}", f"{u2['Mansfield']:.2f}")
        col_n4.metric(f"RSI {t2}", f"{u2['RSI']:.2f}")
        c_sig1, c_sig2 = st.columns(2)
        with c_sig1: mostrar_señal_weinstein(t1, df1)
        with c_sig2: mostrar_señal_weinstein(t2, df2)
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f"Precio {t1}", f"{u1['Close']:.2f} $")
        col2.metric(f"SMA {st.session_state.current_sma}", f"{u1['SMA_30']:.2f} $")
        col3.metric("Fuerza Mansfield", f"{u1['Mansfield']:.2f}")
        col4.metric("RSI (14)", f"{u1['RSI']:.2f}")
        mostrar_señal_weinstein(t1, df1)

    st.markdown("---")
    cv1, cv2, cv3 = st.columns(3); ver_p = cv1.toggle("📉 Ver Gráfico de Precios", value=True); ver_m = cv2.toggle("📊 Ver Gráfico Mansfield", value=True); ver_r = cv3.toggle("🟪 Ver Gráfico RSI", value=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Gráfico Interactivo", "📜 Datos y Validación", "📖 Metodología"])

    with tab1:
        paneles = sum([ver_p, ver_m, ver_r])
        if paneles > 0:
            alturas = []
            if ver_p: alturas.append(0.5 if paneles > 1 else 1.0)
            if ver_m: alturas.append(0.25 if paneles > 1 else 1.0)
            if ver_r: alturas.append(0.25 if paneles > 1 else 1.0)
            fig = make_subplots(rows=paneles, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=alturas[::-1])
            f = 1
            if ver_p:
                if df2 is None:
                    fig.add_trace(go.Candlestick(x=df1.index, open=df1['Open'], high=df1['High'], low=df1['Low'], close=df1['Close'], name=t1), row=f, col=1)
                    fig.add_trace(go.Scatter(x=df1.index, y=df1['SMA_30'], line=dict(color='orange', width=2), name="SMA"), row=f, col=1)
                else:
                    fig.add_trace(go.Scatter(x=df1.index, y=df1['Close'], name=t1, line=dict(width=1.5)), row=f, col=1)
                    fig.add_trace(go.Scatter(x=df2.index, y=df2['Close'], name=t2, line=dict(width=1.5, dash='dot')), row=f, col=1)
                if mostrar_sombreado:
                    for i in range(1, len(df1)):
                        e = df1.iloc[i]['Etapa']
                        color = "rgba(0, 255, 0, 0.05)" if "2" in e else "rgba(255, 0, 0, 0.05)" if "4" in e else "rgba(255, 165, 0, 0.05)" if "3" in e else ""
                        if color: fig.add_vrect(x0=df1.index[i-1], x1=df1.index[i], fillcolor=color, line_width=0, layer="below", row=f, col=1)
                f += 1
            if ver_m:
                fig.add_trace(go.Scatter(x=df1.index, y=df1['Mansfield'], name=f"MF {t1}", fill='tozeroy'), row=f, col=1)
                if df2 is not None: fig.add_trace(go.Scatter(x=df2.index, y=df2['Mansfield'], name=f"MF {t2}", line=dict(dash='dot')), row=f, col=1)
                fig.add_hline(y=0, line_dash="dot", row=f, col=1); f += 1
            if ver_r:
                fig.add_trace(go.Scatter(x=df1.index, y=df1['RSI'], name=f"RSI {t1}", line=dict(color='purple')), row=f, col=1)
                if df2 is not None:
                    fig.add_trace(go.Scatter(x=df2.index, y=df2['RSI'], name=f"RSI {t2}", line=dict(dash='dot', color='red')), row=f, col=1)
                else:
                    fig.add_hline(y=70, line_color="red", row=f, col=1); fig.add_hline(y=30, line_color="green", row=f, col=1)
            
            fig.update_layout(height=850, dragmode='pan', hovermode='x unified', margin=dict(t=30, b=30, l=50, r=50))
            fig.update_xaxes(row=1, col=1, rangeslider_visible=False)
            fig.update_xaxes(row=paneles, col=1, rangeslider=dict(visible=True, thickness=0.02, bgcolor="rgba(128, 128, 128, 0.1)"))
            fig.update_yaxes(fixedrange=False); st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

    with tab2:
        if df2 is None:
            res = ejecutar_backtest_desde_df(df1)
            st.subheader("🧪 Validación Científica")
            c_b1, c_b2, c_b3, c_b4 = st.columns(4); c_b1.metric("Win Rate", f"{res['win_rate']:.1f}%"); c_b2.metric("Rent. Sistema", f"{res['total_ret']:.1f}%"); c_b3.metric("Rent. B&H", f"{res['bh_ret']:.1f}%"); c_b4.metric("Drawdown", f"{res['max_drawdown']:.1f}%")
            fig_eq = go.Figure(); fig_eq.add_trace(go.Scatter(x=res['equity_df']['Fecha'], y=res['equity_df']['Equity'], fill='tozeroy', line_color='green', name="Capital"))
            fig_eq.update_layout(title="Curva de Equidad (Backtesting)", height=300); st.plotly_chart(fig_eq, use_container_width=True)
            pdf = generar_pdf(t1, st.session_state.temp_label, u1['Close'], u1['SMA_30'], u1['Mansfield'], u1['RSI'], obtener_texto_señal(t1, df1), res, st.session_state.current_sma)
            col_exp1, col_exp2 = st.columns(2); col_exp1.download_button(f"📄 PDF {t1}", pdf, f"{t1}.pdf"); col_exp2.download_button(f"📥 CSV {t1}", df1.to_csv().encode('utf-8'), f"{t1}.csv")
            st.dataframe(df1.style.format(precision=2), use_container_width=True)
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader(f"📊 {t1}"); res1 = ejecutar_backtest_desde_df(df1); fig_eq1 = go.Figure(); fig_eq1.add_trace(go.Scatter(x=res1['equity_df']['Fecha'], y=res1['equity_df']['Equity'], fill='tozeroy', line_color='green'))
                fig_eq1.update_layout(title=f"Equidad {t1}", height=200); st.plotly_chart(fig_eq1, use_container_width=True)
                pdf1 = generar_pdf(t1, st.session_state.temp_label, df1.iloc[-1]['Close'], df1.iloc[-1]['SMA_30'], df1.iloc[-1]['Mansfield'], df1.iloc[-1]['RSI'], obtener_texto_señal(t1, df1), res1, st.session_state.current_sma)
                st.download_button(f"📄 PDF {t1}", pdf1, f"{t1}.pdf"); st.download_button(f"📥 CSV {t1}", df1.to_csv().encode('utf-8'), f"{t1}.csv"); st.dataframe(df1.tail(30), use_container_width=True)
            with col_b:
                st.subheader(f"📊 {t2}"); res2 = ejecutar_backtest_desde_df(df2); fig_eq2 = go.Figure(); fig_eq2.add_trace(go.Scatter(x=res2['equity_df']['Fecha'], y=res2['equity_df']['Equity'], fill='tozeroy', line_color='blue'))
                fig_eq2.update_layout(title=f"Equidad {t2}", height=200); st.plotly_chart(fig_eq2, use_container_width=True)
                pdf2 = generar_pdf(t2, st.session_state.temp_label, df2.iloc[-1]['Close'], df2.iloc[-1]['SMA_30'], df2.iloc[-1]['Mansfield'], df2.iloc[-1]['RSI'], obtener_texto_señal(t2, df2), res2, st.session_state.current_sma)
                st.download_button(f"📄 PDF {t2}", pdf2, f"{t2}.pdf"); st.download_button(f"📥 CSV {t2}", df2.to_csv().encode('utf-8'), f"{t2}.csv"); st.dataframe(df2.tail(30), use_container_width=True)

    with tab3:
        st.header("📖 Metodología de Stan Weinstein")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.info("### 1️⃣ Etapa 1: Fase de Suelo\nConsolidación tras una caída. La Media 30 se aplana.")
            st.success("### 2️⃣ Etapa 2: Fase Alcista\nEl precio rompe al alza con fuerza. **Momento óptimo de compra.**")
        with col_m2:
            st.warning("### 3️⃣ Etapa 3: Fase de Techo\nEl impulso se agota. El activo empieza a distribuir.")
            st.error("### 4️⃣ Etapa 4: Fase Bajista\nCaída libre por debajo de la Media 30. **Evitar el activo.**")

else:
    st.image("https://images.unsplash.com/photo-1611974717537-48358a602217?q=80&w=2070&auto=format&fit=crop")
    st.info("👈 Configura los parámetros y pulsa 'Ejecutar Análisis'.")
    st.markdown("""
    ### Bienvenido a la Terminal de Análisis de Etapas
    Esta herramienta permite aplicar la metodología de Stan Weinstein de forma automatizada:
    - **Análisis de Tendencia:** Media Móvil Simple de 30 periodos.
    - **Fuerza Relativa:** Cálculo del indicador Mansfield frente al S&P 500.
    - **Momentum:** Índice de Fuerza Relativa (RSI).
    """)
