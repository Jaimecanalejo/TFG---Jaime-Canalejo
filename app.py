import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_loader import descargar_datos, preparar_datos_semanales
from indicators import calcular_indicadores_individuales, calcular_fuerza_relativa
from classifier import clasificar_historico
from exporter import generar_pdf 
from backtest_simple import ejecutar_backtest_desde_df 
from user_session import obtener_usuario, crear_usuario, actualizar_usuario, verificar_login 
from portfolio import simular_cartera, optimizar_y_simular_cartera
from screener import ejecutar_escaneo, filtrar_candidatos_alta_beta

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
st.set_page_config(page_title="Weinstein Pro | Quant Terminal", layout="wide", page_icon="📈")

# --- SISTEMA VISUAL GLOBAL ---
# Mantener los estilos en un único bloque evita que cada módulo parezca una app distinta.
st.markdown("""
<style>
    :root {
        --app-bg: #f4f7fb;
        --surface: #ffffff;
        --surface-muted: #f8fafc;
        --border: #e2e8f0;
        --text: #0f172a;
        --muted: #64748b;
        --primary: #2563eb;
        --primary-dark: #1d4ed8;
        --success: #059669;
        --danger: #dc2626;
        --radius: 14px;
    }

    .stApp { background: var(--app-bg); color: var(--text); font-size:.88rem; }
    .block-container { max-width: 1800px; padding: 2rem 1.25rem 2.25rem; }
    h1, h2, h3 { color: var(--text); letter-spacing: -0.025em; }
    h1 { font-size: 1.65rem !important; font-weight: 750 !important; }
    h2 { font-size: 1.2rem !important; font-weight: 700 !important; }
    h3 { font-size: .98rem !important; font-weight: 700 !important; }
    p, label, .stCaption { color: var(--muted); }

    [data-testid="stSidebar"] {
        background: #0b1220;
        border-right: 1px solid #172033;
        width: 15rem !important;
        min-width: 15rem !important;
        max-width: 15rem !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        width: 15rem !important;
        padding: .6rem .6rem 1rem;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stCaption { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] hr { border-color: #243044; margin: .5rem 0; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
        background: #111b2e;
        border: 1px solid #243044;
        border-radius: var(--radius);
        padding: .15rem;
    }
    .sidebar-brand { display:flex; align-items:center; gap:.5rem; padding:.1rem .05rem .55rem; }
    .sidebar-logo { display:grid; place-items:center; flex:0 0 28px; width:28px; height:28px; border-radius:8px; background:linear-gradient(135deg,#3b82f6,#6366f1); color:white; font-size:.78rem; font-weight:800; box-shadow:0 6px 16px rgba(37,99,235,.28); }
    .sidebar-brand strong { display:block; color:#f8fafc; font-size:.82rem; line-height:1.1; }
    .sidebar-brand span { color:#7f8da3; font-size:.56rem; }
    .user-chip { display:flex; align-items:center; gap:.5rem; padding:.45rem .55rem; border-radius:9px; background:#162238; color:#dbeafe; font-size:.75rem; margin-bottom:.3rem; }
    .user-dot { width:8px; height:8px; border-radius:50%; background:#34d399; box-shadow:0 0 0 4px rgba(52,211,153,.12); }
    .app-hero {
        overflow:hidden; position:relative; padding:1.35rem 1.55rem; border-radius:14px;
        background:linear-gradient(125deg,#0f172a 0%,#172554 58%,#1e3a8a 100%);
        box-shadow:0 12px 32px rgba(15,23,42,.14); margin:.1rem 0 .8rem;
    }
    .app-hero:after { content:""; position:absolute; width:260px; height:260px; right:-80px; top:-115px; border-radius:50%; background:rgba(96,165,250,.14); }
    .hero-kicker { color:#93c5fd; font-size:.65rem; font-weight:750; letter-spacing:.13em; text-transform:uppercase; }
    .app-hero h1 { color:white; margin:.25rem 0 .3rem; font-size:1.7rem !important; max-width:720px; }
    .app-hero p { color:#cbd5e1; margin:0; max-width:760px; line-height:1.4; font-size:.82rem; }
    .feature-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:.65rem; margin-top:.65rem; }
    .feature-card { background:white; border:1px solid var(--border); border-radius:11px; padding:.75rem .8rem; box-shadow:0 3px 12px rgba(15,23,42,.04); }
    .feature-icon { display:grid; place-items:center; width:28px; height:28px; border-radius:7px; background:#eff6ff; color:#2563eb; font-weight:800; margin-bottom:.45rem; }
    .feature-card strong { color:var(--text); font-size:.84rem; }
    .feature-card p { margin:.2rem 0 0; font-size:.74rem; line-height:1.35; }

    .stButton > button, .stDownloadButton > button {
        min-height: 2.15rem; border-radius: 8px; border: 1px solid var(--border);
        padding-top:.3rem; padding-bottom:.3rem; font-size:.8rem;
        font-weight: 650; box-shadow: 0 1px 2px rgba(15,23,42,.04);
        transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color:#93c5fd; transform:translateY(-1px); box-shadow:0 7px 18px rgba(15,23,42,.08);
    }
    .stButton > button[kind="primary"] { background:linear-gradient(135deg,var(--primary),var(--primary-dark)); border:0; color:white; }
    [data-testid="stSidebar"] .stButton > button {
        background:#162238; color:#dbeafe; border-color:#2a3850; box-shadow:none;
        justify-content:flex-start; min-height:1.8rem; padding:.12rem .48rem;
        border-radius:7px; font-size:.7rem;
    }
    [data-testid="stSidebar"] .stButton > button:hover { background:#1d2b44; border-color:#3b82f6; color:white; }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] { justify-content:center; background:linear-gradient(135deg,#2563eb,#4f46e5); border:0; }
    [data-testid="stSidebar"] div[role="radiogroup"] { gap:.25rem; }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        width:100%; min-height:2rem; display:flex; align-items:center;
        background:#162238; border:1px solid #263650; border-radius:7px; padding:.25rem .42rem;
        font-size:.7rem;
        margin:0; transition:background .15s ease, border-color .15s ease;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label p,
    [data-testid="stSidebar"] .stButton > button p { font-size:.7rem !important; line-height:1.1; margin:0; }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover { background:#1d2b44; border-color:#3b82f6; }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.5rem; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] { font-size:.7rem; margin-bottom:.05rem; }
    [data-testid="stSidebar"] h3 { font-size:.82rem !important; line-height:1.15; margin:.15rem 0 .25rem; }
    [data-testid="stSidebar"] p { line-height:1.25; }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stNumberInput input { min-height:1.9rem; font-size:.72rem; }
    [data-testid="stSidebar"] div[data-baseweb="select"] > div { height:2rem; }
    [data-testid="stSidebar"] .stDateInput [data-baseweb="input"] { height:2rem; }
    [data-testid="stSidebar"] .stCheckbox label { min-height:1.8rem; font-size:.72rem; }

    [data-testid="stMetric"] {
        background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
        padding:.65rem .75rem; box-shadow:0 3px 12px rgba(15,23,42,.04); min-height:82px;
    }
    [data-testid="stMetricLabel"] { color:var(--muted); font-weight:600; font-size:.76rem; }
    [data-testid="stMetricValue"] { color:var(--text); font-size:1.2rem; font-weight:750; letter-spacing:-.025em; }
    [data-testid="stMetricDelta"] { font-size:.72rem; }

    [data-testid="stVerticalBlockBorderWrapper"] { background:var(--surface); border-color:var(--border); border-radius:var(--radius); }
    [data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }
    [data-testid="stPlotlyChart"] { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:.2rem; box-shadow:0 3px 14px rgba(15,23,42,.04); }
    [data-baseweb="tab-list"] { gap:.2rem; background:#e9eef6; padding:.2rem; border-radius:9px; }
    [data-baseweb="tab"] { border-radius:7px; padding:.38rem .7rem; font-size:.8rem; }
    [aria-selected="true"][data-baseweb="tab"] { background:white; box-shadow:0 1px 4px rgba(15,23,42,.1); }
    div[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stDateInput input {
        border-color:var(--border); border-radius:8px; background:var(--surface); min-height:2.15rem; font-size:.8rem;
    }
    [data-testid="stAlert"] { border-radius:9px; border-width:1px; padding:.55rem .75rem; font-size:.8rem; }
    [data-testid="stExpander"] summary { min-height:2.2rem; font-size:.8rem; }
    [data-testid="stDataFrame"] { font-size:.78rem; }
    [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap:.7rem; }
    [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"] { gap:.65rem; }
    [data-testid="stWidgetLabel"] { min-height:auto; margin-bottom:.15rem; font-size:.77rem; }
    [data-stale="true"] { opacity:1 !important; filter:none !important; transition:none !important; pointer-events:auto !important; }
    div[data-testid="stStatusWidget"] { visibility:hidden; display:none; }

    @media (max-width: 900px) { .block-container { padding:2rem 1rem 3rem; } .feature-grid { grid-template-columns:1fr; } .app-hero { padding:1.6rem; } }
</style>
""", unsafe_allow_html=True)

# --- CONTROL DE USUARIOS ---
if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None

if not st.session_state.usuario_actual:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("👋 Bienvenido")
        modo_ingreso = st.radio("¿Qué deseas hacer?", ["Iniciar Sesión", "Soy Nuevo Usuario"])
        
        nombre_input = st.text_input("Nombre de Usuario").strip()
        pass_input = st.text_input("Contraseña", type="password").strip()
        
        if st.button("Acceder", type="primary", use_container_width=True):
            if not nombre_input or not pass_input:
                st.warning("Introduce un nombre de usuario y una contraseña.")
            else:
                if modo_ingreso == "Soy Nuevo Usuario":
                    if crear_usuario(nombre_input, pass_input):
                        st.session_state.usuario_actual = nombre_input
                        st.success("Usuario creado con éxito. Cargando entorno...")
                        st.rerun()
                    else:
                        st.error("El usuario ya existe. Selecciona 'Iniciar Sesión'.")
                else:
                    if verificar_login(nombre_input, pass_input):
                        st.session_state.usuario_actual = nombre_input
                        st.success(f"Bienvenido de nuevo, {nombre_input}!")
                        st.rerun()
                    else:
                        st.error("Usuario no encontrado o contraseña incorrecta. Si eres nuevo, crea una cuenta.")
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

st.sidebar.markdown("""
<div class="sidebar-brand">
  <div class="sidebar-logo">W</div>
  <div><strong>Weinstein Pro</strong><span>QUANT RESEARCH TERMINAL</span></div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown(
    f'<div class="user-chip"><span class="user-dot"></span><span>{st.session_state.usuario_actual}</span></div>',
    unsafe_allow_html=True
)
if st.sidebar.button("Salir"):
    # Limpiamos el usuario actual y los datos en memoria del análisis anterior
    claves_a_borrar = ['usuario_actual', 'df1', 'df2', 't1', 't2', 'df_screener_result', 'mostrar_screener', 'last_error', 'res_portfolio', 'last_portfolio_error']
    for clave in claves_a_borrar:
        if clave in st.session_state:
            del st.session_state[clave]
    st.rerun()

with st.sidebar.container(border=True):
    
    opciones_modo = ["Individual", "Comparativa Multiactivo", "Simulador de Cartera"]
    modo_defecto = perfil_usuario.get('modo_analisis', 'Individual')
    idx_modo = opciones_modo.index(modo_defecto) if modo_defecto in opciones_modo else 0
    
    etiquetas_modo = {
        "Individual": "Individual",
        "Comparativa Multiactivo": "Comparativa",
        "Simulador de Cartera": "Cartera",
    }
    modo_analisis = st.radio(
        "Modo de Análisis", opciones_modo, index=idx_modo,
        format_func=lambda modo: etiquetas_modo[modo]
    )
    
    ticker_1 = ""
    ticker_2 = ""
    
    if modo_analisis != "Simulador de Cartera":
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

    temporalidad = st.selectbox("Temporalidad", options=opciones_temp, index=idx_temp)

    st.markdown("---")
    st.markdown("### 📅 Periodo")
    
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

    fin_actualidad = st.checkbox("Hasta hoy", value=fin_actualidad_defecto)

    if fin_actualidad:
        fecha_fin_sel = pd.Timestamp.now().date()
    else:
        fecha_fin_sel = st.date_input("Fecha de fin", value=fin_defecto, format="DD/MM/YYYY")

    sensibilidad_sma = 30 
    if modo_analisis in ["Individual", "Simulador de Cartera"]:
        st.markdown("---")
        st.markdown("### 🎯 Sensibilidad")
        sensibilidad_defecto = perfil_usuario.get('sensibilidad_sma', 30)
        sensibilidad_sma = st.slider("Media Móvil (SMA)", min_value=10, max_value=100, value=sensibilidad_defecto)

    if modo_analisis != "Simulador de Cartera":
        boton_analizar = st.button("🚀 Ejecutar Análisis", use_container_width=True, type="primary")
    else:
        boton_analizar = False

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
st.sidebar.subheader("🕵️ Vigilancia")
if st.sidebar.button("🔍 Escanear Big Tech", use_container_width=True):
    from screener import ejecutar_escaneo
    tickers_fijos = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "META", "AMZN"]
    with st.sidebar:
        with st.spinner("Escaneando..."):
            st.session_state.df_screener_result = ejecutar_escaneo(tickers_fijos, sensibilidad_sma)
            st.session_state.mostrar_screener = True 

mostrar_sombreado = False

# --- DICCIONARIOS DE PLOTLY EN ESPAÑOL ---
CONFIG_FECHAS = {
    'scrollZoom': True,
    'displaylogo': False,
    'responsive': True,
    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
    'locale': 'es',
    'locales': {
        'es': {
            'format': {
                'months': ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'],
                'shortMonths': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
                'days': ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
                'shortDays': ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
            }
        }
    }
}
CONFIG_ES_NO_ZOOM = dict(CONFIG_FECHAS)
CONFIG_ES_NO_ZOOM['scrollZoom'] = False

COLORES_GRAFICO = ['#2563eb', '#7c3aed', '#059669', '#f59e0b', '#dc2626', '#0891b2']

def aplicar_tema_grafico(fig, altura=None):
    """Aplica una apariencia uniforme y legible a cualquier gráfico Plotly."""
    # Plotly puede renderizar literalmente "undefined" cuando una traza auxiliar
    # no tiene nombre. Estas trazas no deben aparecer en leyendas ni tooltips.
    for traza in fig.data:
        nombre = getattr(traza, 'name', None)
        if nombre is None or str(nombre).strip().lower() in {'', 'none', 'nan', 'undefined'}:
            traza.name = ''
            traza.showlegend = False
    titulo_actual = fig.layout.title.text if fig.layout.title else None
    ajustes = dict(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        colorway=COLORES_GRAFICO,
        font=dict(family='Inter, Segoe UI, sans-serif', color='#334155', size=10),
        hovermode='x unified',
        hoverlabel=dict(bgcolor='#0f172a', bordercolor='#0f172a', font_color='#f8fafc'),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
            bgcolor='rgba(255,255,255,0)', font=dict(size=9)
        ),
        margin=dict(t=46, b=32, l=48, r=20)
    )
    if altura is not None:
        ajustes['height'] = altura
    fig.update_layout(**ajustes)
    if titulo_actual:
        fig.update_layout(title=dict(
            text=titulo_actual, font=dict(size=13, color='#0f172a'),
            x=0.015, xanchor='left'
        ))
    else:
        # No crear un objeto layout.title vacío: algunas versiones de Plotly
        # terminan pintando literalmente "undefined" en la esquina superior.
        fig.update_layout(title=None)

    for anotacion in fig.layout.annotations or ():
        if anotacion.text is None or str(anotacion.text).strip().lower() in {'', 'none', 'nan', 'undefined'}:
            anotacion.visible = False
    fig.update_xaxes(
        showgrid=True, gridcolor='#eef2f7', gridwidth=1, zeroline=False,
        showline=True, linecolor='#e2e8f0', tickfont=dict(color='#64748b'),
        title_font=dict(color='#475569')
    )
    fig.update_yaxes(
        showgrid=True, gridcolor='#eef2f7', gridwidth=1, zeroline=False,
        showline=False, tickfont=dict(color='#64748b'), title_font=dict(color='#475569')
    )
    return fig

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

        st.toast("⏳ Iniciando análisis cuantitativo de Weinstein...", icon="📈")

        with st.spinner("Descargando series, calculando indicadores y ejecutando algoritmo..."):
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

        st.toast("📊 ¡Listo! Renderizando reporte y gráficos interactivos...", icon="🚀")

    # Configuración Visual: se muestra en el sidebar solo si el gráfico a pintar es el individual (df2 es None)
    if st.session_state.get('df1') is not None and st.session_state.get('df2') is None:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🛠️ Configuración Visual")
        mostrar_sombreado = st.sidebar.toggle("Mostrar sombreado de etapas", value=True)
    else:
        mostrar_sombreado = False

# --- 4. RENDERIZADO ---
if modo_analisis == "Simulador de Cartera":
    st.markdown("# 💼 Simulador y Optimizador de Cartera Cuantitativo")
    st.markdown("""
    Este módulo evalúa automáticamente activos candidatos mediante backtesting cuantitativo,
    selecciona los mejores activos para la estrategia de Weinstein Etapa 2
    y simula la evolución monetaria real de la cartera resultante.
    """)
    
    # 1. Panel de selección de activos y parámetros de inversión
    with st.container(border=True):
        st.subheader("⚙️ Configuración de la Cartera")
        
        modo_defecto_cartera = perfil_usuario.get("modo_construccion_cartera", "Automática")
        idx_modo_cartera = 0 if modo_defecto_cartera == "Automática" else 1
        
        modo_construccion = st.radio(
            "Selecciona la modalidad de selección de activos:",
            ["🤖 Selección Automática Inteligente (El algoritmo evalúa y elige los mejores activos)", "✏️ Selección Manual (Personalizada por ti)"],
            index=idx_modo_cartera
        )
        
        es_auto = "Automática" in modo_construccion
        
        if es_auto:
            st.markdown("##### 🤖 Modo Automático Inteligente")

            top_n_cartera = st.number_input(
                "¿Cuántos activos quieres en tu cartera? (Top N):",
                min_value=1,
                max_value=15,
                value=5,
                step=1,
                help="La Teoría Moderna de Carteras (Markowitz) recomienda entre 8 y 12 activos para diversificación óptima del riesgo no sistemático. El algoritmo seleccionará exactamente este número de los mejores candidatos disponibles."
            )

            st.caption(
                f"El algoritmo escaneará **{len(TICKERS_SUGERIDOS)} activos** del universo, "
                f"descartará automáticamente los activos defensivos con baja volatilidad (AAPL, PEP, WMT...) "
                f"mediante un filtro empírico de **volatilidad anualizada ≥ 30%**, y seleccionará los "
                f"**Top {int(top_n_cartera)} activos de alta beta en Etapa 2 con mayor Score combinado**."
            )

            # El pool y el filtro de calidad se aplican internamente en la ejecución
            tickers_finales = TICKERS_SUGERIDOS
        else:
            st.markdown("##### ✏️ Modo Selección Manual")
            tickers_defecto = perfil_usuario.get("tickers_cartera", ["AAPL", "MSFT", "GOOGL"])
            top_n_cartera = len(tickers_defecto)
            tickers_sel = st.multiselect(
                "Selecciona activos sugeridos para tu cartera:",
                options=TICKERS_SUGERIDOS,
                default=[t for t in tickers_defecto if t in TICKERS_SUGERIDOS]
            )
            tickers_manuales = st.text_input(
                "O introduce otros tickers manualmente (separados por comas):",
                value=", ".join([t for t in tickers_defecto if t not in TICKERS_SUGERIDOS])
            )
            tickers_finales = list(set([t.strip().upper() for t in tickers_sel]))
            if tickers_manuales:
                for t in tickers_manuales.split(","):
                    t_clean = t.strip().upper()
                    if t_clean:
                        tickers_finales.append(t_clean)
            tickers_finales = sorted(list(set(tickers_finales)))
            st.write(f"💼 **Activos en Cartera ({len(tickers_finales)}):** {', '.join(tickers_finales) if tickers_finales else 'Ninguno seleccionado'}")
        
        st.markdown("---")
        st.subheader("💵 Parámetros Financieros y Broker")
        col_cap1, col_cap2 = st.columns(2)
        with col_cap1:
            capital_inicial_input = st.number_input(
                "Capital Inicial ($):",
                min_value=100.0,
                max_value=10000000.0,
                value=float(perfil_usuario.get("capital_inicial_cartera", 10000.0)),
                step=1000.0,
                help="Monto total de dinero a repartir de forma uniforme entre los activos de la cartera."
            )
        with col_cap2:
            comision_input = st.number_input(
                "Comisión por Operación ($):",
                min_value=0.0,
                max_value=500.0,
                value=float(perfil_usuario.get("comision_cartera", 1.0)),
                step=0.5,
                help="Comisión simbólica o fija que cobra el broker por cada operación realizada (compra o venta)."
            )

        st.markdown("---")
        st.subheader("📅 Periodo de Simulación de la Cartera")
        st.info("💡 **Recomendación Algorítmica:** El periodo de simulación óptimo para capturar ciclos macroeconómicos completos con la estrategia de Weinstein es de **3 a 5 años** (con re-optimización recomendada cada **2 a 3 años** para adaptarse a los cambios de régimen y nuevos líderes de mercado).")
        
        # Cargar rango guardado
        tipo_rango_defecto = perfil_usuario.get("tipo_rango_cartera", "Últimos N años")
        idx_rango = ["Últimos N años", "Fechas personalizadas del panel lateral"].index(tipo_rango_defecto) if tipo_rango_defecto in ["Últimos N años", "Fechas personalizadas del panel lateral"] else 0
        
        tipo_rango = st.radio(
            "Selecciona cómo definir el periodo de tiempo:",
            ["Últimos N años", "Fechas personalizadas del panel lateral"],
            index=idx_rango
        )
        
        if tipo_rango == "Últimos N años":
            anios_defecto = perfil_usuario.get("anios_cartera", 3)
            anios_simular = st.slider("Años a simular (Recomendado: 3 a 5 años):", min_value=1, max_value=10, value=anios_defecto)
            fecha_fin_sel_cartera = pd.Timestamp.now().date()
            fecha_inicio_sel_cartera = fecha_fin_sel_cartera - pd.Timedelta(days=int(anios_simular * 365.25))
        else:
            fecha_inicio_sel_cartera = fecha_inicio_sel
            fecha_fin_sel_cartera = fecha_fin_sel
            anios_simular = 3

        # Botón para ejecutar la simulación
        texto_boton = "🚀 Optimizar y Simular Cartera Automática" if es_auto else "🚀 Ejecutar Simulación de Cartera Manual"
        boton_simular = st.button(texto_boton, type="primary", use_container_width=True)

    if boton_simular:
        if not tickers_finales:
            st.error("⚠️ Por favor, selecciona o introduce al menos un ticker para evaluar.")
        else:
            # Guardar preferencias
            actualizar_usuario(st.session_state.usuario_actual, {
                "modo_construccion_cartera": "Automática" if es_auto else "Manual",
                "candidatos_cartera": tickers_finales if es_auto else perfil_usuario.get("candidatos_cartera", []),
                "tickers_cartera": tickers_finales if not es_auto else perfil_usuario.get("tickers_cartera", []),
                "top_n_cartera": top_n_cartera,
                "capital_inicial_cartera": capital_inicial_input,
                "comision_cartera": comision_input,
                "temporalidad": temporalidad,
                "sensibilidad_sma": sensibilidad_sma,
                "modo_analisis": modo_analisis,
                "tipo_rango_cartera": tipo_rango,
                "anios_cartera": anios_simular,
                "fecha_inicio": str(fecha_inicio_sel_cartera),
                "fin_actualidad": True if tipo_rango == "Últimos N años" else fin_actualidad,
                "fecha_fin": str(fecha_fin_sel_cartera)
            })
            
            st.session_state.last_portfolio_error = None
            if 'res_portfolio' in st.session_state:
                del st.session_state.res_portfolio
                
            map_int = {"1 Hora": "60m", "1 Día": "1d", "1 Semana": "1wk"}
            interval = map_int[temporalidad]
            
            try:
                if interval == "60m":
                    limite_yahoo = pd.Timestamp.now().date() - pd.Timedelta(days=729)
                    if fecha_inicio_sel_cartera < limite_yahoo:
                        raise ValueError(f"Para la temporalidad de '1 Hora', Yahoo Finance solo permite descargar datos de los últimos 2 años (desde el {limite_yahoo.strftime('%d/%m/%Y')}). Por favor, ajusta la Fecha de inicio.")
                
                msg_toast = "⏳ Evaluando candidatos y optimizando cartera..." if es_auto else "⏳ Iniciando simulación de portafolio..."
                st.toast(msg_toast, icon="💼")
                with st.status("Ejecutando simulador de cartera...", expanded=True) as status:
                    def update_progress(msg):
                        status.write(msg)
                        
                    if es_auto:
                        # Fase 1: Screener automático — filtra el universo por criterios de calidad Weinstein
                        update_progress(f"🔍 Escaneando universo de {len(tickers_finales)} activos con filtros de calidad Weinstein...")
                        df_scan = ejecutar_escaneo(tickers_finales, periodo_sma=sensibilidad_sma,
                                                   inicio=str(fecha_inicio_sel_cartera), fin=str(fecha_fin_sel_cartera))
                        candidatos_filtrados = tickers_finales  # fallback si el screener no da resultados
                        if not df_scan.empty:
                            candidatos_filtrados_list = filtrar_candidatos_alta_beta(df_scan)
                            if candidatos_filtrados_list:
                                candidatos_filtrados = candidatos_filtrados_list
                                descartados = len(tickers_finales) - len(candidatos_filtrados)
                                update_progress(f"✅ Screener completado: {len(candidatos_filtrados)} activos de alta beta seleccionados. {descartados} activos defensivos descartados (volatilidad anualizada < 25%). Evaluando Score histórico para seleccionar Top {top_n_cartera}...")
                            else:
                                update_progress("⚠️ Ningún activo superó los filtros de calidad. Se usará el universo completo como fallback.")
                        # Fase 2: Backtest y selección Top N
                        res = optimizar_y_simular_cartera(
                            lista_candidatos=candidatos_filtrados,
                            top_n=top_n_cartera,
                            inicio=str(fecha_inicio_sel_cartera),
                            fin=str(fecha_fin_sel_cartera),
                            interval=interval,
                            sensibilidad_sma=sensibilidad_sma,
                            progress_callback=update_progress,
                            capital_inicial=capital_inicial_input,
                            comision_por_op=comision_input
                        )
                    else:
                        res = simular_cartera(
                            lista_tickers=tickers_finales,
                            inicio=str(fecha_inicio_sel_cartera),
                            fin=str(fecha_fin_sel_cartera),
                            interval=interval,
                            sensibilidad_sma=sensibilidad_sma,
                            progress_callback=update_progress,
                            capital_inicial=capital_inicial_input,
                            comision_por_op=comision_input
                        )
                    st.session_state.res_portfolio = res
                    status.update(label="💼 ¡Simulación finalizada con éxito!", state="complete", expanded=False)
                st.toast("🚀 ¡Listo! Mostrando resultados de la cartera...", icon="📊")
                st.rerun()
            except Exception as e:
                st.session_state.last_portfolio_error = f"❌ Error en la simulación: {e}"
                st.error(st.session_state.last_portfolio_error)

    if st.session_state.get('last_portfolio_error'):
        st.error(st.session_state.last_portfolio_error)
        
    elif 'res_portfolio' in st.session_state:
        res = st.session_state.res_portfolio
        metrics = res['metricas_globales']
        resumen_df = res['resumen_tickers_df']
        
        st.markdown("---")
        
        # Si fue una cartera optimizada de forma automática, mostrar los ganadores destacados
        if 'selected_tickers' in res:
            st.success(f"🏆 **Activos seleccionados automáticamente por el algoritmo ({len(res['selected_tickers'])}):** {', '.join(res['selected_tickers'])}")
            
        st.subheader("📈 Rendimiento Agregado del Portafolio")
        
        # Render KPIs resumen
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        
        cap_ini = metrics.get('capital_inicial', 10000.0)
        cap_fin = metrics.get('capital_final', cap_ini)
        ganancia = metrics.get('ganancia_neta', cap_fin - cap_ini)
        tot_com = metrics.get('tot_comisiones', 0.0)
        com_op = metrics.get('comision_por_op', 1.0)
        
        delta_cap_str = f"{ganancia:+.2f} $ ({metrics['total_ret']:+.2f}%)"
        
        col_m1.metric("Capital Inicial", f"${cap_ini:,.2f}")
        col_m2.metric("Capital Final", f"${cap_fin:,.2f}", delta=delta_cap_str)
        col_m3.metric("Rent. Algoritmo", f"{metrics['total_ret']:.2f}%", delta=f"{metrics['total_ret'] - metrics['bh_ret']:.2f}% vs B&H")
        col_m4.metric("Comisiones Pagadas", f"${tot_com:,.2f}", delta=f"${com_op:.2f} / op", delta_color="inverse")
        col_m5.metric("Max Drawdown", f"{metrics['max_drawdown']:.2f}%", help=f"Ops Totales: {metrics['num_ops']} (Win Rate: {metrics['win_rate']:.1f}%)")
        
        # Gráfica de Equidad de la Cartera
        fig_eq = go.Figure()
        eq_df = res['portfolio_equity_df']
        fig_eq.add_trace(go.Scatter(
            x=eq_df['Fecha'], 
            y=eq_df['Equity_Portfolio'], 
            fill='tozeroy', 
            line_color='#2ca02c', 
            name="Capital Portafolio ($)",
            hovertemplate="<b>Fecha:</b> %{x}<br><b>Capital:</b> $%{y:,.2f}<extra></extra>"
        ))
        fig_eq.update_layout(
            title=f"Evolución del Capital de la Cartera (Capital Inicial: ${cap_ini:,.2f} | Comisiones Totales: ${tot_com:,.2f})", 
            height=320,
            dragmode='pan',
            hovermode='x unified',
            yaxis=dict(title="Capital Total ($)", tickprefix="$", tickformat=",.0f"),
            margin=dict(t=40, b=30, l=50, r=50)
        )
        aplicar_tema_grafico(fig_eq, 330)
        st.plotly_chart(fig_eq, use_container_width=True, config=CONFIG_ES_NO_ZOOM, theme=None)
        
        # Tabla de evaluación de candidatos (si fue optimización automática)
        if 'evaluacion_candidatos_df' in res:
            st.subheader("🎯 Clasificación de Candidatos y Dictamen de Reasignación")
            st.markdown("El algoritmo evalúa el conjunto de candidatos y emite dictámenes explícitos de selección y reasignación de capital por coste de oportunidad:")
            st.dataframe(res['evaluacion_candidatos_df'], use_container_width=True, hide_index=True)
                
        # Tabla detallada por activo
        st.subheader("📋 Desglose Operativo por Activo Integrado")
        st.markdown("Resultados individuales para cada uno de los activos agregados en la cartera:")
        
        st.dataframe(resumen_df, use_container_width=True, hide_index=True)
        
        # Desplegable con el historial cronológico completo de operaciones
        if 'historial_operaciones_df' in res and not res['historial_operaciones_df'].empty:
            with st.expander("📜 Ver Registro Detallado de Operaciones (Compras, Ventas, Capital y Razón de Salida)", expanded=False):
                st.markdown("Historial cronológico de todas las transacciones ejecutadas por el algoritmo en la cartera:")
                st.dataframe(res['historial_operaciones_df'], use_container_width=True, hide_index=True)
        
        # Exportaciones
        st.subheader("📥 Exportación de Resultados")
        col_exp1, col_exp2 = st.columns(2)
        csv_data = resumen_df.to_csv(index=False).encode('utf-8')
        col_exp1.download_button(
            "📥 Descargar Tabla Resumen (CSV)", 
            csv_data, 
            "resumen_cartera.csv", 
            "text/csv", 
            use_container_width=True
        )
        eq_csv_data = eq_df.to_csv(index=False).encode('utf-8')
        col_exp2.download_button(
            "📥 Descargar Curva de Equidad (CSV)", 
            eq_csv_data, 
            "curva_equidad_cartera.csv", 
            "text/csv", 
            use_container_width=True
        )

elif st.session_state.mostrar_screener and 'df_screener_result' in st.session_state:
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
        # Calcular señales de compra/venta para marcar en los gráficos (Lógica Weinstein)
        res_b1 = ejecutar_backtest_desde_df(df1)
        df1_sig = res_b1['df_signal']
        compras_1 = df1_sig[df1_sig['Posicion'] == 1]
        ventas_1 = df1_sig[df1_sig['Posicion'] == -1]

        if df2 is not None:
            res_b2 = ejecutar_backtest_desde_df(df2)
            df2_sig = res_b2['df_signal']
            compras_2 = df2_sig[df2_sig['Posicion'] == 1]
            ventas_2 = df2_sig[df2_sig['Posicion'] == -1]

        paneles = sum([ver_p, ver_m, ver_r])
        if paneles > 0:
            alturas = []
            if ver_p: alturas.append(0.5 if paneles > 1 else 1.0)
            if ver_m: alturas.append(0.25 if paneles > 1 else 1.0)
            if ver_r: alturas.append(0.25 if paneles > 1 else 1.0)
            
            titulos_panel = []
            if ver_p: titulos_panel.append(f"Precio · {t1}" + (f" vs {t2}" if df2 is not None else ""))
            if ver_m: titulos_panel.append("Fuerza relativa · Mansfield")
            if ver_r: titulos_panel.append("Momentum · RSI (14)")
            fig = make_subplots(
                rows=paneles, cols=1, shared_xaxes=True, vertical_spacing=0.09,
                row_width=alturas[::-1], subplot_titles=titulos_panel
            )
            
            f = 1
            if ver_p:
                if df2 is None:
                    fig.add_trace(go.Candlestick(
                        x=df1.index, open=df1['Open'], high=df1['High'], low=df1['Low'], close=df1['Close'],
                        name=f"Precio {t1}", showlegend=True, increasing_line_color='#10b981', decreasing_line_color='#ef4444',
                        increasing_fillcolor='rgba(16,185,129,.72)', decreasing_fillcolor='rgba(239,68,68,.72)',
                        hovertemplate=(
                            f"<b>{t1}</b> · %{{x|%d %b %Y}}<br>"
                            "Apertura&nbsp;&nbsp;%{open:$,.2f}<br>"
                            "Máximo&nbsp;&nbsp;&nbsp;&nbsp;%{high:$,.2f}<br>"
                            "Mínimo&nbsp;&nbsp;&nbsp;&nbsp;%{low:$,.2f}<br>"
                            "Cierre&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;%{close:$,.2f}<extra></extra>"
                        ),
                        hovertemplatefallback=False
                    ), row=f, col=1)
                    fig.add_trace(go.Scatter(
                        x=df1.index, y=df1['SMA_30'], line=dict(color='#f59e0b', width=2),
                        name=f"SMA {st.session_state.current_sma}",
                        hovertemplate=f"<b>SMA {st.session_state.current_sma}</b><br>%{{x|%d %b %Y}}<br>%{{y:$,.2f}}<extra></extra>"
                    ), row=f, col=1)
                    
                    # Puntos de compra/venta en precio
                    fig.add_trace(go.Scatter(x=compras_1.index, y=compras_1['Close'], mode='markers', marker=dict(color='#059669', size=11, symbol='triangle-up', line=dict(color='white', width=1)), name="Compra"), row=f, col=1)
                    fig.add_trace(go.Scatter(x=ventas_1.index, y=ventas_1['Close'], mode='markers', marker=dict(color='#dc2626', size=11, symbol='triangle-down', line=dict(color='white', width=1)), name="Venta"), row=f, col=1)
                else:
                    fig.add_trace(go.Scatter(x=df1.index, y=df1['Close'], name=t1, line=dict(width=1.5)), row=f, col=1)
                    fig.add_trace(go.Scatter(x=df2.index, y=df2['Close'], name=t2, line=dict(width=1.5, dash='dot')), row=f, col=1)
                    
                    # Puntos de compra/venta comparativos t1
                    fig.add_trace(go.Scatter(x=compras_1.index, y=compras_1['Close'], mode='markers', marker=dict(color='green', size=10, symbol='triangle-up'), name=f"Compra {t1}"), row=f, col=1)
                    fig.add_trace(go.Scatter(x=ventas_1.index, y=ventas_1['Close'], mode='markers', marker=dict(color='red', size=10, symbol='triangle-down'), name=f"Venta {t1}"), row=f, col=1)
                    # Puntos de compra/venta comparativos t2
                    fig.add_trace(go.Scatter(x=compras_2.index, y=compras_2['Close'], mode='markers', marker=dict(color='lightgreen', size=10, symbol='triangle-up'), name=f"Compra {t2}"), row=f, col=1)
                    fig.add_trace(go.Scatter(x=ventas_2.index, y=ventas_2['Close'], mode='markers', marker=dict(color='pink', size=10, symbol='triangle-down'), name=f"Venta {t2}"), row=f, col=1)
                
                if mostrar_sombreado and df2 is None:
                    start_idx = 1
                    current_color = ""
                    for i in range(1, len(df1)):
                        e = df1.iloc[i]['Etapa']
                        color = "rgba(16,185,129,.045)" if "2" in e else "rgba(239,68,68,.04)" if "4" in e else "rgba(245,158,11,.04)" if "3" in e else ""
                        
                        if color != current_color:
                            if current_color != "":
                                fig.add_vrect(x0=df1.index[start_idx-1], x1=df1.index[i-1], fillcolor=current_color, line_width=0, layer="below", row=f, col=1)
                            current_color = color
                            start_idx = i
                    if current_color != "":
                        fig.add_vrect(x0=df1.index[start_idx-1], x1=df1.index[-1], fillcolor=current_color, line_width=0, layer="below", row=f, col=1)
                
                fig.update_yaxes(title_text="Precio ($)", tickprefix="$", row=f, col=1)
                f += 1
            if ver_m:
                fig.add_trace(go.Scatter(x=df1.index, y=df1['Mansfield'], name=f"MF {t1}", fill='tozeroy', line=dict(color='#2563eb', width=2), fillcolor='rgba(37,99,235,.10)'), row=f, col=1)
                if df2 is not None:
                    fig.add_trace(go.Scatter(x=df2.index, y=df2['Mansfield'], name=f"MF {t2}", line=dict(dash='dot', color='#0891b2', width=2)), row=f, col=1)
                fig.add_hline(y=0, line_dash="dash", line_color='#94a3b8', line_width=1, row=f, col=1)
                fig.update_yaxes(title_text="Mansfield", row=f, col=1)
                f += 1
            if ver_r:
                fig.add_trace(go.Scatter(x=df1.index, y=df1['RSI'], name=f"RSI {t1}", line=dict(color='#7c3aed', width=2)), row=f, col=1)
                if df2 is not None:
                    fig.add_trace(go.Scatter(x=df2.index, y=df2['RSI'], name=f"RSI {t2}", line=dict(dash='dot', color='#ec4899', width=2)), row=f, col=1)
                fig.add_hrect(y0=70, y1=100, fillcolor='rgba(239,68,68,.055)', line_width=0, layer='below', row=f, col=1)
                fig.add_hrect(y0=0, y1=30, fillcolor='rgba(16,185,129,.055)', line_width=0, layer='below', row=f, col=1)
                fig.add_hline(y=70, line_dash='dash', line_color='#f87171', line_width=1, row=f, col=1)
                fig.add_hline(y=30, line_dash='dash', line_color='#34d399', line_width=1, row=f, col=1)
                fig.update_yaxes(title_text="RSI", range=[0, 100], row=f, col=1)
            
            fig.update_layout(height=650, dragmode='pan', hovermode='x', margin=dict(t=24, b=24, l=42, r=36))
            
            fig.update_xaxes(showticklabels=True)
            
            fig.update_xaxes(row=1, col=1, rangeslider_visible=False)
            fig.update_xaxes(row=paneles, col=1, rangeslider_visible=False, title_text="Fecha")
            fig.update_yaxes(fixedrange=False)
            aplicar_tema_grafico(fig, 650)
            fig.update_layout(
                hovermode='x', showlegend=True,
                legend=dict(
                    orientation='h', yanchor='bottom', y=1.025,
                    xanchor='left', x=0, traceorder='normal',
                    bgcolor='rgba(255,255,255,.92)', bordercolor='#e2e8f0', borderwidth=1,
                    font=dict(size=9, color='#475569')
                )
            )
            fig.update_annotations(font=dict(size=11, color='#334155'), x=0, xanchor='left')
            
            st.plotly_chart(
                fig, use_container_width=True, config=CONFIG_FECHAS,
                theme=None, key=f"grafico_tecnico_{t1}_{t2 or 'individual'}"
            )

    with tab2:
        if df2 is None:
            res = ejecutar_backtest_desde_df(df1)
            st.subheader("🧪 Validación Científica")
            c_b1, c_b2, c_b3, c_b4 = st.columns(4); c_b1.metric("Win Rate", f"{res['win_rate']:.1f}%"); c_b2.metric("Rent. Sistema", f"{res['total_ret']:.1f}%"); c_b3.metric("Rent. B&H", f"{res['bh_ret']:.1f}%"); c_b4.metric("Drawdown", f"{res['max_drawdown']:.1f}%")
            fig_eq = go.Figure(); fig_eq.add_trace(go.Scatter(x=res['equity_df']['Fecha'], y=res['equity_df']['Equity'], fill='tozeroy', line_color='#059669', fillcolor='rgba(5,150,105,.10)', name="Capital"))
            fig_eq.update_layout(title="Curva de Equidad (Backtesting)", height=245)
            aplicar_tema_grafico(fig_eq, 250)
            
            st.plotly_chart(fig_eq, use_container_width=True, config=CONFIG_ES_NO_ZOOM, theme=None)
            
            pdf = generar_pdf(t1, st.session_state.temp_label, u1['Close'], u1['SMA_30'], u1['Mansfield'], u1['RSI'], obtener_texto_señal(t1, df1), res, st.session_state.current_sma)
            col_exp1, col_exp2 = st.columns(2); col_exp1.download_button(f"📄 PDF {t1}", pdf, f"{t1}.pdf"); col_exp2.download_button(f"📥 CSV {t1}", df1.to_csv().encode('utf-8'), f"{t1}.csv")
            st.dataframe(df1.style.format(precision=2), use_container_width=True)
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader(f"📊 {t1}"); res1 = ejecutar_backtest_desde_df(df1); fig_eq1 = go.Figure(); fig_eq1.add_trace(go.Scatter(x=res1['equity_df']['Fecha'], y=res1['equity_df']['Equity'], fill='tozeroy', line_color='#2563eb', fillcolor='rgba(37,99,235,.10)'))
                fig_eq1.update_layout(title=f"Equidad {t1}", height=200)
                aplicar_tema_grafico(fig_eq1, 210)
                
                st.plotly_chart(fig_eq1, use_container_width=True, config=CONFIG_ES_NO_ZOOM, theme=None)
                
                pdf1 = generar_pdf(t1, st.session_state.temp_label, df1.iloc[-1]['Close'], df1.iloc[-1]['SMA_30'], df1.iloc[-1]['Mansfield'], df1.iloc[-1]['RSI'], obtener_texto_señal(t1, df1), res1, st.session_state.current_sma)
                st.download_button(f"📄 PDF {t1}", pdf1, f"{t1}.pdf"); st.download_button(f"📥 CSV {t1}", df1.to_csv().encode('utf-8'), f"{t1}.csv"); st.dataframe(df1.tail(30), use_container_width=True)
            with col_b:
                st.subheader(f"📊 {t2}"); res2 = ejecutar_backtest_desde_df(df2); fig_eq2 = go.Figure(); fig_eq2.add_trace(go.Scatter(x=res2['equity_df']['Fecha'], y=res2['equity_df']['Equity'], fill='tozeroy', line_color='#7c3aed', fillcolor='rgba(124,58,237,.10)'))
                fig_eq2.update_layout(title=f"Equidad {t2}", height=200)
                aplicar_tema_grafico(fig_eq2, 210)
                
                st.plotly_chart(fig_eq2, use_container_width=True, config=CONFIG_ES_NO_ZOOM, theme=None)
                
                pdf2 = generar_pdf(t2, st.session_state.temp_label, df2.iloc[-1]['Close'], df2.iloc[-1]['SMA_30'], df2.iloc[-1]['Mansfield'], df2.iloc[-1]['RSI'], obtener_texto_señal(t2, df2), res2, st.session_state.current_sma)
                st.download_button(f"📄 PDF {t2}", pdf2, f"{t2}.pdf"); st.download_button(f"📥 CSV {t2}", df2.to_csv().encode('utf-8'), f"{t2}.csv"); st.dataframe(df2.tail(30), use_container_width=True)

else:
    st.markdown("""
    <section class="app-hero">
        <div class="hero-kicker">Research workspace</div>
        <h1>Decisiones de inversión respaldadas por datos.</h1>
        <p>Analiza tendencias, fuerza relativa y momentum con la metodología de Weinstein. Configura tu primer estudio desde el panel lateral para comenzar.</p>
    </section>
    <div class="feature-grid">
        <div class="feature-card"><div class="feature-icon">01</div><strong>Tendencia</strong><p>Identifica etapas de mercado mediante medias móviles y estructura de precio.</p></div>
        <div class="feature-card"><div class="feature-icon">02</div><strong>Fuerza relativa</strong><p>Compara cada activo con el S&amp;P 500 utilizando el indicador Mansfield.</p></div>
        <div class="feature-card"><div class="feature-icon">03</div><strong>Validación</strong><p>Contrasta señales con RSI, backtesting y métricas de riesgo consistentes.</p></div>
    </div>
    """, unsafe_allow_html=True)
