from fpdf import FPDF
import datetime

class InformeWeinstein(FPDF):
    def header(self):
        # Fondo oscuro profesional para la cabecera
        self.set_fill_color(30, 39, 46) 
        self.rect(0, 0, 210, 35, 'F')
        
        # Título principal
        self.set_y(10)
        self.set_font('Arial', 'B', 20)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'WEINSTEIN ANALYTICS PRO', 0, 1, 'C')
        
        # Subtítulo
        self.set_font('Arial', 'I', 10)
        self.set_text_color(189, 195, 199)
        self.cell(0, 6, 'Reporte Cuantitativo y Analisis de Etapas', 0, 1, 'C')
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()} | Generado el {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")} | Uso Academico', 0, 0, 'C')

    def section_title(self, title):
        self.ln(5)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(41, 128, 185) # Azul corporativo
        self.cell(0, 8, title.upper(), 'B', 1, 'L')
        self.ln(4)

    def draw_stage_diagram(self):
        """Dibuja una infografía de las etapas de Weinstein con estilo profesional"""
        self.section_title("4. Referencia Visual del Ciclo de Mercado")
        
        x_start = 25
        y_base = self.get_y() + 25
        
        # Dibujar eje base
        self.set_draw_color(200, 200, 200)
        self.line(x_start, y_base + 5, x_start + 160, y_base + 5) 
        
        # Dibujar la curva de la media móvil
        self.set_draw_color(41, 128, 185)
        self.set_line_width(1)
        self.line(x_start, y_base, x_start+30, y_base)          # Etapa 1
        self.line(x_start+30, y_base, x_start+70, y_base-30)    # Etapa 2
        self.line(x_start+70, y_base-30, x_start+100, y_base-30)# Etapa 3
        self.line(x_start+100, y_base-30, x_start+140, y_base)  # Etapa 4
        
        # Nodos marcadores de etapas
        self.set_fill_color(255, 255, 255)
        self.set_font('Arial', 'B', 8)
        self.set_text_color(50, 50, 50)
        
        # Nodo E1 (Gris)
        self.set_draw_color(150, 150, 150)
        self.ellipse(x_start+12, y_base-2, 4, 4, 'DF')
        self.text(x_start+8, y_base+12, "ETAPA 1: Suelo")
        
        # Nodo E2 (Verde)
        self.set_draw_color(39, 174, 96) 
        self.ellipse(x_start+50, y_base-17, 4, 4, 'DF')
        self.text(x_start+42, y_base-20, "ETAPA 2: Alcista")
        
        # Nodo E3 (Naranja)
        self.set_draw_color(243, 156, 18) 
        self.ellipse(x_start+83, y_base-32, 4, 4, 'DF')
        self.text(x_start+78, y_base-35, "ETAPA 3: Techo")
        
        # Nodo E4 (Rojo)
        self.set_draw_color(192, 57, 43) 
        self.ellipse(x_start+120, y_base-17, 4, 4, 'DF')
        self.text(x_start+115, y_base-20, "ETAPA 4: Bajista")
        
        self.set_line_width(0.2) # Reset de línea
        self.ln(45)

def generar_pdf(ticker, temp, precio, sma, mf, rsi, señal, backtest, sma_periodo):
    pdf = InformeWeinstein()
    pdf.add_page()
    
    # --- 1. PERFIL DEL ACTIVO ---
    pdf.section_title("1. Perfil del Activo y Datos de Mercado")
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(220, 220, 220)
    pdf.set_text_color(40, 40, 40)
    
    # Fila 1 de datos
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(45, 8, " Activo Analizado:", "LT", 0, "L", True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 8, f" {ticker}", "TR", 0, "L")
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(45, 8, " Temporalidad:", "LT", 0, "L", True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 8, f" {temp}", "TR", 1, "L")
    
    # Fila 2 de datos
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(45, 8, " Precio de Cierre:", "L", 0, "L", True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 8, f" {precio:.2f} $", "R", 0, "L")
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(45, 8, f" SMA ({sma_periodo} per.):", "L", 0, "L", True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 8, f" {sma:.2f} $", "R", 1, "L")
    
    # Fila 3 de datos
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(45, 8, " Fuerza Mansfield:", "LB", 0, "L", True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 8, f" {mf:.2f}", "RB", 0, "L")
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(45, 8, " RSI (14 per.):", "LB", 0, "L", True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(50, 8, f" {rsi:.2f}", "RB", 1, "L")
    
    # --- 2. DICTAMEN ALGORITMICO ---
    pdf.section_title("2. Resolucion del Algoritmo")
    
    # Lógica de colores dinámicos
    if "COMPRA" in señal:
        color_fondo = (234, 250, 234) # Verde claro
        color_texto = (39, 174, 96)   # Verde oscuro
    elif "VENTA" in señal:
        color_fondo = (253, 235, 236) # Rojo claro
        color_texto = (192, 57, 43)   # Rojo oscuro
    else:
        color_fondo = (252, 243, 207) # Amarillo claro
        color_texto = (211, 84, 0)    # Naranja oscuro
        
    pdf.set_fill_color(*color_fondo)
    pdf.set_text_color(*color_texto)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 12, f"DICTAMEN TECNICO: {señal.upper()}", 1, 1, 'C', fill=True)
    pdf.ln(3)
    
    # Texto justificativo automático
    pdf.set_text_color(60, 60, 60)
    pdf.set_font('Arial', '', 10)
    tendencia = "alcista" if precio > sma else "bajista"
    momentum = "fuerza relativa positiva frente al S&P 500" if mf > 0 else "debilidad relativa frente al mercado"
    texto_justificacion = (
        f"El motor cuantitativo ha analizado la accion de precio de {ticker}. Actualmente cotiza a {precio:.2f} $, "
        f"situandose en una tendencia de medio plazo {tendencia} al estar {'por encima' if tendencia=='alcista' else 'por debajo'} "
        f"de su media movil de {sma_periodo} periodos ({sma:.2f} $). Ademas, el indicador Mansfield ({mf:.2f}) muestra "
        f"una clara {momentum}. Con un RSI de {rsi:.2f}, el algoritmo determina: {señal}."
    )
    pdf.multi_cell(0, 6, texto_justificacion)
    
    # --- 3. GLOSARIO DE INDICADORES ---
    pdf.section_title("3. Glosario de Indicadores Tecnicos")
    
    # Explicación Mansfield
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 6, "Fuerza Relativa de Mansfield:", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(60, 60, 60)
    texto_mf = ("Mide el desempeño del activo comparado directamente con un indice de referencia global (como el S&P 500). "
                "Un valor superior a 0 significa que el activo esta batiendo al mercado y atrayendo capital institucional. "
                "En la metodologia de Weinstein, NUNCA se debe comprar un activo con un Mansfield negativo, sin importar "
                "lo atractiva que parezca la grafica.")
    pdf.multi_cell(0, 5, texto_mf)
    pdf.ln(2)
    
    # Explicación RSI
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 6, "RSI (Relative Strength Index):", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(60, 60, 60)
    texto_rsi = ("Oscilador de momentum que mide la velocidad y magnitud de los cambios de precio recientes. "
                 "Permite evaluar si el activo tiene fuerza impulsiva o si, por el contrario, la tendencia esta agotada. "
                 "Valores extremos pueden advertir de niveles de sobrecompra (por encima de 70) o sobreventa (por debajo de 30).")
    pdf.multi_cell(0, 5, texto_rsi)
    
    # --- 4. INFOGRAFIA VISUAL ---
    pdf.draw_stage_diagram()
    
    # --- 5. BACKTESTING Y MÉTRICAS ---
    pdf.section_title("5. Estadisticas de Backtesting (Estrategia Etapa 2)")
    pdf.set_fill_color(41, 128, 185)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 10)
    
    # Cabecera tabla de resultados
    pdf.cell(47, 8, "Metrica de Riesgo", 1, 0, 'C', True)
    pdf.cell(48, 8, "Resultado Algoritmo", 1, 0, 'C', True)
    pdf.cell(47, 8, "Metrica de Control", 1, 0, 'C', True)
    pdf.cell(48, 8, "Buy & Hold", 1, 1, 'C', True)
    
    pdf.set_text_color(40, 40, 40)
    pdf.set_font('Arial', '', 10)
    
    # Datos Backtesting Fila 1
    pdf.cell(47, 8, " Nro. Operaciones", 1)
    pdf.cell(48, 8, f" {backtest['num_ops']}", 1, 0, 'C')
    pdf.cell(47, 8, " Rentabilidad Total", 1)
    pdf.cell(48, 8, f" {backtest['bh_ret']:.2f}%", 1, 1, 'C')
    
    # Datos Backtesting Fila 2 (Con resaltado de rentabilidad)
    pdf.cell(47, 8, " Win Rate (Acierto)", 1)
    pdf.cell(48, 8, f" {backtest['win_rate']:.2f}%", 1, 0, 'C')
    pdf.cell(47, 8, " Rent. del Sistema", 1)
    
    # Color dinámico para la rentabilidad de nuestro sistema
    if backtest['total_ret'] > 0:
        pdf.set_text_color(39, 174, 96); pdf.set_font('Arial', 'B', 10)
    else:
        pdf.set_text_color(192, 57, 43); pdf.set_font('Arial', 'B', 10)
        
    pdf.cell(48, 8, f" {backtest['total_ret']:.2f}%", 1, 1, 'C')
    
    # Datos Backtesting Fila 3
    pdf.set_text_color(40, 40, 40)
    pdf.set_font('Arial', '', 10)
    pdf.cell(47, 8, " Drawdown Maximo", 1)
    pdf.cell(48, 8, f" {backtest['max_drawdown']:.2f}%", 1, 0, 'C')
    pdf.cell(47, 8, " Datos Evaluados", 1)
    pdf.cell(48, 8, " Historico Completo", 1, 1, 'C')
    
    # Disclaimer legal / Académico
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.multi_cell(0, 4, "Aviso legal: Este informe ha sido generado automaticamente por la Terminal Weinstein Pro. "
                         "Los resultados de backtesting historico no garantizan rendimientos futuros. Este documento "
                         "esta diseñado con fines estrictamente academicos (Trabajo de Fin de Grado) y de investigacion.")

    return pdf.output(dest='S').encode('latin-1')
