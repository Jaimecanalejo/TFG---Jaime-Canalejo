import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_loader import descargar_datos, preparar_datos_semanales
from indicators import calcular_indicadores_individuales, calcular_fuerza_relativa
from exporter import generar_pdf 
from backtest_simple import ejecutar_backtest_desde_df 
from user_session import obtener_usuario, crear_usuario, actualizar_usuario # <-- AÑADIR IMPORTACIÓN

# --- LISTA DE TICKERS SUGERIDOS PARA BÚSQUEDA DINÁMICA ---
TICKERS_SUGERIDOS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AVGO", "PEP", "COST",
    "ADBE", "CSCO", "NFLX", "AMD", "CMCSA", "TMUS", "INTC", "INTU", "AMAT", "QCOM",
    "TXN", "AMGN", "HON", "ISRG", "BKNG", "VRTX", "GILD", "SBUX", "MDLZ", "REGN",
    "PANW", "SNPS", "VRSK", "MELI", "CDNS", "KLAC", "CSX", "MAR", "PYPL", "ORLY",
    "ASML", "MNST", "ROP", "LRCX", "ADSK", "CTAS", "AEP", "PAYX", "PCAR", "DXCM",
    "IDXX", "KDP", "CHTR", "MCHP", "CPRT", "LULU", "EXC", "MRVL", "AZN", "BKR",
    "TEAM", "ADX", "WDAY", "GFS", "ODFL", "NXPI", "MRNA", "ABNB",
    "DASH", "BIIB", "SGEN", "ZS", "DLTR", "FAST", "EA", "EBAY", "ANSS", "VRSN",
    "JPM", "V", "MA", "UNH", "HD", "PG", "DIS", "JNJ", "WMT", "BAC", "XOM", "CVX"
]

# --- 1. LÓGICA DE CLASIFICACIÓN DE ETAPAS (ALGORITMO WEINSTEIN) ---
def clasificar_historico(df):
    """Clasifica cada vela en una de las 4 etapas de Weinstein basándose en SMA, Precio y Mansfield."""
    df = df.copy()
    df['Etapa'] = "Indeterminado"
    for i in range(1, len(df)):
        act, ant = df.iloc[i], df.iloc[i-1]
        if act['Close'] > act['SMA_30'] and act['SMA_30'] > ant['SMA_30'] and act['Mansfield'] > 0:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 2 (Alcista)"
        elif act['Close'] < act['SMA_30'] and act['SMA_30'] < ant['SMA_30'] and act['Mansfield'] < 0:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 4 (Bajista)"
        elif act['Close'] > act['SMA_30']:
            df.iat[i, df.columns.get_loc('Etapa')] = "Etapa 1 (Suelo)"
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

# --- CONTROL DE USUARIOS ---
if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None

if not st.session_state.usuario_actual:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("👋 Bienvenido")
        modo_ingreso = st.radio("¿Qué deseas hacer?", ["Iniciar Sesión", "Soy Nuevo Usuario"])
        
        nombre_input = st.text_input("Nombre de Usuario").strip()
        
        if st.button("Acceder", type="primary", use_container_width=True):
            if not nombre_input:
                st.warning("Introduce un nombre.")
            else:
                if modo_ingreso == "Soy Nuevo Usuario":
                    if crear_usuario(nombre_input):
                        st.session_state.usuario_actual = nombre_input
                        st.success("Usuario creado con éxito. Cargando entorno...")
                        st.rerun()
                    else:
                        st.error("El usuario ya existe. Selecciona 'Iniciar Sesión'.")
                else:
                    perfil = obtener_usuario(nombre_input)
                    if perfil:
                        st.session_state.usuario_actual = nombre_input
                        st.success(f"Bienvenido de nuevo, {nombre_input}!")
                        st.rerun()
                    else:
                        st.error("Usuario no encontrado. Crea una cuenta nueva.")
    st.stop() # Detiene la ejecución del resto de la app hasta loguearse

# Cargar perfil del usuario actual
perfil_usuario = obtener_usuario(st.session_state.usuario_actual)

# --- HACKS VISUALES PARA MEJORAR LA UX ---
components.html("""
    <script>
        const doc = window.parent.document;

        const traducciones = {
            'No results': 'Ningún resultado',
            'Zoom in': 'Acercar',
            'Zoom out': 'Alejar',
            'Pan': 'Navegar',
            'Zoom': 'Zoom',
            'Autoscale': 'Autoescala',
            'Reset axes': 'Restablecer ejes',
            'Box Select': 'Selección rectangular',
            'Lasso Select': 'Selección lazo',
            'Download plot as a PNG': 'Descargar como PNG'
        };

        const observer = new MutationObserver(() => {
            // Traducir desplegables
            const listItems = doc.querySelectorAll('li');
            listItems.forEach(li => {
                if (li.textContent.trim() === 'No results') {
                    li.textContent = 'Ningún resultado';
                }
            });

            // Traducir controles de Plotly
            const plotlyControls = doc.querySelectorAll('.modebar-btn');
            plotlyControls.forEach(btn => {
                const textoIngles = btn.getAttribute('data-title');
                if (traducciones[textoIngles]) {
                    btn.setAttribute('data-title', traducciones[textoIngles]);
                }
            });
        });

        observer.observe(doc.body, { childList: true, subtree: true });
    </script>
""", height=0, width=0)
st.markdown("""
    <style>
        [data-stale="true"] {
            opacity: 1 !important;
            filter: none !important;
            transition: none !important;
            pointer-events: auto !important;
        }
        div[data-testid="stStatusWidget"] {
            visibility: hidden;
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

if 'mostrar_screener' not in st.session_state:
    st.session_state.mostrar_screener = False

if 'last_error' not in st.session_state:
    st.session_state.last_error = None

st.sidebar.header("🕹️ Panel de Control")

st.sidebar.markdown(f"👤 **Usuario:** {st.session_state.usuario_actual}")
if st.sidebar.button("Cerrar Sesión"):
    # Limpiamos el usuario actual y los datos en memoria del análisis anterior
    claves_a_borrar = ['usuario_actual', 'df1', 'df2', 't1', 't2', 'df_screener_result', 'mostrar_screener', 'last_error']
    for clave in claves_a_borrar:
        if clave in st.session_state:
            del st.session_state[clave]
    st.rerun()

# --- Tu Contenedor Original ---
with st.sidebar.container(border=True):
    
    opciones_modo = ["Individual", "Comparativa Multiactivo"]
    modo_defecto = perfil_usuario.get('modo_analisis', 'Individual')
    idx_modo = opciones_modo.index(modo_defecto) if modo_defecto in opciones_modo else 0
    
    modo_analisis = st.radio("Modo de Análisis:", opciones_modo, index=idx_modo)
    
    st.markdown("### 📊 Selección de Activos")
    
    opciones_busqueda = ["✏️ Escribir otro Ticker..."] + TICKERS_SUGERIDOS

    # Determinar el índice por defecto según el perfil del usuario
    ticker_1_defecto = perfil_usuario.get('ticker_1', 'AAPL')
    try:
        idx_t1 = opciones_busqueda.index(ticker_1_defecto)
    except ValueError:
        idx_t1 = 0 # Si puso uno manual

    # Ticker 1
    ticker_seleccionado = st.selectbox(
        "Ticker Principal", 
        options=opciones_busqueda, 
        index=idx_t1,
        help="Busca en la lista o elige 'Escribir otro Ticker...' para introducir uno nuevo."
    )
    
    if ticker_seleccionado == "✏️ Escribir otro Ticker...":
        ticker_1 = st.text_input("Introduce el Ticker Principal manualmente:", value=ticker_1_defecto if idx_t1 == 0 else "").upper()
    else:
        ticker_1 = ticker_seleccionado

    # Ticker 2
    ticker_2 = ""
    ticker_2_defecto = perfil_usuario.get('ticker_2', 'MSFT')
    try:
        idx_t2 = opciones_busqueda.index(ticker_2_defecto)
    except ValueError:
        idx_t2 = 0

    if modo_analisis == "Comparativa Multiactivo":
        ticker_2_seleccionado = st.selectbox(
            "Ticker Comparativo", 
            options=opciones_busqueda, 
            index=idx_t2,
            help="Busca en la lista o elige 'Escribir otro Ticker...' para introducir uno nuevo."
        )
        
        if ticker_2_seleccionado == "✏️ Escribir otro Ticker...":
            ticker_2 = st.text_input("Introduce el Ticker Comparativo manualmente:", value=ticker_2_defecto if idx_t2 == 0 else "").upper()
        else:
            ticker_2 = ticker_2_seleccionado

    st.markdown("---")
    
    opciones_temp = ["1 Hora", "1 Día", "1 Semana"]
    temp_defecto = perfil_usuario.get('temporalidad', '1 Semana')
    idx_temp = opciones_temp.index(temp_defecto) if temp_defecto in opciones_temp else 2

    temporalidad = st.selectbox("Selecciona Temporalidad:", options=opciones_temp, index=idx_temp)

    st.markdown("---")
    st.markdown("### 📅 Periodo de Análisis")
    
    # Cargar preferencias de fechas del usuario
    fecha_inicio_str = perfil_usuario.get('fecha_inicio', "2020-01-01")
    try:
        inicio_defecto = pd.to_datetime(fecha_inicio_str).date()
    except:
        inicio_defecto = pd.to_datetime("2020-01-01").date()

    fin_actualidad_defecto = perfil_usuario.get('fin_actualidad', True)
    
    fecha_fin_str = perfil_usuario.get('fecha_fin', str(pd.Timestamp.now().date()))
    try:
        fin_defecto = pd.to_datetime(fecha_fin_str).date()
    except:
        fin_defecto = pd.Timestamp.now().date()

    # Inputs de fecha con los valores del usuario
    fecha_inicio_sel = st.date_input("Fecha de inicio", value=inicio_defecto, format="DD/MM/YYYY")

    fin_actualidad = st.checkbox("Fecha final: Actualidad (Hoy)", value=fin_actualidad_defecto)

    if fin_actualidad:
        fecha_fin_sel = pd.Timestamp.now().date()
    else:
        fecha_fin_sel = st.date_input("Fecha de fin", value=fin_defecto, format="DD/MM/YYYY")

    sensibilidad_sma = 30 
    if modo_analisis == "Individual":
        st.markdown("---")
        st.markdown("### 🎯 Filtro de Sensibilidad")
        sensibilidad_defecto = perfil_usuario.get('sensibilidad_sma', 30)
        sensibilidad_sma = st.slider("Periodo Media Móvil (SMA)", min_value=10, max_value=100, value=sensibilidad_defecto)

    st.markdown("<br>", unsafe_allow_html=True)
    boton_analizar = st.button("🚀 Ejecutar Análisis", use_container_width=True, type="primary")

    if boton_analizar: # Guardar preferencias al ejecutar análisis
        actualizar_usuario(st.session_state.usuario_actual, {
            "ticker_1": ticker_1,
            "ticker_2": ticker_2 if ticker_2 else "MSFT",
            "temporalidad": temporalidad,
            "sensibilidad_sma": sensibilidad_sma,
            "modo_analisis": modo_analisis,
            "fecha_inicio": str(fecha_inicio_sel),
            "fin_actualidad": fin_actualidad,
            "fecha_fin": str(fecha_fin_sel)
        })

    if temporalidad == "1 Hora":
        limite_yahoo = pd.Timestamp.now().date() - pd.Timedelta(days=729)
        if fecha_inicio_sel < limite_yahoo:
            st.warning(f"⚠️ Aviso: Yahoo solo almacena datos de 1h desde {limite_yahoo.strftime('%d/%m/%Y')}.")

# -----------------------------------------------------------

st.sidebar.markdown("---")
st.sidebar.subheader("🕵️ Vigilancia de Mercado")
if st.sidebar.button("🔍 Escaneo Rápido Big Tech", use_container_width=True):
    from screener import ejecutar_escaneo
    tickers_fijos = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "META", "AMZN"]
    with st.sidebar:
        with st.spinner("Escaneando..."):
            st.session_state.df_screener_result = ejecutar_escaneo(tickers_fijos, sensibilidad_sma)
            st.session_state.mostrar_screener = True 

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ Configuración Visual")
mostrar_sombreado = st.sidebar.toggle("Mostrar sombreado de etapas", value=True)

# --- DICCIONARIOS DE PLOTLY EN ESPAÑOL ---
CONFIG_ES_ZOOM = {
    'scrollZoom': True,
    'locale': 'es',
    'locales': {
        'es': {
            'format': {
                'months': ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
                'shortMonths': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
                'days': ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
                'shortDays': ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
            },
            'toolbar': {
                'download': 'Descargar gráfico como PNG',
                'zoom': 'Zoom',
                'zoomin': 'Acercar',
                'zoomout': 'Alejar',
                'Pan': 'Navegar',
                'reset': 'Restablecer',
                'select': 'Selección Lazo',
                'box': 'Selección Rectangular',
                'autoscale': 'Autoescala',
                'resetscale': 'Restablecer ejes',
                'togglehover': 'Alternar modo de cernido',
                'togglespikelines': 'Alternar líneas guía'
            }
        }
    }
}
CONFIG_ES_NO_ZOOM = dict(CONFIG_ES_ZOOM)
CONFIG_ES_NO_ZOOM['scrollZoom'] = False

# --- 3. LÓGICA DE PROCESAMIENTO ---
if boton_analizar or ('df1' in st.session_state and not st.session_state.mostrar_screener):
    if boton_analizar:
        
        st.session_state.mostrar_screener = False 
        st.session_state.last_error = None
        
        if not ticker_1:
            st.session_state.last_error = "⚠️ Por favor, introduce un ticker principal válido."
            st.sidebar.error(st.session_state.last_error)
            st.stop()
            
        if modo_analisis == "Comparativa Multiactivo" and not ticker_2:
            st.session_state.last_error = "⚠️ Por favor, introduce un ticker comparativo válido."
            st.sidebar.error(st.session_state.last_error)
            st.stop()
            
        map_int = {"1 Hora": "60m", "1 Día": "1d", "1 Semana": "1wk"}
        interval = map_int[temporalidad]
        
        fecha_descarga = fecha_inicio_sel

        if interval == "60m":
            limite_yahoo = pd.Timestamp.now().date() - pd.Timedelta(days=729)
            if fecha_inicio_sel < limite_yahoo:
                st.session_state.last_error = f"❌ Error de Rango: Para la temporalidad de '1 Hora', Yahoo Finance solo permite descargar datos de los últimos 2 años (desde el {limite_yahoo.strftime('%d/%m/%Y')}). Por favor, ajusta la Fecha de inicio."
                st.error(st.session_state.last_error)
                if 'df1' in st.session_state: del st.session_state.df1
                if 'df2' in st.session_state: del st.session_state.df2
                st.stop()

        with st.spinner(f'Descargando datos...'):
            df1_raw = descargar_datos(ticker_1, str(fecha_descarga), str(fecha_fin_sel), interval=interval)
            df_mkt_raw = descargar_datos("^GSPC", str(fecha_descarga), str(fecha_fin_sel), interval=interval)
            df2_raw = descargar_datos(ticker_2, str(fecha_descarga), str(fecha_fin_sel), interval=interval) if ticker_2 else None

        if df1_raw is None or df1_raw.empty:
            st.session_state.last_error = f"❌ Error: El ticker '{ticker_1}' no es válido o no devuelve datos en este rango de fechas."
            st.error(st.session_state.last_error)
            if 'df1' in st.session_state: del st.session_state.df1
            if 'df2' in st.session_state: del st.session_state.df2
            st.stop()
        if df_mkt_raw is None or df_mkt_raw.empty:
            st.session_state.last_error = "❌ Error al descargar datos de mercado (^GSPC). Revisa la conexión."
            st.error(st.session_state.last_error)
            if 'df1' in st.session_state: del st.session_state.df1
            if 'df2' in st.session_state: del st.session_state.df2
            st.stop()

        if df1_raw is not None and not df1_raw.empty:
            df1 = preparar_datos_semanales(df1_raw) if interval == "1wk" else df1_raw
            df_mkt = preparar_datos_semanales(df_mkt_raw) if interval == "1wk" else df_mkt_raw
            df1 = calcular_indicadores_individuales(df1, periodo_sma=sensibilidad_sma)
            df1['Mansfield'] = calcular_fuerza_relativa(df1, df_mkt)
            st.session_state.df1 = clasificar_historico(df1)
            st.session_state.t1, st.session_state.temp_label, st.session_state.current_sma = ticker_1, temporalidad, sensibilidad_sma
            if df2_raw is not None and not df2_raw.empty:
                df2 = preparar_datos_semanales(df2_raw) if interval == "1wk" else df2_raw
                df2 = calcular_indicadores_individuales(df2, periodo_sma=sensibilidad_sma)
                df2['Mansfield'] = calcular_fuerza_relativa(df2, df_mkt)
                st.session_state.df2 = clasificar_historico(df2); st.session_state.t2 = ticker_2
            else: st.session_state.df2 = None

# --- 4. RENDERIZADO ---
if st.session_state.mostrar_screener and 'df_screener_result' in st.session_state:
    st.markdown("# 🔍 Escáner Pro")
    df_res = st.session_state.df_screener_result
    
    def aplicar_colores_etapa(val):
        color = "#e2e3e5" 
        if "2" in str(val): color = "#d4edda" 
        elif "4" in str(val): color = "#f8d7da" 
        elif "3" in str(val): color = "#fff3cd" 
        return f'background-color: {color}'

    try:
        st.dataframe(df_res.style.applymap(aplicar_colores_etapa, subset=['Etapa Actual']), use_container_width=True)
    except:
        st.dataframe(df_res, use_container_width=True)

elif st.session_state.get('last_error'):
    st.error(st.session_state.last_error)

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
    
    tab1, tab2 = st.tabs(["📊 Gráfico Interactivo", "📜 Datos y Validación"])

    with tab1:
        paneles = sum([ver_p, ver_m, ver_r])
        if paneles > 0:
            alturas = []
            if ver_p: alturas.append(0.5 if paneles > 1 else 1.0)
            if ver_m: alturas.append(0.25 if paneles > 1 else 1.0)
            if ver_r: alturas.append(0.25 if paneles > 1 else 1.0)
            
            fig = make_subplots(rows=paneles, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_width=alturas[::-1])
            
            f = 1
            if ver_p:
                if df2 is None:
                    fig.add_trace(go.Candlestick(x=df1.index, open=df1['Open'], high=df1['High'], low=df1['Low'], close=df1['Close'], name=t1), row=f, col=1)
                    fig.add_trace(go.Scatter(x=df1.index, y=df1['SMA_30'], line=dict(color='orange', width=2), name="SMA"), row=f, col=1)
                else:
                    fig.add_trace(go.Scatter(x=df1.index, y=df1['Close'], name=t1, line=dict(width=1.5)), row=f, col=1)
                    fig.add_trace(go.Scatter(x=df2.index, y=df2['Close'], name=t2, line=dict(width=1.5, dash='dot')), row=f, col=1)
                
                if mostrar_sombreado:
                    start_idx = 1
                    current_color = ""
                    for i in range(1, len(df1)):
                        e = df1.iloc[i]['Etapa']
                        color = "rgba(0, 255, 0, 0.05)" if "2" in e else "rgba(255, 0, 0, 0.05)" if "4" in e else "rgba(255, 165, 0, 0.05)" if "3" in e else ""
                        
                        if color != current_color:
                            if current_color != "":
                                fig.add_vrect(x0=df1.index[start_idx-1], x1=df1.index[i-1], fillcolor=current_color, line_width=0, layer="below", row=f, col=1)
                            current_color = color
                            start_idx = i
                    if current_color != "":
                        fig.add_vrect(x0=df1.index[start_idx-1], x1=df1.index[-1], fillcolor=current_color, line_width=0, layer="below", row=f, col=1)
                
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
            
            fig.update_xaxes(showticklabels=True)
            
            fig.update_xaxes(row=1, col=1, rangeslider_visible=False)
            fig.update_xaxes(row=paneles, col=1, rangeslider=dict(visible=True, thickness=0.02, bgcolor="rgba(128, 128, 128, 0.1)"))
            fig.update_yaxes(fixedrange=False)
            
            st.plotly_chart(fig, use_container_width=True, config=CONFIG_ES_ZOOM)

    with tab2:
        if df2 is None:
            res = ejecutar_backtest_desde_df(df1)
            st.subheader("🧪 Validación Científica")
            c_b1, c_b2, c_b3, c_b4 = st.columns(4); c_b1.metric("Win Rate", f"{res['win_rate']:.1f}%"); c_b2.metric("Rent. Sistema", f"{res['total_ret']:.1f}%"); c_b3.metric("Rent. B&H", f"{res['bh_ret']:.1f}%"); c_b4.metric("Drawdown", f"{res['max_drawdown']:.1f}%")
            fig_eq = go.Figure(); fig_eq.add_trace(go.Scatter(x=res['equity_df']['Fecha'], y=res['equity_df']['Equity'], fill='tozeroy', line_color='green', name="Capital"))
            fig_eq.update_layout(title="Curva de Equidad (Backtesting)", height=300)
            
            st.plotly_chart(fig_eq, use_container_width=True, config=CONFIG_ES_NO_ZOOM)
            
            pdf = generar_pdf(t1, st.session_state.temp_label, u1['Close'], u1['SMA_30'], u1['Mansfield'], u1['RSI'], obtener_texto_señal(t1, df1), res, st.session_state.current_sma)
            col_exp1, col_exp2 = st.columns(2); col_exp1.download_button(f"📄 PDF {t1}", pdf, f"{t1}.pdf"); col_exp2.download_button(f"📥 CSV {t1}", df1.to_csv().encode('utf-8'), f"{t1}.csv")
            st.dataframe(df1.style.format(precision=2), use_container_width=True)
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader(f"📊 {t1}"); res1 = ejecutar_backtest_desde_df(df1); fig_eq1 = go.Figure(); fig_eq1.add_trace(go.Scatter(x=res1['equity_df']['Fecha'], y=res1['equity_df']['Equity'], fill='tozeroy', line_color='green'))
                fig_eq1.update_layout(title=f"Equidad {t1}", height=200)
                
                st.plotly_chart(fig_eq1, use_container_width=True, config=CONFIG_ES_NO_ZOOM)
                
                pdf1 = generar_pdf(t1, st.session_state.temp_label, df1.iloc[-1]['Close'], df1.iloc[-1]['SMA_30'], df1.iloc[-1]['Mansfield'], df1.iloc[-1]['RSI'], obtener_texto_señal(t1, df1), res1, st.session_state.current_sma)
                st.download_button(f"📄 PDF {t1}", pdf1, f"{t1}.pdf"); st.download_button(f"📥 CSV {t1}", df1.to_csv().encode('utf-8'), f"{t1}.csv"); st.dataframe(df1.tail(30), use_container_width=True)
            with col_b:
                st.subheader(f"📊 {t2}"); res2 = ejecutar_backtest_desde_df(df2); fig_eq2 = go.Figure(); fig_eq2.add_trace(go.Scatter(x=res2['equity_df']['Fecha'], y=res2['equity_df']['Equity'], fill='tozeroy', line_color='blue'))
                fig_eq2.update_layout(title=f"Equidad {t2}", height=200)
                
                st.plotly_chart(fig_eq2, use_container_width=True, config=CONFIG_ES_NO_ZOOM)
                
                pdf2 = generar_pdf(t2, st.session_state.temp_label, df2.iloc[-1]['Close'], df2.iloc[-1]['SMA_30'], df2.iloc[-1]['Mansfield'], df2.iloc[-1]['RSI'], obtener_texto_señal(t2, df2), res2, st.session_state.current_sma)
                st.download_button(f"📄 PDF {t2}", pdf2, f"{t2}.pdf"); st.download_button(f"📥 CSV {t2}", df2.to_csv().encode('utf-8'), f"{t2}.csv"); st.dataframe(df2.tail(30), use_container_width=True)

else:
    st.info("👈 Configura los parámetros y pulsa 'Ejecutar Análisis'.")
    st.markdown("""
    ### Bienvenido a la Terminal de Análisis de Etapas
    Esta herramienta permite aplicar la metodología de Stan Weinstein de forma automatizada:
    - **Análisis de Tendencia:** Media Móvil Simple de 30 periodos.
    - **Fuerza Relativa:** Cálculo del indicador Mansfield frente al S&P 500.
    - **Momentum:** Índice de Fuerza Relativa (RSI).
    """)
