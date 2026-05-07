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
