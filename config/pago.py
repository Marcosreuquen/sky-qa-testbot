# ==========================================
# 4. DATOS DE PAGO POR HOME MARKET
# ==========================================

# Home market por defecto
HOME_MARKET = "PE"

# Ambiente por defecto y ambientes disponibles
AMBIENTE = "qa"
AMBIENTES_DISPONIBLES = {
    "qa": "initial-sale-qa",
    "tsts": "initial-sale-tsts",
    "stage": "initial-sale-stage",
}

# URLs base por market (template con placeholder {env})
_URLS_BASE = {
    "CL": "https://{env}.skyairline.com/es/chile",
    "PE": "https://{env}.skyairline.com/es/peru",
    "AR": "https://{env}.skyairline.com/es/argentina",
    "BR": "https://{env}.skyairline.com/pt/brasil",
}


def get_urls_por_market(ambiente="qa"):
    env = AMBIENTES_DISPONIBLES.get(ambiente, AMBIENTES_DISPONIBLES["qa"])
    return {market: url.format(env=env) for market, url in _URLS_BASE.items()}


# URLs por market (ambiente por defecto)
URLS_POR_MARKET = get_urls_por_market(AMBIENTE)

# Medio de pago asociado a cada market segun https://docs.google.com/document/d/1wIDHOWCInWtTeQo7H7l4cW3sp1MUXK5WQqeqBIh-p7Y/edit?tab=t.0
MEDIO_PAGO_POR_MARKET = {
    "CL": "Webpay",
    "PE": "Niubiz",
    "AR": "Mercado Pago",
    "BR": "Cielo",
}

# Datos de prueba de tarjeta/pago por market
TARJETA_POR_MARKET = {
    "CL": {
        "numero": "4051885600446623",
        "fecha": "12/30",       # cualquiera futura
        "cvv": "123",
        "tipo": "Crédito",
        "rut": "11.111.111-1",
        "clave": "123",
    },
    "PE": {
        "numero": "371204534881155",
        "fecha": "03/28",
        "cvv": "111",
        "email": "integraciones@niubiz.com.pe",
        "cuotas": "1",
    },
    "AR": {
        "numero": "4023653523914373",
        "fecha": "11/30",
        "cvv": "123",
        "titular": "APRO",
        "email": "user@gmail.com",
        "doc_tipo": "DNI",
        "doc_numero": "74415450",
    },
    "BR": {
        "numero": "4000000000001091",
        "fecha": "01/35",
        "cvv": "123",
        "tipo": "Débito",
        "codigo_auth": "1234",
    },
}
