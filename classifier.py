def clasificar_etapa(row):
    """
    Fase IV.a: Algoritmo de clasificación de etapas de Weinstein.
    Recibe una fila del DataFrame con los indicadores.
    """
    precio = row['Close']
    sma = row['SMA_30']
    mansfield = row['Mansfield']
    
    # Necesitamos comparar con la SMA de la semana anterior para saber la pendiente
    # (Este cálculo lo haremos fuera de la función, aquí solo definimos la lógica)
    
    # ETAPA 2: ALCISTA (Lo que buscamos)
    if precio > sma and mansfield > 0:
        return "Etapa 2: Alcista (Apta para compra)"
    
    # ETAPA 4: BAJISTA (Peligro)
    elif precio < sma and mansfield < 0:
        return "Etapa 4: Bajista (Evitar/Venta)"
    
    # ETAPA 1 O 3: TRANSICIÓN (Suelo o Techo)
    else:
        return "Etapa 1/3: Consolidación o Cambio de tendencia"

# Nota: En el siguiente paso haremos este análisis más complejo 
# mirando la pendiente de la media móvil.