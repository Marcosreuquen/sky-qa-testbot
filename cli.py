import argparse

CHECKPOINTS_VALIDOS = ["BUSQUEDA", "SELECCION_TARIFA", "DATOS_PASAJERO", "CHECKOUT", "PAGO"]
MARKETS_VALIDOS = ["CL", "PE", "AR", "BR"]


def parse_args():
    """Parsea argumentos de línea de comandos para sobreescribir la configuración."""
    parser = argparse.ArgumentParser(
        description="🤖 Sky QA TestBot — Automatización de compra de vuelos Sky Airline",
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

    # --- 1. Ruta y Tiempos ---
    grupo_rutas = parser.add_argument_group("Ruta y Tiempos")
    grupo_rutas.add_argument("--url", type=str, help="URL inicial (override, normalmente se deduce del market)")
    grupo_rutas.add_argument("--pausa", type=int, metavar="MS", help="Tiempo de pausa de seguridad (ms)")
    grupo_rutas.add_argument("--slow-mo", type=int, metavar="MS", help="Velocidad visual slow_mo (ms)")
    grupo_rutas.add_argument("--headless", action="store_true", help="Ejecutar en modo headless (sin ventana)")

    # --- 2. Datos del Vuelo ---
    grupo_vuelo = parser.add_argument_group("Datos del Vuelo")
    grupo_vuelo.add_argument("--origen", type=str, help="Ciudad de origen")
    grupo_vuelo.add_argument("--destino", type=str, help="Ciudad de destino")
    grupo_vuelo.add_argument("--dias", type=int, metavar="N", help="Días a futuro para seleccionar fecha")

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
    Retorna un diccionario con toda la configuración resuelta.
    """
    from config import (
        TIEMPO_PAUSA_SEGURIDAD,
        VELOCIDAD_VISUAL,
        VUELO_ORIGEN,
        VUELO_DESTINO,
        DIAS_A_FUTURO,
        PASAJERO,
        HOME_MARKET,
        URLS_POR_MARKET,
        MEDIO_PAGO_POR_MARKET,
        TARJETA_POR_MARKET,
        CHECKPOINT,
    )

    # Resolver market
    market = args.market or HOME_MARKET
    tarjeta_market = TARJETA_POR_MARKET[market]

    cfg = {
        "market": market,
        "medio_pago": MEDIO_PAGO_POR_MARKET[market],
        "url": args.url or URLS_POR_MARKET[market],
        "pausa": args.pausa if args.pausa is not None else TIEMPO_PAUSA_SEGURIDAD,
        "slow_mo": args.slow_mo if args.slow_mo is not None else VELOCIDAD_VISUAL,
        "headless": args.headless,
        "origen": args.origen or VUELO_ORIGEN,
        "destino": args.destino or VUELO_DESTINO,
        "dias": args.dias if args.dias is not None else DIAS_A_FUTURO,
        "checkpoint": args.checkpoint or CHECKPOINT,
        "pasajero": {
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
        },
        "tarjeta": {
            "numero": args.tarjeta_numero or tarjeta_market["numero"],
            "fecha": args.tarjeta_fecha or tarjeta_market["fecha"],
            "cvv": args.tarjeta_cvv or tarjeta_market["cvv"],
            **{k: v for k, v in tarjeta_market.items() if k not in ("numero", "fecha", "cvv")},
        },
    }

    return cfg
