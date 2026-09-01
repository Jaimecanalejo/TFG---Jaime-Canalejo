"""Métricas e interpretación de cruces del RSI."""

import pandas as pd


def analizar_cruces_rsi(df, umbral_compra=30.0, umbral_venta=70.0):
    """Cuenta entradas del RSI en sobreventa y sobrecompra.

    Un cruce de compra se registra cuando el RSI pasa desde un valor igual o
    superior a 30 a otro inferior a 30. El cruce de venta es el movimiento
    equivalente desde 70 o menos hacia un valor superior a 70.
    """
    if "RSI" not in df.columns:
        raise ValueError("El DataFrame no contiene la columna RSI.")

    rsi = pd.to_numeric(df["RSI"], errors="coerce").dropna()
    if rsi.empty:
        return {
            "cruces_compra": 0,
            "cruces_venta": 0,
            "fechas_compra": [],
            "fechas_venta": [],
            "rsi_actual": None,
            "zona_actual": "sin datos",
            "periodo_inicio": None,
            "periodo_fin": None,
        }

    anterior = rsi.shift(1)
    mascara_compra = (rsi < umbral_compra) & (anterior >= umbral_compra)
    mascara_venta = (rsi > umbral_venta) & (anterior <= umbral_venta)
    fechas_compra = rsi.index[mascara_compra].tolist()
    fechas_venta = rsi.index[mascara_venta].tolist()
    rsi_actual = float(rsi.iloc[-1])

    if rsi_actual < umbral_compra:
        zona_actual = "sobreventa"
    elif rsi_actual > umbral_venta:
        zona_actual = "sobrecompra"
    else:
        zona_actual = "neutral"

    return {
        "cruces_compra": len(fechas_compra),
        "cruces_venta": len(fechas_venta),
        "fechas_compra": fechas_compra,
        "fechas_venta": fechas_venta,
        "rsi_actual": rsi_actual,
        "zona_actual": zona_actual,
        "periodo_inicio": rsi.index[0],
        "periodo_fin": rsi.index[-1],
    }


def generar_comentario_local(ticker, analisis):
    """Genera una lectura explicativa disponible incluso sin API de IA."""
    compras = analisis["cruces_compra"]
    ventas = analisis["cruces_venta"]
    actual = analisis["rsi_actual"]
    zona = analisis["zona_actual"]
    total = compras + ventas

    if total == 0:
        frecuencia = "no entró en ninguna de las dos zonas extremas"
    elif total <= 3:
        frecuencia = "mostró pocos episodios extremos"
    else:
        frecuencia = "mostró episodios extremos con cierta frecuencia"

    actual_texto = "sin un valor RSI actual disponible" if actual is None else f"con un RSI actual de {actual:.2f}, en zona {zona}"
    return (
        f"{ticker} {frecuencia}: atravesó {compras} veces el umbral de 30 hacia la zona "
        f"potencial de compra y {ventas} veces el umbral de 70 hacia la zona potencial "
        f"de venta. Actualmente se encuentra {actual_texto}. Estos cruces describen "
        "momentum y posibles excesos; no constituyen por sí solos una orden de inversión."
    )


def generar_comentario_ia(ticker, analisis, api_key, model="gpt-5-mini"):
    """Solicita a OpenAI una interpretación breve de las métricas RSI calculadas."""
    from openai import OpenAI

    inicio = _formatear_fecha(analisis["periodo_inicio"])
    fin = _formatear_fecha(analisis["periodo_fin"])
    entrada = (
        f"Activo: {ticker}\nPeriodo: {inicio} a {fin}\n"
        f"Entradas en sobreventa (cruce descendente de 30): {analisis['cruces_compra']}\n"
        f"Entradas en sobrecompra (cruce ascendente de 70): {analisis['cruces_venta']}\n"
        f"RSI actual: {analisis['rsi_actual']}\nZona actual: {analisis['zona_actual']}"
    )
    cliente = OpenAI(api_key=api_key)
    respuesta = cliente.responses.create(
        model=model,
        instructions=(
            "Eres un analista técnico prudente. Explica en español y en un único párrafo "
            "de 80 a 130 palabras qué revelan los cruces RSI proporcionados. Compara la "
            "frecuencia de sobreventa y sobrecompra, interpreta el estado actual y aclara "
            "que el RSI debe confirmarse con tendencia, precio y volumen. No inventes datos "
            "ni presentes el comentario como asesoramiento financiero."
        ),
        input=entrada,
        max_output_tokens=250,
        store=False,
    )
    return respuesta.output_text.strip()


def firma_analisis_rsi(ticker, analisis):
    """Firma estable para separar y renovar comentarios por activo y periodo."""
    return "|".join([
        str(ticker),
        _formatear_fecha(analisis["periodo_inicio"]),
        _formatear_fecha(analisis["periodo_fin"]),
        str(analisis["cruces_compra"]),
        str(analisis["cruces_venta"]),
        str(analisis["rsi_actual"]),
    ])


def _formatear_fecha(valor):
    if valor is None:
        return "sin datos"
    try:
        return pd.Timestamp(valor).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(valor)
