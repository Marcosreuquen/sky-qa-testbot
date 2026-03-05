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
)


# ==========================================
# HOME Y LOGIN
# ==========================================

def _esperar_home_lista(page, timeout_ms=45000):
    """Espera a que el flight-box esté listo para interacción."""
    deadline = time.monotonic() + timeout_ms / 1000
    ultimo_error = None
    while time.monotonic() < deadline:
        try:
            origen = _buscar_selector_visible(
                page,
                [
                    "#origin-id",
                    "#origin-id input",
                    'input[placeholder*="Desde" i]',
                    'input[aria-label*="Desde" i]',
                ],
            )
            destino = _buscar_selector_visible(
                page,
                [
                    "#destination-id",
                    "#destination-id input",
                    'input[placeholder*="Hacia" i]',
                    'input[aria-label*="Hacia" i]',
                ],
            )
            boton_buscar = _buscar_selector_visible(
                page,
                [
                    'button:has-text("Buscar vuelo")',
                    'button:has-text("Buscar voo")',
                    'button:has-text("Search")',
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
    dias_calendario = page.locator('div.vc-day-content[aria-disabled="false"]')
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


# ==========================================
# FECHAS
# ==========================================

def _abrir_calendario_fechas(page):
    candidatos = [
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

    abierto = _click_selector_visible(page, candidatos, force=True)
    if not abierto:
        raise RuntimeError("No se pudo abrir el calendario de fechas.")

    for _ in range(20):
        if _buscar_visible(page.locator('div.vc-day-content[aria-disabled="false"]')):
            return
        page.wait_for_timeout(150)

    raise RuntimeError("El calendario no mostró días habilitados.")


def _obtener_dias_disponibles_calendario(page):
    dias_filtrados = page.locator('div.vc-day:not(.is-not-in-month) div.vc-day-content[aria-disabled="false"]')
    if _buscar_visible(dias_filtrados):
        return dias_filtrados
    return page.locator('div.vc-day-content[aria-disabled="false"]')


def _fecha_aplicada_en_wrapper(page):
    patron_fecha = re.compile(r"\b\d{1,2}\s+[A-Za-zÁÉÍÓÚáéíóú]{3,}\s+\d{4}\b")
    wrappers = page.locator(
        "div.wrapper.width-min-calendar, "
        'div.wrapper:has(.sky-layout-calendar), '
        'div.wrapper:has(.inner-component-calendar), '
        'div.wrapper:has(label:has-text("Fecha de ida")), '
        'div.wrapper:has(label:has-text("Fecha de ida y vuelta")), '
        'div.wrapper:has(label:has-text("Departure"))',
    )

    for indice in range(wrappers.count()):
        item = wrappers.nth(indice)
        try:
            if not item.is_visible():
                continue

            inputs = item.locator("input")
            for idx_input in range(inputs.count()):
                campo = inputs.nth(idx_input)
                try:
                    if not campo.is_visible():
                        continue
                    valor = _normalizar_texto(campo.input_value())
                    if valor and patron_fecha.search(valor):
                        return True
                except Exception:
                    continue

            texto = _normalizar_texto(item.inner_text()).replace("  -  ", " - ")
            if patron_fecha.search(texto):
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


def _seleccionar_fechas(page):
    page.wait_for_timeout(600)
    _abrir_calendario_fechas(page)
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
            boton_vuelo.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            boton_vuelo.click(force=True)
            page.wait_for_selector('[data-test^="is-itinerary-selectRate"]', timeout=5000)
            seleccionado = True
            break
        except Exception as error:
            print(f"⚠️ Click de vuelo {indice} ({tramo}) falló: {error}")

    if not seleccionado:
        raise RuntimeError(f"No fue posible seleccionar vuelo para {tramo}.")

    botones_tarifa = page.locator('[data-test^="is-itinerary-selectRate"] button')
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


def _saltar_extras(page):
    print("--- Saltando Extras ---")
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
