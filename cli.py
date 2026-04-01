import argparse
from datetime import date

from config.pago import AMBIENTES_DISPONIBLES, MEDIO_PAGO_POR_MARKET as _MEDIO_PAGO

CDP_URL_DEFAULT = "http://127.0.0.1:9222"
CHECKPOINTS_VALIDOS = [
    "BUSQUEDA",
    "SELECCION_TARIFA",
    "ANCILLARIES",
    "LLEGADA_DATOS_PASAJERO",
    "DATOS_PASAJERO",
    "CHECKOUT",
    "PAGO",
]
MARKETS_VALIDOS = list(_MEDIO_PAGO.keys())
TIPOS_VIAJE_VALIDOS = ["ONE_WAY", "ROUND_TRIP"]
AMBIENTES_VALIDOS = list(AMBIENTES_DISPONIBLES.keys())
SELECCION_ASIENTO_VALIDA = ["SKIP", "AUTO"]


def _int_positivo(value):
    entero = int(value)
    if entero <= 0:
        raise argparse.ArgumentTypeError("Debe ser mayor a 0")
    return entero


def _int_no_negativo(value):
    entero = int(value)
    if entero < 0:
        raise argparse.ArgumentTypeError("No puede ser negativo")
    return entero


def _fecha_hace_anios(anios):
    hoy = date.today()
    try:
        fecha = hoy.replace(year=hoy.year - anios)
    except ValueError:
        # Corrige 29/02 en años no bisiestos
        fecha = hoy.replace(month=2, day=28, year=hoy.year - anios)
    return fecha.strftime("%d/%m/%Y")


def _email_con_sufijo(email_base, indice):
    if "@" not in email_base:
        return f"{email_base}{indice}"
    usuario, dominio = email_base.split("@", 1)
    return f"{usuario}{indice}@{dominio}"


def _doc_con_sufijo(doc_base, indice):
    return f"{doc_base}{indice}"


def _sufijo_alfabetico(indice):
    # 1 -> A, 2 -> B, ..., 26 -> Z, 27 -> AA
    valor = max(1, indice)
    partes = []
    while valor > 0:
        valor, resto = divmod(valor - 1, 26)
        partes.append(chr(65 + resto))
    return "".join(reversed(partes))


def _normalizar_tipo_viaje(tipo_viaje):
    valor = (tipo_viaje or "").strip().upper()
    if valor in {"OW", "ONEWAY", "ONE_WAY", "SOLO_IDA"}:
        return "ONE_WAY"
    if valor in {"RT", "ROUNDTRIP", "ROUND_TRIP", "IDA_Y_VUELTA"}:
        return "ROUND_TRIP"
    return valor


def _normalizar_seleccion_asiento(valor):
    normalizado = (valor or "").strip().upper()
    if normalizado in {"SKIP", "OMITIR", "NONE", "SIN_ASIENTO"}:
        return "SKIP"
    if normalizado in {"AUTO", "AUTOMATICO", "AUTOMÁTICO", "FIRST", "PRIMERO"}:
        return "AUTO"
    return normalizado


def _generar_pasajeros(base, adultos, ninos, infantes):
    pasajeros = []

    def _clonar(tipo_pasajero, indice_tipo):
        indice_global = len(pasajeros) + 1
        pasajero = {**base, "tipo_pasajero": tipo_pasajero}

        if indice_global > 1:
            sufijo = _sufijo_alfabetico(indice_global)
            pasajero["nombre"] = f"{base['nombre']} {sufijo}"
            pasajero["apellido"] = f"{base['apellido']} {sufijo}"
            pasajero["email"] = _email_con_sufijo(base["email"], indice_global)
            pasajero["doc_numero"] = _doc_con_sufijo(base["doc_numero"], indice_global)

        if tipo_pasajero == "CHD":
            pasajero["nombre"] = f"Nino {_sufijo_alfabetico(indice_tipo)}"
            pasajero["fecha_nac"] = _fecha_hace_anios(10)
        elif tipo_pasajero == "INF":
            pasajero["nombre"] = f"Infante {_sufijo_alfabetico(indice_tipo)}"
            pasajero["fecha_nac"] = _fecha_hace_anios(1)

        return pasajero

    for indice in range(1, adultos + 1):
        pasajeros.append(_clonar("ADT", indice))

    for indice in range(1, ninos + 1):
        pasajeros.append(_clonar("CHD", indice))

    for indice in range(1, infantes + 1):
        pasajeros.append(_clonar("INF", indice))

    return pasajeros


def parse_args():
    """Parsea argumentos de línea de comandos para sobreescribir la configuración."""
    parser = argparse.ArgumentParser(
        description="🤖 Sky TestBot — Automatización de compra de vuelos Sky Airline (QA/TSTS/Stage)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Home Markets disponibles:
  CL  Chile     → Webpay
  PE  Perú      → Niubiz
  AR  Argentina → Mercado Pago
  BR  Brasil    → Cielo

Ejemplos:
  python test_sky.py --market PE
  python test_sky.py --market CL --origen Santiago --destino "La Serena"
  python test_sky.py --market AR --checkpoint BUSQUEDA
  python test_sky.py --market BR --headless --slow-mo 0
  python test_sky.py --tipo-viaje ROUND_TRIP --dias 16 --dias-retorno 5
  python test_sky.py --adultos 3 --ninos 1 --market PE
  python test_sky.py --market PE --modo-exploracion --solo-exploracion
  python test_sky.py --retencion-evidencias-semanas 3
  python test_sky.py --usar-chrome-existente --cdp-url http://127.0.0.1:9222
        """,
    )

    # --- Home Market ---
    grupo_market = parser.add_argument_group("Home Market")
    grupo_market.add_argument(
        "--market",
        type=str,
        choices=MARKETS_VALIDOS,
        default=None,
        help="Home market (CL/PE/AR/BR). Define URL, medio de pago y datos de tarjeta automáticamente",
    )
    grupo_market.add_argument(
        "--ambiente",
        type=str,
        choices=AMBIENTES_VALIDOS,
        default=None,
        help="Ambiente a usar: qa (por defecto), tsts o stage",
    )

    # --- 1. Ruta y Tiempos ---
    grupo_rutas = parser.add_argument_group("Ruta y Tiempos")
    grupo_rutas.add_argument("--url", type=str, help="URL inicial (override, normalmente se deduce del market)")
    grupo_rutas.add_argument("--pausa", type=int, metavar="MS", help="Tiempo de pausa de seguridad (ms)")
    grupo_rutas.add_argument("--slow-mo", type=int, metavar="MS", help="Velocidad visual slow_mo (ms)")
    grupo_rutas.add_argument(
        "--espera-final-segundos",
        type=_int_no_negativo,
        metavar="N",
        help="Espera final antes del screenshot/cierre (segundos)",
    )
    grupo_rutas.add_argument(
        "--usar-chrome-existente",
        action="store_true",
        help="Conectar al Chrome ya abierto mediante CDP (requiere --remote-debugging-port)",
    )
    grupo_rutas.add_argument(
        "--cdp-url",
        type=str,
        help="URL CDP de Chrome (ej: http://127.0.0.1:9222)",
    )
    grupo_rutas.add_argument(
        "--cdp-reutilizar-primera-pestana",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    grupo_rutas.add_argument("--headless", action="store_true", help="Ejecutar en modo headless (sin ventana)")
    grupo_rutas.add_argument(
        "--modo-exploracion",
        action="store_true",
        help="Registra controles visibles y screenshots por etapa para mapear variantes de UI",
    )
    grupo_rutas.add_argument(
        "--solo-exploracion",
        action="store_true",
        help="Termina después de la búsqueda (sin selección de tarifa ni pago). Implica modo exploración",
    )
    grupo_rutas.add_argument(
        "--control-dir",
        type=str,
        help="Directorio temporal de control para pausa/reanudación desde la GUI",
    )
    grupo_limpieza = grupo_rutas.add_mutually_exclusive_group()
    grupo_limpieza.add_argument(
        "--limpiar-evidencias-antiguas",
        dest="limpiar_evidencias_antiguas",
        action="store_true",
        default=None,
        help="Elimina entradas viejas de screenshots_pruebas antes de arrancar",
    )
    grupo_limpieza.add_argument(
        "--no-limpiar-evidencias-antiguas",
        dest="limpiar_evidencias_antiguas",
        action="store_false",
        help="No elimina evidencias viejas al iniciar la ejecución",
    )
    grupo_rutas.add_argument(
        "--retencion-evidencias-semanas",
        type=_int_positivo,
        metavar="N",
        help="Cantidad de semanas a conservar en screenshots_pruebas",
    )

    # --- 2. Datos del Vuelo ---
    grupo_vuelo = parser.add_argument_group("Datos del Vuelo")
    grupo_vuelo.add_argument("--origen", type=str, help="Ciudad de origen")
    grupo_vuelo.add_argument("--destino", type=str, help="Ciudad de destino")
    grupo_vuelo.add_argument("--dias", type=int, metavar="N", help="Días a futuro para seleccionar fecha")
    grupo_vuelo.add_argument(
        "--tipo-viaje",
        type=_normalizar_tipo_viaje,
        choices=TIPOS_VIAJE_VALIDOS,
        help="Tipo de viaje: ONE_WAY (solo ida) o ROUND_TRIP (ida y vuelta)",
    )
    grupo_vuelo.add_argument(
        "--dias-retorno",
        type=_int_positivo,
        metavar="N",
        help="Días de diferencia entre ida y vuelta (solo ROUND_TRIP)",
    )
    grupo_vuelo.add_argument(
        "--adultos",
        type=_int_positivo,
        metavar="N",
        help="Cantidad de pasajeros adultos",
    )
    grupo_vuelo.add_argument(
        "--ninos",
        type=_int_no_negativo,
        metavar="N",
        help="Cantidad de pasajeros niños",
    )
    grupo_vuelo.add_argument(
        "--infantes",
        type=_int_no_negativo,
        metavar="N",
        help="Cantidad de pasajeros infantes",
    )
    grupo_vuelo.add_argument(
        "--seleccion-asiento",
        type=_normalizar_seleccion_asiento,
        choices=SELECCION_ASIENTO_VALIDA,
        help="Estrategia para asientos: SKIP o AUTO",
    )
    grupo_vuelo.add_argument(
        "--maletas-cabina",
        type=_int_no_negativo,
        metavar="N",
        help="Cantidad total de maletas/equipaje de cabina adicional a intentar agregar",
    )
    grupo_vuelo.add_argument(
        "--maletas-bodega",
        type=_int_no_negativo,
        metavar="N",
        help="Cantidad total de maletas/equipaje en bodega a intentar agregar",
    )

    # --- 3. Datos del Pasajero ---
    grupo_pax = parser.add_argument_group("Datos del Pasajero")
    grupo_pax.add_argument("--nombre", type=str, help="Nombre del pasajero")
    grupo_pax.add_argument("--apellido", type=str, help="Apellido del pasajero")
    grupo_pax.add_argument("--email", type=str, help="Email del pasajero")
    grupo_pax.add_argument("--doc-tipo", type=str, help="Tipo de documento (ej: DNI, Pasaporte)")
    grupo_pax.add_argument("--doc-numero", type=str, help="Número de documento")
    grupo_pax.add_argument("--telefono", type=str, help="Teléfono del pasajero")
    grupo_pax.add_argument("--prefijo-pais", type=str, help="Prefijo telefónico del país")
    grupo_pax.add_argument("--genero", type=str, choices=["Masculino", "Femenino"], help="Género")
    grupo_pax.add_argument("--pais-emision", type=str, help="País de emisión del documento")
    grupo_pax.add_argument("--fecha-nac", type=str, metavar="DD/MM/AAAA", help="Fecha de nacimiento")

    # --- 4. Datos de Pago (overrides manuales) ---
    grupo_pago = parser.add_argument_group("Datos de Pago (override manual)")
    grupo_pago.add_argument("--tarjeta-numero", type=str, help="Número de tarjeta (override)")
    grupo_pago.add_argument("--tarjeta-fecha", type=str, metavar="MM/YY", help="Fecha de expiración (override)")
    grupo_pago.add_argument("--tarjeta-cvv", type=str, help="CVV de la tarjeta (override)")

    # --- 5. Checkpoint ---
    grupo_ck = parser.add_argument_group("Checkpoint")
    grupo_ck.add_argument(
        "--checkpoint",
        type=str,
        choices=CHECKPOINTS_VALIDOS,
        default=None,
        help="Punto de pausa para inspección manual",
    )

    return parser.parse_args()


def aplicar_args(args):
    """
    Aplica los argumentos CLI sobre los valores por defecto de config.
    El --market define automáticamente: URL, medio de pago y datos de tarjeta.
    El --ambiente define el subdominio de la URL (qa/tsts/stage).
    Retorna CFG: diccionario con toda la configuración resuelta.

    Schema de CFG (keys disponibles en test_sky.py):
        market          str   "PE"|"CL"|"AR"|"BR"
        ambiente        str   "qa"|"tsts"|"stage"
        medio_pago      str   "Niubiz"|"Webpay"|"Mercado Pago"|"Cielo"
        url             str   URL base del home market + ambiente
        pausa           int   ms de pausa de seguridad entre pasos
        slow_mo         int   ms de slow_mo de Playwright
        espera_final_segundos int
        limpiar_evidencias_antiguas bool
        retencion_evidencias_semanas int
        usar_chrome_existente bool
        cdp_url         str
        cdp_reutilizar_primera_pestana bool
        headless        bool
        modo_exploracion bool
        solo_exploracion bool
        origen          str
        destino         str
        dias            int
        tipo_viaje      str   "ONE_WAY"|"ROUND_TRIP"
        dias_retorno    int
        pasajeros       dict  {adultos, ninos, infantes}
        pasajeros_lista list[dict]  lista completa de pasajeros
        extras          dict  {seleccion_asiento, maletas_cabina, maletas_bodega}
        checkpoint      str|None
        pasajero        dict  primer pasajero (alias de pasajeros_lista[0])
        tarjeta         dict  {numero, fecha, cvv, ...campos extra por market}
    """
    from config import (
        TIEMPO_PAUSA_SEGURIDAD,
        VELOCIDAD_VISUAL,
        ESPERA_FINAL_SEGUNDOS,
        LIMPIAR_EVIDENCIAS_ANTIGUAS,
        SEMANAS_RETENCION_EVIDENCIAS,
        VUELO_ORIGEN,
        VUELO_DESTINO,
        MIN_DIAS_A_FUTURO,
        DIAS_A_FUTURO,
        TIPO_VIAJE,
        DIAS_RETORNO_DESDE_IDA,
        CANTIDAD_ADULTOS,
        CANTIDAD_NINOS,
        CANTIDAD_INFANTES,
        SELECCION_ASIENTO,
        MALETAS_CABINA,
        MALETAS_BODEGA,
        PASAJERO,
        HOME_MARKET,
        AMBIENTE,
        MEDIO_PAGO_POR_MARKET,
        TARJETA_POR_MARKET,
        CHECKPOINT,
        get_urls_por_market,
    )

    # Resolver market y ambiente
    market = args.market or HOME_MARKET
    ambiente = args.ambiente or AMBIENTE
    urls_por_market = get_urls_por_market(ambiente)
    tarjeta_market = TARJETA_POR_MARKET[market]
    tipo_viaje = _normalizar_tipo_viaje(args.tipo_viaje or TIPO_VIAJE)

    dias = args.dias if args.dias is not None else DIAS_A_FUTURO
    if dias < MIN_DIAS_A_FUTURO:
        print(
            f"⚠️  '--dias {dias}' es menor al umbral antifraude sugerido ({MIN_DIAS_A_FUTURO}). "
            "Se mantiene el valor elegido, pero podría haber mayor riesgo de rechazo en pago.",
        )

    adultos = args.adultos if args.adultos is not None else CANTIDAD_ADULTOS
    ninos = args.ninos if args.ninos is not None else CANTIDAD_NINOS
    infantes = args.infantes if args.infantes is not None else CANTIDAD_INFANTES

    if infantes > adultos:
        raise ValueError("La cantidad de infantes no puede ser mayor a la cantidad de adultos.")

    dias_retorno = args.dias_retorno if args.dias_retorno is not None else DIAS_RETORNO_DESDE_IDA
    seleccion_asiento = _normalizar_seleccion_asiento(args.seleccion_asiento or SELECCION_ASIENTO)
    maletas_cabina = args.maletas_cabina if args.maletas_cabina is not None else MALETAS_CABINA
    maletas_bodega = args.maletas_bodega if args.maletas_bodega is not None else MALETAS_BODEGA
    pasajero_base = {
        "nombre": args.nombre or PASAJERO["nombre"],
        "apellido": args.apellido or PASAJERO["apellido"],
        "email": args.email or PASAJERO["email"],
        "doc_tipo": args.doc_tipo or PASAJERO["doc_tipo"],
        "doc_numero": args.doc_numero or PASAJERO["doc_numero"],
        "telefono": args.telefono or PASAJERO["telefono"],
        "prefijo_pais": args.prefijo_pais or PASAJERO["prefijo_pais"],
        "genero": args.genero or PASAJERO["genero"],
        "pais_emision": args.pais_emision or PASAJERO["pais_emision"],
        "fecha_nac": args.fecha_nac or PASAJERO["fecha_nac"],
    }
    pasajeros_lista = _generar_pasajeros(pasajero_base, adultos, ninos, infantes)

    cfg = {
        "market": market,
        "ambiente": ambiente,
        "medio_pago": MEDIO_PAGO_POR_MARKET[market],
        "url": args.url or urls_por_market[market],
        "pausa": args.pausa if args.pausa is not None else TIEMPO_PAUSA_SEGURIDAD,
        "slow_mo": args.slow_mo if args.slow_mo is not None else VELOCIDAD_VISUAL,
        "espera_final_segundos": (
            args.espera_final_segundos if args.espera_final_segundos is not None else ESPERA_FINAL_SEGUNDOS
        ),
        "limpiar_evidencias_antiguas": (
            args.limpiar_evidencias_antiguas
            if args.limpiar_evidencias_antiguas is not None
            else LIMPIAR_EVIDENCIAS_ANTIGUAS
        ),
        "retencion_evidencias_semanas": (
            args.retencion_evidencias_semanas
            if args.retencion_evidencias_semanas is not None
            else SEMANAS_RETENCION_EVIDENCIAS
        ),
        "usar_chrome_existente": args.usar_chrome_existente,
        "cdp_url": args.cdp_url or CDP_URL_DEFAULT,
        "cdp_reutilizar_primera_pestana": args.cdp_reutilizar_primera_pestana,
        "control_dir": args.control_dir,
        "headless": args.headless,
        "modo_exploracion": args.modo_exploracion or args.solo_exploracion,
        "solo_exploracion": args.solo_exploracion,
        "origen": args.origen or VUELO_ORIGEN,
        "destino": args.destino or VUELO_DESTINO,
        "dias": dias,
        "tipo_viaje": tipo_viaje,
        "dias_retorno": dias_retorno,
        "pasajeros": {
            "adultos": adultos,
            "ninos": ninos,
            "infantes": infantes,
        },
        "pasajeros_lista": pasajeros_lista,
        "extras": {
            "seleccion_asiento": seleccion_asiento,
            "maletas_cabina": maletas_cabina,
            "maletas_bodega": maletas_bodega,
        },
        "checkpoint": args.checkpoint or CHECKPOINT,
        "pasajero": pasajeros_lista[0],
        "tarjeta": {
            "numero": args.tarjeta_numero or tarjeta_market["numero"],
            "fecha": args.tarjeta_fecha or tarjeta_market["fecha"],
            "cvv": args.tarjeta_cvv or tarjeta_market["cvv"],
            **{k: v for k, v in tarjeta_market.items() if k not in ("numero", "fecha", "cvv")},
        },
    }

    return cfg
