def clasificar_etapa(row):
    """
    Fase IV.a: Algoritmo de clasificación de etapas de Weinstein.
    Recibe una fila del DataFrame con los indicadores.
    """
    precio = row['Close']
    sma = row['SMA_30']
    mansfield = row['Mansfield']
    
    
    # ETAPA 2: ALCISTA (Lo que buscamos)
    if precio > sma and mansfield > 0:
        return "Etapa 2: Alcista (Apta para compra)"
    
    # ETAPA 4: BAJISTA (Peligro)
    elif precio < sma and mansfield < 0:
        return "Etapa 4: Bajista (Evitar/Venta)"
    
    # ETAPA 1 O 3: TRANSICIÓN (Suelo o Techo)
    else:
        return "Etapa 1/3: Consolidación o Cambio de tendencia"
