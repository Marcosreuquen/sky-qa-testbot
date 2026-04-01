"""
Flujo de búsqueda de vuelo:
  - login panel, home lista
  - tipo de viaje, origen, destino
  - fechas (calendario)
  - configuración de pasajeros en búsqueda
  - selección de vuelo y tarifa
  - saltar extras
"""

import re
import time
from datetime import datetime, timedelta

import core.state as state
from core.helpers import (
    _normalizar_texto,
    _buscar_visible,
    _buscar_selector_visible,
    _click_selector_visible,
    _click_todos_selectores_visibles,
    _click_texto_visible,
    _input_editable,
    _capturar_estado_ui,
    detectar_etapa_actual,
    gestionar_pausa_edicion,
)


# ==========================================
# HOME Y LOGIN
# ==========================================

def _esperar_home_lista(page, timeout_ms=45000):
    """Espera a que el flight-box esté listo para interacción."""
    deadline = time.monotonic() + timeout_ms / 1000
    ultimo_error = None
    while time.monotonic() < deadline:
        gestionar_pausa_edicion(page, "esperando_home")
        try:
            origen = _buscar_selector_visible(
                page,
                [
                    "#origin-id",
                    "#origin-id input",
                    '[data-test*="origin"]',
                    'input[placeholder*="Desde" i]',
                    'input[placeholder*="Origen" i]',
                    'input[aria-label*="Desde" i]',
                    'input[aria-label*="Origen" i]',
                ],
            )
            destino = _buscar_selector_visible(
                page,
                [
                    "#destination-id",
                    "#destination-id input",
                    '[data-test*="destination"]',
                    'input[placeholder*="Hacia" i]',
                    'input[placeholder*="Destino" i]',
                    'input[aria-label*="Hacia" i]',
                    'input[aria-label*="Destino" i]',
                ],
            )
            boton_buscar = _buscar_selector_visible(
                page,
                [
                    'button:has-text("Buscar vuelo")',
                    'button:has-text("Buscar vuelos")',
                    'button:has-text("Buscar")',
                    'button:has-text("Buscar voo")',
                    'button:has-text("Search")',
                    'button[type="submit"]',
                    '[data-test*="search"]',
                ],
            )
            if origen and destino and boton_buscar:
                return
        except Exception as error:
            ultimo_error = error
        page.wait_for_timeout(1000)

    raise RuntimeError(f"No se pudo detectar el formulario de búsqueda listo en {timeout_ms}ms: {ultimo_error}")


def _panel_login_abierto(page):
    return bool(
        _buscar_selector_visible(
            page,
            [
                ':text("Inicia sesión")',
                'input[placeholder*="Correo electrónico" i]',
                'input[placeholder*="Contraseña" i]',
            ],
        )
    )


def _cerrar_panel_login_si_abierto(page):
    for _ in range(4):
        if not _panel_login_abierto(page):
            return True
        page.keyboard.press("Escape")
        page.wait_for_timeout(140)
        if not _panel_login_abierto(page):
            return True

        _click_selector_visible(
            page,
            [
                'button:has-text("Cerrar")',
                'button[aria-label*="cerrar" i]',
                'aside button[aria-label*="close" i]',
            ],
            force=True,
            requerido=False,
        )
        page.wait_for_timeout(140)
    return not _panel_login_abierto(page)


# ==========================================
# TIPO DE VIAJE Y CIUDAD
# ==========================================

def _seleccionar_tipo_viaje(page):
    tipo_viaje = state.CFG["tipo_viaje"]
    if tipo_viaje == "ROUND_TRIP":
        etiquetas = ["Ida-Vuelta", "Ida y vuelta", "Round trip", "Ida e volta"]
    else:
        etiquetas = ["Solo ida", "One way", "Somente ida"]

    patron = re.compile("|".join(re.escape(etiqueta) for etiqueta in etiquetas), re.IGNORECASE)
    item = _buscar_visible(page.locator("label.sky-radiobutton.radio-flight-type").filter(has_text=patron))
    if not item:
        item = _buscar_visible(page.locator("label.sky-radiobutton").filter(has_text=patron))
    if item:
        item.click(force=True)
        return

    candidatos = []
    for etiqueta in etiquetas:
        candidatos.extend(
            [
                f'button:has-text("{etiqueta}")',
                f'span:has-text("{etiqueta}")',
                f'div:has-text("{etiqueta}")',
            ]
        )

    if _click_selector_visible(page, candidatos, force=True):
        return

    if tipo_viaje == "ONE_WAY":
        print("⚠️ No se encontró control explícito de 'Solo ida'. Se asume valor por defecto.")
        return

    raise RuntimeError(f"No se pudo seleccionar tipo de viaje '{tipo_viaje}'.")


def _seleccionar_ciudad(page, contenedor_selector, ciudad):
    _cerrar_panel_login_si_abierto(page)
    if not _click_selector_visible(page, [contenedor_selector], force=True, requerido=True):
        raise RuntimeError(f"No se pudo abrir selector de ciudad para '{ciudad}'.")

    input_ciudad = None
    for intento in range(20):
        gestionar_pausa_edicion(page, f"seleccion_ciudad_{ciudad}")
        page.wait_for_timeout(200)
        input_ciudad = _input_editable(page.locator(":focus"))
        if not input_ciudad:
            input_ciudad = _input_editable(page.locator(f"{contenedor_selector} input:not([readonly])"))
        if not input_ciudad:
            input_ciudad = _input_editable(page.locator(f"{contenedor_selector} input"))
        if not input_ciudad:
            input_ciudad = _input_editable(
                page.locator(
                    'input[placeholder*="Desde" i]:not([readonly]), '
                    'input[placeholder*="Hacia" i]:not([readonly]), '
                    'input[placeholder*="Origen" i]:not([readonly]), '
                    'input[placeholder*="Destino" i]:not([readonly]), '
                    'input[aria-label*="Desde" i]:not([readonly]), '
                    'input[aria-label*="Hacia" i]:not([readonly]), '
                    'input[aria-label*="Origen" i]:not([readonly]), '
                    'input[aria-label*="Destino" i]:not([readonly]), '
                    '.ant-select-dropdown input:not([readonly]), '
                    'input[role="combobox"]:not([readonly])',
                )
            )
        if input_ciudad:
            break
        if intento in {5, 10, 15}:
            _click_selector_visible(page, [contenedor_selector], force=True, requerido=False)

    if not input_ciudad:
        raise RuntimeError(f"No se encontró input editable para ciudad '{ciudad}'.")

    input_ciudad.click(force=True)
    input_ciudad.fill(ciudad)
    page.wait_for_timeout(700)

    if _click_texto_visible(page, ciudad, exacto=True):
        return

    opcion = _buscar_visible(page.get_by_text(re.compile(re.escape(ciudad), re.IGNORECASE)))
    if opcion:
        opcion.click()
        return

    opcion_dropdown = _buscar_selector_visible(
        page,
        [
            'div[role="option"]',
            '.ant-select-item-option',
            '.ant-select-item-option-content',
            'li[role="option"]',
        ],
    )
    if opcion_dropdown:
        opcion_dropdown.click()
        return

    page.keyboard.press("Enter")
    page.wait_for_timeout(300)
    texto_contenedor = ""
    try:
        texto_contenedor = _normalizar_texto(page.locator(contenedor_selector).first.inner_text())
    except Exception:
        pass
    if ciudad.lower() in texto_contenedor.lower():
        return

    raise RuntimeError(f"No se encontró opción de autocompletado para ciudad '{ciudad}'.")


def _ciudad_aplicada_en_contenedor(page, contenedor_selector, ciudad):
    contenedor = page.locator(contenedor_selector).first
    try:
        if not contenedor.is_visible():
            return False
    except Exception:
        return False

    valores = []
    try:
        texto = _normalizar_texto(contenedor.inner_text())
        if texto:
            valores.append(texto)
    except Exception:
        pass

    inputs = contenedor.locator("input")
    for indice in range(inputs.count()):
        campo = inputs.nth(indice)
        try:
            valor = _normalizar_texto(campo.input_value())
            if valor:
                valores.append(valor)
        except Exception:
            continue

    ciudad_normalizada = ciudad.lower()
    return any(ciudad_normalizada in valor.lower() for valor in valores)


def _seleccionar_opcion_dropdown(page, texto_opcion):
    if _click_texto_visible(page, texto_opcion, exacto=True):
        return True

    patron = re.compile(f"^{re.escape(texto_opcion)}$", re.IGNORECASE)
    item = _buscar_visible(page.get_by_text(patron))
    if item:
        item.click()
        return True
    return False


# ==========================================
# PASAJEROS EN BÚSQUEDA
# ==========================================

def _cerrar_calendario_si_abierto(page):
    dias_calendario = page.locator('div.vc-day-content, [role="button"].vc-day-content, button.vc-title')
    for _ in range(4):
        if not _buscar_visible(dias_calendario):
            return
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)


def _modal_pasajeros_abierto(page):
    return bool(
        _buscar_selector_visible(
            page,
            [
                "div.searchbox-passenger_container",
                'button:has-text("Confirmar")',
            ],
        )
    )


def _hay_modal_infante(page):
    return bool(
        _buscar_selector_visible(
            page,
            [
                '.ant-modal-body:has-text("Infante")',
                '.ant-modal-body:has-text("infante")',
                '.ant-modal-body:has-text("Acepto y entiendo las condiciones")',
            ],
        )
    )


def _aceptar_modal_infante(page):
    if not _hay_modal_infante(page):
        return True

    for _ in range(8):
        if not _hay_modal_infante(page):
            return True

        if _click_selector_visible(
            page,
            [
                'button:has-text("Acepto y entiendo las condiciones")',
                'button:has-text("Acepto y entiendo")',
                'button:has-text("Acepto")',
            ],
            force=True,
        ):
            page.wait_for_timeout(250)
            continue

        page.wait_for_timeout(250)

    return not _hay_modal_infante(page)


def _cerrar_selector_pasajeros(page):
    for _ in range(12):
        _aceptar_modal_infante(page)
        if _hay_modal_infante(page):
            page.wait_for_timeout(200)
            continue

        if _click_selector_visible(
            page,
            [
                'button:has-text("Aplicar")',
                'button:has-text("Listo")',
                'button:has-text("Hecho")',
                'button:has-text("Done")',
                'button:has-text("Confirmar")',
            ],
            force=True,
        ):
            return True
        page.wait_for_timeout(180)
    return False


def _abrir_selector_pasajeros(page):
    _cerrar_calendario_si_abierto(page)
    if _modal_pasajeros_abierto(page):
        return True

    candidatos = [
        'div.wrapper:has(label:has-text("Pasajeros"))',
        'div.wrapper:has(label:has-text("Pasajeros")) .textfield_icon',
        'div.wrapper:has(label:has-text("Pasajeros")) input',
        'div.wrapper:has(label:has-text("Passenger"))',
        'div.wrapper:has(label:has-text("Passageiros"))',
        "#passengers-id",
        '[data-test*="passenger"]',
        'button:has-text("Pasajeros")',
        'button:has-text("Passageiros")',
        'button:has-text("Passenger")',
    ]

    for _ in range(4):
        for selector in candidatos:
            if _click_selector_visible(page, [selector], force=True):
                page.wait_for_timeout(220)
                if _modal_pasajeros_abierto(page):
                    return True
        page.wait_for_timeout(220)

    return False


def _click_boton_contador(page, etiquetas_fila):
    patron = re.compile("|".join(re.escape(etiqueta) for etiqueta in etiquetas_fila), re.IGNORECASE)
    filas = page.locator("div.searchbox-passenger_container, li, div, section").filter(has_text=patron)
    selector_boton_mas = (
        'button.sky-select-number_button:has(.sky-select-number_button_icon[aria-label="more"]), '
        'button.sky-select-number_button:has(span[aria-label="plus"]), '
        'button[aria-label*="Aumentar"], '
        'button[aria-label*="Increase"], '
        'button[aria-label*="Adicionar"], '
        'button[aria-label*="Más"], '
        'button[aria-label*="Mas"], '
        'button:has-text("+")'
    )

    candidatos = []
    for indice in range(filas.count()):
        fila = filas.nth(indice)
        try:
            if not fila.is_visible():
                continue
            texto_fila = _normalizar_texto(fila.inner_text())
            if not patron.search(texto_fila):
                continue
        except Exception:
            continue

        botones_mas = fila.locator(selector_boton_mas)
        visibles = []
        for idx_btn in range(botones_mas.count()):
            boton = botones_mas.nth(idx_btn)
            try:
                if boton.is_visible() and boton.is_enabled():
                    visibles.append(boton)
            except Exception:
                continue

        if visibles:
            candidatos.append((len(visibles), len(texto_fila), visibles[0]))

    candidatos.sort(key=lambda item: (item[0], item[1]))
    if candidatos:
        candidatos[0][2].click()
        return True

    return False


def _configurar_pasajeros_busqueda(page):
    adultos = state.CFG["pasajeros"]["adultos"]
    ninos = state.CFG["pasajeros"]["ninos"]
    infantes = state.CFG["pasajeros"]["infantes"]
    total = adultos + ninos + infantes

    if total <= 1 and ninos == 0 and infantes == 0:
        return

    print(f"--- Configurando pasajeros: ADT={adultos}, CHD={ninos}, INF={infantes} ---")
    abierto = _abrir_selector_pasajeros(page)
    if not abierto:
        raise RuntimeError("No se pudo abrir el selector de pasajeros en la búsqueda.")

    modal_pasajeros = page.locator("div.searchbox-passenger_container")
    if not _buscar_visible(modal_pasajeros):
        for _ in range(3):
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)
            if _abrir_selector_pasajeros(page):
                page.wait_for_timeout(250)
            if _buscar_visible(modal_pasajeros):
                break
        if not _buscar_visible(modal_pasajeros):
            raise RuntimeError("No se logró abrir el modal de pasajeros.")

    _capturar_estado_ui(page, "selector_pasajeros_abierto")

    for _ in range(max(0, adultos - 1)):
        if not _click_boton_contador(page, ["Adulto", "Adultos", "Adult"]):
            raise RuntimeError("No se pudo incrementar la cantidad de adultos.")
        page.wait_for_timeout(150)

    for _ in range(max(0, ninos)):
        if not _click_boton_contador(page, ["Niño", "Niños", "Nino", "Ninos", "Child", "Children", "Criança", "Crianca"]):
            raise RuntimeError("No se pudo incrementar la cantidad de niños.")
        page.wait_for_timeout(150)

    for _ in range(max(0, infantes)):
        if not _click_boton_contador(page, ["Infante", "Infantes", "Infant", "Bebê", "Bebe"]):
            raise RuntimeError("No se pudo incrementar la cantidad de infantes.")
        _aceptar_modal_infante(page)
        page.wait_for_timeout(150)

    _cerrar_selector_pasajeros(page)
    _capturar_estado_ui(page, "selector_pasajeros_configurado")


def _pasajeros_busqueda_aplicados(page):
    adultos = state.CFG["pasajeros"]["adultos"]
    ninos = state.CFG["pasajeros"]["ninos"]
    infantes = state.CFG["pasajeros"]["infantes"]
    total = adultos + ninos + infantes

    if total <= 1 and ninos == 0 and infantes == 0:
        return True

    wrappers = page.locator(
        'div.wrapper:has(label:has-text("Pasajeros")), '
        'div.wrapper:has(label:has-text("Passenger")), '
        'div.wrapper:has(label:has-text("Passageiros")), '
        "#passengers-id"
    )
    patron_total = re.compile(rf"\b{total}\b")

    for indice in range(wrappers.count()):
        item = wrappers.nth(indice)
        try:
            if not item.is_visible():
                continue
            texto = _normalizar_texto(item.inner_text())
            if patron_total.search(texto):
                return True
        except Exception:
            continue
    return False


def _iniciar_busqueda(page):
    _cerrar_panel_login_si_abierto(page)
    if not _click_selector_visible(
        page,
        [
            'button:has-text("Buscar vuelo")',
            'button:has-text("Buscar vuelos")',
            'button:has-text("Buscar")',
            'button:has-text("Buscar voo")',
            'button:has-text("Search")',
            'button[type="submit"]',
            '[data-test*="search"]',
        ],
        force=True,
        requerido=True,
        descripcion="botón Buscar vuelo",
    ):
        raise RuntimeError("No se pudo iniciar la búsqueda de vuelos.")
    page.wait_for_timeout(1500)
    _cerrar_panel_login_si_abierto(page)


def _esperar_resultados_busqueda(page, timeout_ms=45000):
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        gestionar_pausa_edicion(page, "esperando_resultados_busqueda")
        etapa_actual = detectar_etapa_actual(page)
        if etapa_actual != "BUSQUEDA":
            return etapa_actual
        if _buscar_selector_visible(
            page,
            [
                'button:has-text("Elegir vuelo")',
                '[data-test^="is-itinerary-selectFlight"]',
                '[data-test^="is-itinerary-selectRate"]',
            ],
        ):
            return "SELECCION_TARIFA"
        page.wait_for_timeout(500)

    raise RuntimeError(f"La búsqueda no avanzó fuera de BUSQUEDA dentro de {timeout_ms}ms. URL actual: {page.url}")


# ==========================================
# FECHAS
# ==========================================

def _abrir_calendario_fechas(page):
    def calendario_visible():
        return bool(
            _buscar_visible(page.locator("button.vc-title"))
            or _buscar_visible(page.locator('[role="button"].vc-day-content'))
            or _buscar_selector_visible(
                page,
                [
                    ':text("Seleccionar fecha de ida")',
                    ':text("Seleccionar fecha de ida y vuelta")',
                    ':text("Departure date")',
                    ':text("Fecha de ida")',
                ],
            )
        )

    candidatos = [
        'div.wrapper.width-min-calendar .textfield_input',
        'div.wrapper.width-min-calendar .textfield_icon',
        'div.wrapper.width-min-calendar input',
        'div.wrapper:has(label:has-text("Solo ida"))',
        'div.wrapper:has(label:has-text("One way"))',
        'div.wrapper:has(label:has-text("Somente ida"))',
        'div.wrapper:has(label:has-text("Ida-Vuelta"))',
        'div.wrapper:has(label:has-text("Ida y vuelta"))',
        'div.wrapper:has(label:has-text("Round trip"))',
        'div.wrapper:has(label:has-text("Ida e volta"))',
        'div.wrapper:has(label:has-text("Fecha de ida"))',
        'div.wrapper:has(label:has-text("Departure"))',
    ]

    if calendario_visible():
        return

    ultimo_error = None
    for _ in range(4):
        for selector in candidatos:
            try:
                item = _buscar_selector_visible(page, [selector])
                if not item:
                    continue
                item.scroll_into_view_if_needed()
                item.click(force=True)
                page.wait_for_timeout(250)
                if calendario_visible():
                    return
                try:
                    item.click(force=True)
                    page.wait_for_timeout(250)
                    if calendario_visible():
                        return
                except Exception:
                    pass
            except Exception as error:
                ultimo_error = error
                continue

    raise RuntimeError(f"El calendario no quedó visible/listo para seleccionar fechas. Último error: {ultimo_error}")


def _obtener_dias_disponibles_calendario(page):
    dias_filtrados = page.locator('div.vc-day:not(.is-not-in-month) div.vc-day-content[aria-disabled="false"]')
    if _buscar_visible(dias_filtrados):
        return dias_filtrados
    return page.locator('div.vc-day-content[aria-disabled="false"]')


_MESES_VARIANTES = {
    1: ["enero", "ene", "january", "jan", "janeiro"],
    2: ["febrero", "feb", "february", "fevereiro"],
    3: ["marzo", "mar", "march", "marco", "março"],
    4: ["abril", "abr", "april"],
    5: ["mayo", "may", "maio"],
    6: ["junio", "jun", "june", "junho"],
    7: ["julio", "jul", "july", "julho"],
    8: ["agosto", "ago", "aug", "august"],
    9: ["septiembre", "setiembre", "sep", "sept", "september", "set", "setembro"],
    10: ["octubre", "oct", "october", "out", "outubro"],
    11: ["noviembre", "nov", "november"],
    12: ["diciembre", "dic", "dec", "december", "dez", "dezembro"],
}


def _fecha_objetivo_ida():
    return (datetime.now() + timedelta(days=state.CFG["dias"])).date()


def _fecha_objetivo_vuelta():
    return _fecha_objetivo_ida() + timedelta(days=state.CFG.get("dias_retorno", 0))


def _texto_contiene_fecha_objetivo(texto, fecha_objetivo):
    texto_normalizado = _normalizar_texto(texto).lower()
    if not texto_normalizado:
        return False

    if str(fecha_objetivo.year) not in texto_normalizado:
        return False

    numeros = re.findall(r"\d{1,4}", texto_normalizado)
    numeros_normalizados = set()
    for numero in numeros:
        numeros_normalizados.add(numero)
        try:
            numeros_normalizados.add(str(int(numero)))
        except Exception:
            continue

    if str(fecha_objetivo.day) not in numeros_normalizados:
        return False

    if any(mes in texto_normalizado for mes in _MESES_VARIANTES[fecha_objetivo.month]):
        return True

    formatos_numericos = [
        fecha_objetivo.strftime("%d/%m/%Y"),
        fecha_objetivo.strftime("%d-%m-%Y"),
    ]
    return any(formato.lower() in texto_normalizado for formato in formatos_numericos)


def _fecha_aplicada_en_wrapper(page):
    fecha_ida = _fecha_objetivo_ida()
    fecha_vuelta = _fecha_objetivo_vuelta() if state.CFG["tipo_viaje"] == "ROUND_TRIP" else None
    inputs = page.locator(
        "div.wrapper.width-min-calendar input, "
        'div.wrapper:has(label:has-text("Fecha de ida")) input, '
        'div.wrapper:has(label:has-text("Fecha de ida y vuelta")) input, '
        'div.wrapper:has(label:has-text("Departure")) input, '
        'div.wrapper:has(label:has-text("One way")) input, '
        'div.wrapper:has(label:has-text("Solo ida")) input',
    )

    se_encontraron_inputs_visibles = False
    for idx_input in range(inputs.count()):
        campo = inputs.nth(idx_input)
        try:
            if not campo.is_visible():
                continue
            se_encontraron_inputs_visibles = True
            valor = _normalizar_texto(campo.input_value())
            if valor and _texto_contiene_fecha_objetivo(valor, fecha_ida):
                if not fecha_vuelta or _texto_contiene_fecha_objetivo(valor, fecha_vuelta):
                    return True
        except Exception:
            continue

    if se_encontraron_inputs_visibles:
        return False

    wrappers = page.locator(
        "div.wrapper.width-min-calendar, "
        'div.wrapper:has(label:has-text("Fecha de ida")), '
        'div.wrapper:has(label:has-text("Fecha de ida y vuelta")), '
        'div.wrapper:has(label:has-text("Departure"))',
    )

    for indice in range(wrappers.count()):
        item = wrappers.nth(indice)
        try:
            if not item.is_visible():
                continue

            texto = _normalizar_texto(item.inner_text()).replace("  -  ", " - ")
            if not texto or texto.lower() in {"solo ida", "ida-vuelta", "one way", "departure"}:
                continue
            if _texto_contiene_fecha_objetivo(texto, fecha_ida):
                if not fecha_vuelta or _texto_contiene_fecha_objetivo(texto, fecha_vuelta):
                    return True
        except Exception:
            continue
    return False


def _click_dia_calendario(page, dias_locator, indice, etiqueta):
    """Click robusto para días del calendario. Evita fallas por overlays/transiciones."""
    total = dias_locator.count()
    if total == 0:
        raise RuntimeError(f"No hay días disponibles para seleccionar ({etiqueta}).")

    indice_real = max(0, min(indice, total - 1))
    objetivo = dias_locator.nth(indice_real)

    try:
        objetivo.scroll_into_view_if_needed()
    except Exception:
        pass

    try:
        objetivo.click(timeout=4000)
        return indice_real
    except Exception:
        pass

    try:
        objetivo.click(force=True, timeout=4000)
        return indice_real
    except Exception:
        pass

    handle = objetivo.element_handle()
    if handle:
        try:
            page.evaluate("(el) => el.click()", handle)
            return indice_real
        except Exception:
            pass

    raise RuntimeError(f"No se pudo seleccionar fecha de {etiqueta} en índice {indice_real}.")


def _click_fecha_objetivo_visible(page, fecha_objetivo):
    titulos_vcalendar = page.locator("button.vc-title")
    for indice in range(titulos_vcalendar.count()):
        titulo = titulos_vcalendar.nth(indice)
        try:
            if not titulo.is_visible():
                continue
            texto_titulo = _normalizar_texto(titulo.inner_text()).lower()
            if str(fecha_objetivo.year) not in texto_titulo:
                continue
            if not any(mes in texto_titulo for mes in _MESES_VARIANTES[fecha_objetivo.month]):
                continue

            pane = titulo.locator('xpath=ancestor::div[contains(@class,"vc-pane")][1]')
            dias_pane = pane.locator('[role="button"].vc-day-content')
            for idx_dia in range(dias_pane.count()):
                dia = dias_pane.nth(idx_dia)
                try:
                    if not dia.is_visible():
                        continue
                    if _normalizar_texto(dia.inner_text()) != str(fecha_objetivo.day):
                        continue
                    clases = (dia.get_attribute("class") or "").lower()
                    if "vc-disabled" in clases or "disabled" in clases:
                        continue
                    dia.click(force=True, timeout=4000)
                    return True
                except Exception:
                    continue
        except Exception:
            continue

    payload = {
        "day": str(fecha_objetivo.day),
        "year": str(fecha_objetivo.year),
        "month_names": _MESES_VARIANTES[fecha_objetivo.month],
    }

    return page.evaluate(
        """
        ({ day, year, month_names }) => {
          const norm = (value) =>
            (value || "")
              .normalize("NFD")
              .replace(/[\\u0300-\\u036f]/g, "")
              .toLowerCase()
              .replace(/\\s+/g, " ")
              .trim();

          const visible = (el) => {
            if (!el || !el.isConnected) return false;
            const style = window.getComputedStyle(el);
            if (!style || style.display === "none" || style.visibility === "hidden") return false;
            const rect = el.getBoundingClientRect();
            return rect.width > 6 && rect.height > 6;
          };

          const disabled = (el) => {
            const cls = norm(el?.className || "");
            return (
              !el ||
              el.disabled ||
              el.getAttribute("aria-disabled") === "true" ||
              cls.includes("disabled") ||
              cls.includes("unavailable") ||
              cls.includes("not-in-month") ||
              cls.includes("blocked")
            );
          };

          const monthTokens = month_names.map(norm);
          const all = [...document.querySelectorAll("body *")].filter(visible);
          const monthHeaders = all.filter((el) => monthTokens.includes(norm(el.textContent)));

          for (const header of monthHeaders) {
            let container = header;
            for (let depth = 0; depth < 7 && container; depth += 1, container = container.parentElement) {
              const text = norm(container?.textContent);
              if (!text || !text.includes(year) || !monthTokens.some((month) => text.includes(month))) continue;

              const candidates = [...container.querySelectorAll("button, div, span")].filter((el) => {
                return visible(el) && !disabled(el) && norm(el.textContent) === day;
              });
              if (candidates.length > 0) {
                candidates[0].click();
                return true;
              }
            }
          }

          const attrCandidates = all.filter((el) => {
            if (disabled(el)) return false;
            const haystack = norm(
              [
                el.getAttribute("aria-label"),
                el.getAttribute("title"),
                el.getAttribute("data-date"),
                el.textContent,
              ]
                .filter(Boolean)
                .join(" ")
            );
            return haystack.includes(year) && monthTokens.some((month) => haystack.includes(month)) && haystack.includes(day);
          });
          if (attrCandidates.length > 0) {
            attrCandidates[0].click();
            return true;
          }

          return false;
        }
        """,
        payload,
    )


def _avanzar_calendario(page):
    return _click_selector_visible(
        page,
        [
            'button[aria-label*="siguiente" i]',
            'button[aria-label*="next" i]',
            'button[aria-label*="mes siguiente" i]',
            'button:has(svg[class*="right"])',
            'button:has(i[class*="right"])',
            '[class*="calendar"] [class*="right"]',
        ],
        force=True,
        requerido=False,
    )


def _seleccionar_fecha_objetivo(page, fecha_objetivo, etiqueta):
    for _ in range(10):
        gestionar_pausa_edicion(page, f"seleccion_fecha_{etiqueta}")
        if _click_fecha_objetivo_visible(page, fecha_objetivo):
            page.wait_for_timeout(450)
            return
        if not _avanzar_calendario(page):
            break
        page.wait_for_timeout(350)

    raise RuntimeError(f"No se pudo seleccionar fecha de {etiqueta}: {fecha_objetivo.isoformat()}.")


def _seleccionar_fechas_por_indice(page):
    dias_disponibles = _obtener_dias_disponibles_calendario(page)
    cantidad_dias = dias_disponibles.count()
    if cantidad_dias == 0:
        raise RuntimeError("No hay días disponibles para seleccionar en el calendario.")

    indice_ida = min(state.CFG["dias"], cantidad_dias - 1)
    indice_ida = _click_dia_calendario(page, dias_disponibles, indice_ida, "ida")

    if state.CFG["tipo_viaje"] == "ROUND_TRIP":
        page.wait_for_timeout(300)
        dias_retorno = _obtener_dias_disponibles_calendario(page)
        cantidad_retorno = dias_retorno.count()
        if cantidad_retorno == 0:
            raise RuntimeError("No hay días disponibles para seleccionar fecha de vuelta.")

        indice_vuelta = min(indice_ida + state.CFG["dias_retorno"], cantidad_retorno - 1)
        if indice_vuelta <= indice_ida and cantidad_retorno > indice_ida + 1:
            indice_vuelta = indice_ida + 1

        _click_dia_calendario(page, dias_retorno, indice_vuelta, "vuelta")


def _seleccionar_fechas(page):
    page.wait_for_timeout(600)
    _abrir_calendario_fechas(page)
    try:
        _seleccionar_fecha_objetivo(page, _fecha_objetivo_ida(), "ida")
        if state.CFG["tipo_viaje"] == "ROUND_TRIP":
            _seleccionar_fecha_objetivo(page, _fecha_objetivo_vuelta(), "vuelta")
    except Exception as error:
        print(f"⚠️ Selección exacta de fechas falló ({error}). Se intenta fallback por índice.")
        _seleccionar_fechas_por_indice(page)

    if not _fecha_aplicada_en_wrapper(page):
        raise RuntimeError("La fecha seleccionada no quedó aplicada en el buscador.")

    _cerrar_calendario_si_abierto(page)


# ==========================================
# VUELO Y TARIFA
# ==========================================

def _seleccionar_vuelo_y_tarifa(page, tramo):
    print(f"--- Seleccionando Vuelo ({tramo}) ---")

    try:
        page.wait_for_selector(
            'button:has-text("Elegir vuelo"), [data-test^="is-itinerary-selectFlight"]',
            timeout=30000,
        )
    except Exception as error:
        raise RuntimeError(f"No se cargaron vuelos para {tramo}: {error}")

    page.wait_for_timeout(2500)
    botones_vuelo = page.locator('button:has-text("Elegir vuelo")')
    if botones_vuelo.count() == 0:
        botones_vuelo = page.locator('[data-test^="is-itinerary-selectFlight"]')

    seleccionado = False
    for indice in range(botones_vuelo.count()):
        try:
            boton_vuelo = botones_vuelo.nth(indice)
            url_previa = page.url or ""
            boton_vuelo.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            boton_vuelo.click(force=True)
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                url_actual = page.url or ""
                if _buscar_selector_visible(page, ['[data-test^="is-itinerary-selectRate"]']):
                    seleccionado = True
                    break
                if url_actual != url_previa and any(
                    fragmento in url_actual.lower()
                    for fragmento in ("/seats", "/additional-services", "passenger-detail", "checkout")
                ):
                    seleccionado = True
                    break
                page.wait_for_timeout(250)
            if not seleccionado:
                raise RuntimeError("La UI no avanzó a tarifas ni a la siguiente etapa.")
            seleccionado = True
            break
        except Exception as error:
            print(f"⚠️ Click de vuelo {indice} ({tramo}) falló: {error}")

    if not seleccionado:
        raise RuntimeError(f"No fue posible seleccionar vuelo para {tramo}.")

    botones_tarifa = page.locator('[data-test^="is-itinerary-selectRate"] button')
    if _url_contiene(page, "/seats") or _url_contiene(page, "/additional-services"):
        return
    if botones_tarifa.count() == 0:
        botones_tarifa = page.locator('button:has-text("Seleccionar"), button:has-text("Selecionar"), button:has-text("Select")')

    if botones_tarifa.count() == 0:
        raise RuntimeError(f"No se encontraron tarifas para {tramo}.")

    if botones_tarifa.count() > 1:
        botones_tarifa.nth(1).click()
    else:
        botones_tarifa.first.click()

    try:
        page.wait_for_timeout(1000)
        btn_marketing = page.get_by_role("button", name="Seguir con mi tarifa actual")
        if btn_marketing.is_visible():
            btn_marketing.click()
    except Exception:
        pass


def _url_contiene(page, fragmento):
    return fragmento in ((page.url or "").lower())


def _esperar_cambio_post_accion(page, url_previa, timeout_ms=12000):
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        gestionar_pausa_edicion(page, "esperando_cambio_post_accion")
        if (page.url or "") != url_previa:
            return True
        if _buscar_selector_visible(
            page,
            [
                'button:has-text("Seguir sin elegir")',
                'button:has-text("Elegir asiento ahora")',
                'button:has-text("Continue without selecting")',
                'button:has-text("Choose seat now")',
                'button:has-text("Finalizar")',
                'button:has-text("Continuar")',
            ],
        ):
            return True
        page.wait_for_timeout(200)
    return False


def _click_primer_selector(page, selectores, timeout=2500):
    for selector in selectores:
        locator = page.locator(selector)
        try:
            if locator.count() == 0:
                continue
        except Exception:
            continue

        for indice in range(locator.count()):
            item = locator.nth(indice)
            try:
                item.scroll_into_view_if_needed()
            except Exception:
                pass
            try:
                item.click(force=True, timeout=timeout)
                return True
            except Exception:
                continue
    return False


def _continuar_modal_asientos_sin_elegir(page):
    return _click_selector_visible(
        page,
        [
            'button:has-text("Seguir sin elegir")',
            'button:has-text("Continuar sin elegir")',
            'button:has-text("Continue without selecting")',
            'button:has-text("Continue without seat selection")',
            'button:has-text("Continuar sin seleccionar asiento")',
        ],
        force=True,
        requerido=False,
    )


def _seleccionar_primer_asiento_disponible(page):
    selectores = [
        '[data-test*="seat"] button:not([disabled])',
        '[data-testid*="seat"] button:not([disabled])',
        'button[class*="seat"]:not([disabled])',
        '[class*="seat-map"] button:not([disabled])',
        '[class*="seat"] [role="button"]',
        'svg [class*="seat"][class*="available"]',
        'svg [class*="available"]',
    ]

    for selector in selectores:
        locator = page.locator(selector)
        for indice in range(locator.count()):
            item = locator.nth(indice)
            try:
                if not item.is_visible():
                    continue
                item.scroll_into_view_if_needed()
                item.click(force=True, timeout=2500)
                page.wait_for_timeout(500)
                return True
            except Exception:
                continue

    return False


def _resolver_pantalla_asientos(page):
    estrategia = state.CFG.get("extras", {}).get("seleccion_asiento", "SKIP")
    deadline = time.monotonic() + 12
    auto_intentado = estrategia != "AUTO"

    while time.monotonic() < deadline:
        gestionar_pausa_edicion(page, "resolver_asientos")

        if not _url_contiene(page, "/seats"):
            return True

        if detectar_etapa_actual(page) in {"DATOS_PASAJERO", "CHECKOUT"}:
            return True

        url_previa = page.url or ""

        if not auto_intentado:
            auto_intentado = True
            if _seleccionar_primer_asiento_disponible(page):
                print("🪑 Asiento seleccionado automáticamente.")
            else:
                print("⚠️ No se encontró asiento disponible con selectores conocidos. Se continuará sin elegir.")

        if _click_selector_visible(
            page,
            [
                'button:has-text("Continuar al siguiente vuelo")',
                'button:has-text("Continuar ao próximo voo")',
                'button:has-text("Continue to next flight")',
                'button:has-text("Quiero un asiento aleatorio")',
                'button:has-text("I want a random seat")',
                'button:has-text("Continuar")',
                'button:has-text("Continue")',
            ],
            force=True,
            requerido=False,
        ) or _click_primer_selector(
            page,
            [
                'button:has-text("Continuar al siguiente vuelo")',
                'button:has-text("Continuar ao próximo voo")',
                'button:has-text("Continue to next flight")',
                'button:has-text("Quiero un asiento aleatorio")',
                'button:has-text("I want a random seat")',
                'button:has-text("Continuar")',
                'button:has-text("Continue")',
            ],
        ):
            page.wait_for_timeout(600)
            _continuar_modal_asientos_sin_elegir(page)
            if _esperar_cambio_post_accion(page, url_previa):
                return True

        if _continuar_modal_asientos_sin_elegir(page) or _click_primer_selector(
            page,
            [
                'button:has-text("Seguir sin elegir")',
                'button:has-text("Continuar sin elegir")',
                'button:has-text("Continue without selecting")',
            ],
        ):
            if _esperar_cambio_post_accion(page, url_previa):
                return True

        page.wait_for_timeout(700)

    return not _url_contiene(page, "/seats")


def _contar_unidades_servicio(page):
    patron = re.compile(r"^\d+$")
    candidatos = page.locator("div, span, p")
    for indice in range(candidatos.count()):
        item = candidatos.nth(indice)
        try:
            if not item.is_visible():
                continue
            texto = _normalizar_texto(item.inner_text())
            if patron.match(texto):
                return int(texto)
        except Exception:
            continue
    return 0


def _ajustar_cantidad_servicio_lateral(page, cantidad_objetivo):
    if cantidad_objetivo <= 0:
        return True

    boton_sumar = None
    deadline = time.monotonic() + 5

    while time.monotonic() < deadline and boton_sumar is None:
        gestionar_pausa_edicion(page, "ancillary_panel_lateral")
        botones = page.locator("button.sky-select-number_button")
        for indice in range(botones.count()):
            boton = botones.nth(indice)
            try:
                if boton.is_visible() and boton.is_enabled():
                    boton_sumar = boton
            except Exception:
                continue
        if boton_sumar is None:
            page.wait_for_timeout(200)

    if not boton_sumar:
        return False

    for _ in range(cantidad_objetivo):
        boton_sumar.click(force=True)
        page.wait_for_timeout(250)
    return True


def _seleccionar_servicio_adicional(page, etiquetas, cantidad_objetivo):
    if cantidad_objetivo <= 0:
        return False

    direct_selectores = []
    for etiqueta in etiquetas:
        direct_selectores.extend(
            [
                f'section:has-text("{etiqueta}") button:has-text("Agregar")',
                f'article:has-text("{etiqueta}") button:has-text("Agregar")',
                f'div:has-text("{etiqueta}") button:has-text("Agregar")',
            ]
        )

    if not _click_selector_visible(page, direct_selectores, force=True, requerido=False):
        patron = re.compile("|".join(re.escape(etiqueta) for etiqueta in etiquetas), re.IGNORECASE)
        tarjetas = page.locator("section, article, div").filter(has_text=patron)

        for indice in range(tarjetas.count()):
            tarjeta = tarjetas.nth(indice)
            try:
                if not tarjeta.is_visible():
                    continue
                boton_agregar = _buscar_visible(
                    tarjeta.locator('button:has-text("Agregar"), button:has-text("Add"), button:has-text("Adicionar")')
                )
                if not boton_agregar:
                    continue
                boton_agregar.scroll_into_view_if_needed()
                boton_agregar.click(force=True)
                break
            except Exception:
                continue
        else:
            return False

    page.wait_for_timeout(600)

    if _ajustar_cantidad_servicio_lateral(page, cantidad_objetivo):
        _click_selector_visible(
            page,
            [
                'button:has-text("Finalizar")',
                'button:has-text("Guardar y continuar")',
                'button:has-text("Done")',
            ],
            force=True,
            requerido=False,
        )
        page.wait_for_timeout(800)
        return True

    return False


def _resolver_pantalla_ancillaries(page):
    extras = state.CFG.get("extras", {})
    maletas_cabina = extras.get("maletas_cabina", 0)
    maletas_bodega = extras.get("maletas_bodega", 0)
    deadline = time.monotonic() + 12
    cabina_pendiente = maletas_cabina > 0
    bodega_pendiente = maletas_bodega > 0

    while time.monotonic() < deadline:
        gestionar_pausa_edicion(page, "resolver_ancillaries")

        if not _url_contiene(page, "/additional-services"):
            return True

        if detectar_etapa_actual(page) in {"DATOS_PASAJERO", "CHECKOUT"}:
            return True

        url_previa = page.url or ""

        if cabina_pendiente:
            cabina_pendiente = False
            if not _seleccionar_servicio_adicional(
                page,
                ["Equipaje en cabina", "Cabin bag", "Cabin baggage"],
                maletas_cabina,
            ):
                print(f"⚠️ No se pudo agregar equipaje de cabina solicitado ({maletas_cabina}).")

        if bodega_pendiente:
            bodega_pendiente = False
            if not _seleccionar_servicio_adicional(
                page,
                ["Equipaje en bodega", "Checked baggage", "Equipaje facturado"],
                maletas_bodega,
            ):
                print(f"⚠️ No se pudo agregar equipaje en bodega solicitado ({maletas_bodega}).")

        if _click_selector_visible(
            page,
            [
                'button:has-text("Continuar")',
                'button:has-text("Guardar y continuar")',
                'button:has-text("Continue")',
            ],
            force=True,
            requerido=False,
        ) or _click_primer_selector(
            page,
            [
                'button:has-text("Continuar")',
                'button:has-text("Guardar y continuar")',
                'button:has-text("Continue")',
            ],
        ):
            page.wait_for_timeout(900)
            if _esperar_cambio_post_accion(page, url_previa):
                return True

        page.wait_for_timeout(700)

    return not _url_contiene(page, "/additional-services")


def _saltar_extras(page, verbose=True):
    if verbose:
        print("--- Saltando Extras ---")
    deadline = time.monotonic() + 25

    while time.monotonic() < deadline:
        if _url_contiene(page, "/seats"):
            if not _resolver_pantalla_asientos(page):
                print("⚠️ Pantalla de asientos aún no lista para avanzar. Reintentando...")
                return False
            continue

        if _url_contiene(page, "/additional-services"):
            if not _resolver_pantalla_ancillaries(page):
                print("⚠️ Pantalla de servicios adicionales aún no lista para avanzar. Reintentando...")
                return False
            continue

        return True

    botones = [
        [
            'button:has-text("Continuar al siguiente vuelo")',
            'button:has-text("Continuar ao próximo voo")',
            'button:has-text("Continue to next flight")',
        ],
        [
            'button:has-text("Continuar sin elegir")',
            'button:has-text("Continuar sin seleccionar asiento")',
            'button:has-text("Continuar sin seleccionar")',
            'button:has-text("Continuar sin asientos")',
            'button:has-text("Continuar sem selecionar")',
            'button:has-text("Continue without selecting")',
            'button:has-text("Continue without seat selection")',
        ],
        [
            'button:has-text("Guardar y continuar")',
            'button:has-text("Siguiente")',
            'button:has-text("Continuar")',
            'button:has-text("Continuar compra")',
            'button:has-text("Continue")',
        ],
    ]

    for candidatos in botones:
        try:
            if _click_selector_visible(page, candidatos, force=True):
                page.wait_for_timeout(600)
        except Exception as error:
            print(f"⚠️ No se pudo clickear '{candidatos[0]}': {error}")

    return not (_url_contiene(page, "/seats") or _url_contiene(page, "/additional-services"))
