from fpdf import FPDF
import datetime

class InformeWeinstein(FPDF):
    def header(self):
        # Cabecera institucional
        self.set_fill_color(41, 128, 185) # Azul profesional
        self.rect(0, 0, 210, 40, 'F')
        self.set_font('Arial', 'B', 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 15, 'WEINSTEIN ANALYTICS PRO', 0, 1, 'C')
        self.set_font('Arial', 'I', 9)
        self.cell(0, -2, 'Reporte de Analisis Algoritmico de Activos', 0, 1, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()} - Generado el {datetime.datetime.now().strftime("%d/%m/%Y")}', 0, 0, 'C')

    def draw_stage_diagram(self):
        """Dibuja la infografia de las etapas de Weinstein"""
        self.ln(5)
        self.set_font('Arial', 'B', 10)
        self.set_text_color(60, 60, 60)
        self.cell(0, 10, "Referencia Visual del Modelo de Etapas:", 0, 1)
        
        x_start = 30
        y_base = self.get_y() + 15
        self.set_draw_color(100, 100, 100)
        self.set_line_width(0.6)
        
        # Dibujo de la curva del ciclo (Etapas 1-2-3-4)
        self.line(x_start, y_base, x_start+25, y_base) # E1
        self.line(x_start+25, y_base, x_start+60, y_base-20) # E2
        self.line(x_start+60, y_base-20, x_start+85, y_base-20) # E3
        self.line(x_start+85, y_base-20, x_start+120, y_base) # E4
        
        self.set_font('Arial', '', 7)
        self.text(x_start+2, y_base+4, "E1: Suelo")
        self.text(x_start+30, y_base-12, "E2: Alcista")
        self.text(x_start+63, y_base-23, "E3: Techo")
        self.text(x_start+95, y_base-8, "E4: Bajista")
        self.ln(20)

def generar_pdf(ticker, temp, precio, sma, mf, rsi, señal, backtest, sma_periodo):
    pdf = InformeWeinstein()
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    
    # --- BLOQUE 1: RESUMEN DEL ACTIVO ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Analisis de Situacion: {ticker}", 0, 1)
    
    pdf.set_font('Arial', '', 10)
    # Tabla de datos basicos
    pdf.cell(47, 8, "Activo", 1); pdf.cell(47, 8, ticker, 1)
    pdf.cell(47, 8, "Precio Cierre", 1); pdf.cell(47, 8, f"{precio:.2f} $", 1, 1)
    pdf.cell(47, 8, "Temporalidad", 1); pdf.cell(47, 8, temp, 1)
    pdf.cell(47, 8, f"SMA {sma_periodo}", 1); pdf.cell(47, 8, f"{sma:.2f} $", 1, 1)
    pdf.ln(4)

    # --- BLOQUE 2: CONSEJO Y EXPLICACION (Lo que habias pedido) ---
    color_box = (210, 255, 210) if "COMPRA" in señal else (255, 210, 210) if "VENTA" in señal else (245, 245, 220)
    pdf.set_fill_color(*color_box)
    pdf.set_font('Arial', 'B', 13)
    pdf.cell(0, 12, f"DICTAMEN ALGORITMICO: {señal}", 1, 1, 'C', fill=True)
    pdf.ln(2)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 7, "Justificacion Tecnica Detallada:", 0, 1)
    pdf.set_font('Arial', '', 10)
    
    # El texto de explicacion que fusiona todos los indicadores
    texto_justificacion = (
        f"El sistema ha verificado que el precio de {ticker} cotiza actualmente {'por encima' if precio > sma else 'por debajo'} "
        f"de su media movil simple de {sma_periodo} periodos. La Fuerza Relativa de Mansfield registra un valor de {mf:.2f}, "
        f"lo que denota un momentum {'positivo' if mf > 0 else 'negativo'} respecto al indice S&P 500. "
        f"Con un RSI en {rsi:.2f}, la lectura sugiere una fase de "
        f"{'expansion fuerte' if 'COMPRA' in señal else 'capitulacion o debilidad' if 'VENTA' in señal else 'transicion lateral'}."
    )
    pdf.multi_cell(0, 6, texto_justificacion)
    
    # --- BLOQUE 3: INFOGRAFIA ---
    pdf.draw_stage_diagram()

    # --- BLOQUE 4: METRICAS DE BACKTESTING ---
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, "Validacion Cientifica (Resultados Historicos del Algoritmo):", 0, 1)
    
    pdf.set_font('Arial', '', 9)
    # Cuadro de resultados
    pdf.cell(45, 7, "Operaciones:", 1); pdf.cell(45, 7, f"{backtest['num_ops']}", 1)
    pdf.cell(45, 7, "Tasa de Acierto:", 1); pdf.cell(53, 7, f"{backtest['win_rate']:.1f}%", 1, 1)
    pdf.cell(45, 7, "Rentabilidad Sistema:", 1); pdf.cell(45, 7, f"{backtest['total_ret']:.1f}%", 1)
    pdf.cell(45, 7, "Max. Drawdown:", 1); pdf.cell(53, 7, f"{backtest['max_drawdown']:.1f}%", 1, 1)
    pdf.cell(45, 7, "Rentabilidad B&H:", 1); pdf.cell(45, 7, f"{backtest['bh_ret']:.1f}%", 1)
    pdf.cell(45, 7, "SMA de Analisis:", 1); pdf.cell(53, 7, f"{sma_periodo} sesiones", 1, 1)

    pdf.ln(10)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(150, 150, 150)
    pdf.multi_cell(0, 4, "Aviso: Este informe ha sido generado por un sistema experto cuantitativo. "
                         "Los resultados pasados no garantizan rentabilidades futuras. Analisis para uso academico (TFG).")

    return pdf.output(dest='S').encode('latin-1')
