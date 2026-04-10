from fpdf import FPDF
import datetime

class InformeWeinstein(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Informe de Análisis de Etapas (Weinstein)', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf(ticker, temporalidad, precio, sma, mansfield, rsi, señal):
    pdf = InformeWeinstein()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)

    # Datos Generales
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f"Resumen de Activo: {ticker}", 1, 1, 'L', fill=True)
    pdf.ln(5)

    col_width = 45
    pdf.cell(col_width, 10, f"Fecha: {datetime.date.today()}", 0, 0)
    pdf.cell(col_width, 10, f"Temporalidad: {temporalidad}", 0, 1)
    pdf.ln(5)

    # Métricas
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "Métricas Clave:", 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(col_width, 10, f"Precio: {precio:.2f} $", 1, 0)
    pdf.cell(col_width, 10, f"SMA 30: {sma:.2f} $", 1, 0)
    pdf.cell(col_width, 10, f"Mansfield: {mansfield:.2f}", 1, 0)
    pdf.cell(col_width, 10, f"RSI: {rsi:.2f}", 1, 1)
    pdf.ln(10)

    # Señal
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 15, f"ESTADO: {señal}", 1, 1, 'C')
    
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 10)
    pdf.multi_cell(0, 10, "Nota: Este informe ha sido generado automáticamente por la Terminal Weinstein Pro. Los datos se basan en el cierre de la última vela disponible.")

    return pdf.output(dest='S').encode('latin-1')