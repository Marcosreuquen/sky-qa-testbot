import os
import re
import time
from datetime import datetime

from playwright._impl._errors import TargetClosedError
from playwright.sync_api import Playwright, expect, sync_playwright

from cli import aplicar_args, parse_args

# Evita ruido deprecado del runtime Node usado por Playwright (DEP0169).
_node_options = os.environ.get("NODE_OPTIONS", "").strip()
if "--no-deprecation" not in _node_options.split():
    os.environ["NODE_OPTIONS"] = f"{_node_options} --no-deprecation".strip()

# ==========================================
# 🤖 INICIO DEL BOT
# ==========================================

# Configuración resuelta (defaults + CLI overrides)
CFG = aplicar_args(parse_args())
EXPLORACION_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
EXPLORACION_DIR = os.path.join("screenshots_pruebas", f"exploracion_{EXPLORACION_RUN_ID}")


def pausar_en_checkpoint(page, checkpoint_actual):
    """Pausa el bot si se alcanza el checkpoint configurado"""
    if CFG["checkpoint"] == checkpoint_actual:
        print(f"\n⏸️  CHECKPOINT ALCANZADO: {checkpoint_actual}")
        print("🖱️  Puedes interactuar manualmente con la página.")
        print("▶️  Presiona 'Resume' en el inspector para continuar o cerrar.\n")
        if CFG.get("headless"):
            print("ℹ️  Headless activo: se omite page.pause() y se detiene la ejecución en el checkpoint.")
            return True
        page.pause()
        return True
    return False


def _activar_modo_manual(page):
    if CFG.get("headless"):
        print("ℹ️ Modo headless: se omite page.pause().")
        return
    page.pause()


def _normalizar_texto(texto):
    return " ".join((texto or "").split())


def _listar_textos_visibles(locator, limite=25):
    valores = []
    try:
        cantidad = min(locator.count(), limite)
    except Exception:
        return valores

    for indice in range(cantidad):
        item = locator.nth(indice)
        try:
            if not item.is_visible():
                continue
            texto = _normalizar_texto(item.inner_text())
            if texto and texto not in valores:
                valores.append(texto)
        except Exception:
            continue
    return valores


def _listar_aria_labels(locator, limite=25):
    valores = []
    try:
        cantidad = min(locator.count(), limite)
    except Exception:
        return valores

    for indice in range(cantidad):
        item = locator.nth(indice)
        try:
            if not item.is_visible():
                continue
            label = _normalizar_texto(item.get_attribute("aria-label"))
            if label and label not in valores:
                valores.append(label)
        except Exception:
            continue
    return valores


def _capturar_estado_ui(page, etapa):
    if not CFG.get("modo_exploracion"):
        return

    os.makedirs(EXPLORACION_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefijo = os.path.join(EXPLORACION_DIR, f"{timestamp}_{etapa}")

    screenshot_path = f"{prefijo}.png"
    reporte_path = f"{prefijo}.txt"

    try:
        page.screenshot(path=screenshot_path, full_page=True)
    except Exception as error:
        print(f"⚠️ Exploración: no se pudo guardar screenshot en etapa '{etapa}': {error}")

    labels = _listar_textos_visibles(page.locator("label"))
    botones = _listar_textos_visibles(page.locator("button"))
    titulos = _listar_textos_visibles(page.locator("h1, h2, h3, h4"))
    aria_sumar = _listar_aria_labels(
        page.locator(
            'button[aria-label*="Aumentar"], '
            'button[aria-label*="Increase"], '
            'button[aria-label*="Adicionar"], '
            'button[aria-label*="Más"], '
            'button[aria-label*="Mas"]',
        )
    )

    with open(reporte_path, "w", encoding="utf-8") as archivo:
        archivo.write(f"etapa: {etapa}\n")
        archivo.write(f"url: {page.url}\n\n")
        archivo.write("titulos_visibles:\n")
        for valor in titulos:
            archivo.write(f"- {valor}\n")
        archivo.write("\nlabels_visibles:\n")
        for valor in labels:
            archivo.write(f"- {valor}\n")
        archivo.write("\nbotones_visibles:\n")
        for valor in botones:
            archivo.write(f"- {valor}\n")
        archivo.write("\naria_labels_sumar:\n")
        for valor in aria_sumar:
            archivo.write(f"- {valor}\n")

    print(f"🧪 Exploración UI [{etapa}] -> {screenshot_path}")
    print(f"🧾 Reporte UI [{etapa}] -> {reporte_path}")


def _guardar_html_debug(page, etapa):
    base_dir = EXPLORACION_DIR if CFG.get("modo_exploracion") else "screenshots_pruebas"
    os.makedirs(base_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = os.path.join(base_dir, f"{timestamp}_{etapa}.html")
    try:
        with open(html_path, "w", encoding="utf-8") as archivo:
            archivo.write(page.content())
        print(f"🧾 HTML debug [{etapa}] -> {html_path}")
    except Exception as error:
        print(f"⚠️ No se pudo guardar HTML debug [{etapa}]: {error}")


def _esperar_home_lista(page, timeout_ms=45000):
    """Espera a que el flight-box esté listo para interacción."""
    inicio = datetime.now()
    ultimo_error = None
    while (datetime.now() - inicio).total_seconds() * 1000 < timeout_ms:
        try:
            # En SKY el input editable puede aparecer recién tras click en el contenedor.
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


def _es_pagina_reutilizable(page):
    try:
        url = (page.url or "").strip().lower()
    except Exception:
        return False
    if not url:
        return False
    if url in {"about:blank", "chrome://newtab/", "chrome://new-tab-page/"}:
        return True
    return url.startswith("chrome://newtab")


def _buscar_visible(locator):
    """Retorna el primer elemento visible de un locator o None."""
    try:
        cantidad = locator.count()
    except Exception:
        return None

    for indice in range(cantidad):
        item = locator.nth(indice)
        try:
            if item.is_visible():
                return item
        except Exception:
            continue
    return None


def _buscar_selector_visible(page, selectores):
    for selector in selectores:
        item = _buscar_visible(page.locator(selector))
        if item:
            return item
    return None


def _click_selector_visible(page, selectores, force=False, descripcion=None, requerido=False):
    item = _buscar_selector_visible(page, selectores)
    if not item:
        if requerido:
            raise RuntimeError(f"No se encontró elemento visible: {descripcion or selectores}")
        return False
    item.scroll_into_view_if_needed()
    item.click(force=force)
    return True


def _click_todos_selectores_visibles(page, selectores, force=False):
    clickeado = False
    for selector in selectores:
        locator = page.locator(selector)
        for indice in range(locator.count()):
            item = locator.nth(indice)
            try:
                if not item.is_visible():
                    continue
                if not item.is_enabled():
                    continue
                item.scroll_into_view_if_needed()
                item.click(force=force)
                clickeado = True
                page.wait_for_timeout(120)
            except Exception:
                continue
    return clickeado


def _rellenar_input_visible(page, selectores, valor, requerido=False):
    item = _buscar_selector_visible(page, selectores)
    if not item:
        if requerido:
            raise RuntimeError(f"No se encontró input visible: {selectores}")
        return False
    try:
        if not item.is_enabled():
            if requerido:
                raise RuntimeError(f"Input deshabilitado: {selectores}")
            return False
    except Exception:
        if requerido:
            raise RuntimeError(f"No se pudo validar estado del input: {selectores}")
        return False

    try:
        if not item.is_editable():
            if requerido:
                raise RuntimeError(f"Input no editable: {selectores}")
            return False
    except Exception:
        if requerido:
            raise RuntimeError(f"No se pudo validar edición del input: {selectores}")
        return False

    item.fill(str(valor), timeout=2500)
    return True


def _click_texto_visible(page, texto, exacto=True):
    locator = page.get_by_text(texto, exact=exacto)
    item = _buscar_visible(locator)
    if item:
        item.click()
        return True
    return False


def _click_ultimo_texto_visible(locator, force=False):
    try:
        for indice in range(locator.count() - 1, -1, -1):
            item = locator.nth(indice)
            if not item.is_visible():
                continue
            item.scroll_into_view_if_needed()
            item.click(force=force)
            return True
    except Exception:
        return False
    return False


def _input_editable(locator_inputs):
    try:
        cantidad = locator_inputs.count()
    except Exception:
        return None

    for indice in range(cantidad):
        item = locator_inputs.nth(indice)
        try:
            if item.is_visible() and item.is_editable():
                return item
        except Exception:
            continue
    return None


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

    # Intento 1: match exacto del nombre de ciudad
    if _click_texto_visible(page, ciudad, exacto=True):
        return

    # Intento 2: match parcial (ej: "La Serena (LSC)")
    opcion = _buscar_visible(page.get_by_text(re.compile(re.escape(ciudad), re.IGNORECASE)))
    if opcion:
        opcion.click()
        return

    # Intento 3: primera opción visible del dropdown/autocomplete
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

    # Fallback final: algunos listados aceptan Enter sobre la primera sugerencia.
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


def _seleccionar_tipo_viaje(page):
    tipo_viaje = CFG["tipo_viaje"]
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

    # Fallback: para ONE_WAY muchas veces ya está seleccionado por defecto.
    if tipo_viaje == "ONE_WAY":
        print("⚠️ No se encontró control explícito de 'Solo ida'. Se asume valor por defecto.")
        return

    raise RuntimeError(f"No se pudo seleccionar tipo de viaje '{tipo_viaje}'.")


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

    # Prioriza la fila más específica (menos botones visibles y texto más corto).
    candidatos.sort(key=lambda item: (item[0], item[1]))
    if candidatos:
        candidatos[0][2].click()
        return True

    return False


def _configurar_pasajeros_busqueda(page):
    adultos = CFG["pasajeros"]["adultos"]
    ninos = CFG["pasajeros"]["ninos"]
    infantes = CFG["pasajeros"]["infantes"]
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

    # Cerrar selector si existe botón explícito
    _cerrar_selector_pasajeros(page)
    _capturar_estado_ui(page, "selector_pasajeros_configurado")


def _seleccionar_fechas(page):
    page.wait_for_timeout(600)
    _abrir_calendario_fechas(page)
    dias_disponibles = _obtener_dias_disponibles_calendario(page)
    cantidad_dias = dias_disponibles.count()
    if cantidad_dias == 0:
        raise RuntimeError("No hay días disponibles para seleccionar en el calendario.")

    indice_ida = min(CFG["dias"], cantidad_dias - 1)
    indice_ida = _click_dia_calendario(page, dias_disponibles, indice_ida, "ida")

    if CFG["tipo_viaje"] == "ROUND_TRIP":
        page.wait_for_timeout(300)
        dias_retorno = _obtener_dias_disponibles_calendario(page)
        cantidad_retorno = dias_retorno.count()
        if cantidad_retorno == 0:
            raise RuntimeError("No hay días disponibles para seleccionar fecha de vuelta.")

        indice_vuelta = min(indice_ida + CFG["dias_retorno"], cantidad_retorno - 1)
        if indice_vuelta <= indice_ida and cantidad_retorno > indice_ida + 1:
            indice_vuelta = indice_ida + 1

        _click_dia_calendario(page, dias_retorno, indice_vuelta, "vuelta")

    if not _fecha_aplicada_en_wrapper(page):
        raise RuntimeError("La fecha seleccionada no quedó aplicada en el buscador.")

    _cerrar_calendario_si_abierto(page)


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
    """
    Click robusto para días del calendario.
    Evita fallas por overlays/transiciones del componente.
    """
    total = dias_locator.count()
    if total == 0:
        raise RuntimeError(f"No hay días disponibles para seleccionar ({etiqueta}).")

    indice_real = max(0, min(indice, total - 1))
    objetivo = dias_locator.nth(indice_real)

    try:
        objetivo.scroll_into_view_if_needed()
    except Exception:
        pass

    # 1) Click normal
    try:
        objetivo.click(timeout=4000)
        return indice_real
    except Exception:
        pass

    # 2) Click forzado (evita validación de hit-target)
    try:
        objetivo.click(force=True, timeout=4000)
        return indice_real
    except Exception:
        pass

    # 3) Fallback JS click
    handle = objetivo.element_handle()
    if handle:
        try:
            page.evaluate("(el) => el.click()", handle)
            return indice_real
        except Exception:
            pass

    raise RuntimeError(f"No se pudo seleccionar fecha de {etiqueta} en índice {indice_real}.")


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


def _esperar_o_avanzar_hasta_pasajeros(page, timeout_ms=60000):
    inicio = datetime.now()

    while (datetime.now() - inicio).total_seconds() * 1000 < timeout_ms:
        url_actual = page.url or ""
        if "passenger-detail" in url_actual or "checkout" in url_actual:
            return

        _saltar_extras(page)
        page.wait_for_timeout(1200)

    raise RuntimeError(
        f"No se pudo avanzar a passenger-detail/checkout dentro de {timeout_ms}ms. URL actual: {page.url}",
    )


def _avanzar_a_checkout_desde_passenger(page, timeout_ms=60000):
    inicio = datetime.now()

    while (datetime.now() - inicio).total_seconds() * 1000 < timeout_ms:
        url_actual = page.url or ""
        if "checkout" in url_actual:
            return

        if "passenger-detail" in url_actual:
            _click_todos_selectores_visibles(
                page,
                [
                    'button:has-text("Siguiente")',
                    'button:has-text("Ir al pago")',
                    'button:has-text("Continuar")',
                    'button:has-text("Continue")',
                ],
                force=True,
            )
            page.wait_for_timeout(700)
            _click_todos_selectores_visibles(
                page,
                [
                    'button:has-text("Proceder al pago")',
                    'button:has-text("Proceed to payment")',
                    'button:has-text("Ir al pago")',
                ],
                force=True,
            )

        page.wait_for_timeout(1200)

    raise RuntimeError(f"No se pudo avanzar de passenger-detail a checkout en {timeout_ms}ms. URL: {page.url}")


def _rellenar_fecha_nacimiento(page, fecha):
    dia, mes, anio = fecha.split("/")
    contenedor = _buscar_selector_visible(page, ['[data-test="is-passengerForm-textFieldBirthdate"]'])
    if not contenedor:
        raise RuntimeError("No se encontró el campo de fecha de nacimiento.")

    # Variante A: fecha como 3 selects (día/mes/año)
    selects = contenedor.locator('.ant-select-selector, [role="combobox"]')
    if selects.count() >= 3:
        valores = [str(int(dia)), str(int(mes)), anio]
        for indice, valor in enumerate(valores):
            campo_select = selects.nth(indice)
            try:
                if not campo_select.is_visible():
                    continue
                campo_select.click(force=True)
                page.wait_for_timeout(150)
                if not _click_texto_visible(page, valor, exacto=True):
                    if not _click_texto_visible(page, valor, exacto=False):
                        page.keyboard.type(valor)
                        page.keyboard.press("Enter")
                page.wait_for_timeout(120)
            except Exception:
                continue
        return

    # Variante B: fecha en inputs
    valores = [str(int(dia)), str(int(mes)), anio]
    inputs = contenedor.locator("input")
    llenados = 0

    for indice in range(inputs.count()):
        campo = inputs.nth(indice)
        try:
            if campo.is_visible():
                campo.fill(valores[llenados])
                llenados += 1
                if llenados == 3:
                    break
        except Exception:
            continue

    if llenados != 3:
        raise RuntimeError("No fue posible completar la fecha de nacimiento.")


def _abrir_tarjeta_pasajero(page, pasajero, indice):
    candidatos_texto = [
        f"Pasajero {indice}",
        f"{pasajero['nombre']} {pasajero['apellido']}",
        pasajero["nombre"],
    ]
    for texto in candidatos_texto:
        if _click_texto_visible(page, texto, exacto=False):
            page.wait_for_timeout(400)
            return


def _forzar_guardado_tarjetas_pasajero(page, pasajeros):
    for indice, pasajero in enumerate(pasajeros, start=1):
        _abrir_tarjeta_pasajero(page, pasajero, indice)
        page.wait_for_timeout(200)
        _click_selector_visible(
            page,
            ['[data-test="is-passengerForm-saveButton"]', 'button:has-text("Guardar datos")'],
            force=True,
        )
        page.wait_for_timeout(500)


def _completar_contacto_comprobante(page):
    seccion = _buscar_visible(page.get_by_text("Contacto para recibir el comprobante"))
    if not seccion:
        return True

    mensaje_error = "Indica quién será el contacto que recibirá el comprobante."
    nombre = _normalizar_texto(CFG["pasajero"].get("nombre", ""))
    apellido = _normalizar_texto(CFG["pasajero"].get("apellido", ""))
    nombre_completo = _normalizar_texto(f"{nombre} {apellido}")
    candidatos_nombre = [valor for valor in [nombre_completo, nombre] if valor]

    for _ in range(5):
        if not _buscar_visible(page.get_by_text(mensaje_error)):
            return True

        try:
            seccion.scroll_into_view_if_needed()
        except Exception:
            pass

        # Asegura la sección desplegada y luego abre el dropdown de comprobante.
        if not _buscar_selector_visible(page, ['[data-test="is-thirdStep-dropdownReservationName"] .textfield_input']):
            _click_selector_visible(
                page,
                ['h3:has-text("Contacto para recibir el comprobante")'],
                force=True,
            )
            page.wait_for_timeout(200)

        if not _click_selector_visible(
            page,
            ['[data-test="is-thirdStep-dropdownReservationName"] .textfield_input'],
            force=True,
        ):
            page.wait_for_timeout(250)
            continue

        page.wait_for_timeout(180)

        # Primer intento: navegación de teclado sobre el dropdown abierto.
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(220)

        # Segundo intento: click por texto visible (match exacto preferente).
        if _buscar_visible(page.get_by_text(mensaje_error)):
            for candidato in candidatos_nombre:
                if _click_ultimo_texto_visible(page.get_by_text(candidato, exact=True), force=True):
                    page.wait_for_timeout(200)
                    break

        _rellenar_input_visible(
            page,
            ['[data-test="is-reservationManagerForm-textFieldEmail"] input'],
            CFG["pasajero"]["email"],
        )
        _rellenar_input_visible(
            page,
            ['[data-test="is-reservationManagerForm-textFieldPhoneNumber"] input'],
            CFG["pasajero"]["telefono"],
        )
        _rellenar_input_visible(
            page,
            ['[data-test="is-reservationManagerForm-textFieldPrefixPhoneNumber"] input'],
            CFG["pasajero"]["prefijo_pais"],
        )

        # Fuerza blur/validación de los campos del bloque.
        _click_selector_visible(
            page,
            ['h3:has-text("Contacto para recibir el comprobante")'],
            force=True,
        )
        page.wait_for_timeout(250)

    return not _buscar_visible(page.get_by_text(mensaje_error))


def _avanzar_a_checkout(page, timeout_ms=60000):
    inicio = datetime.now()

    while (datetime.now() - inicio).total_seconds() * 1000 < timeout_ms:
        if "checkout" in (page.url or ""):
            return True

        _completar_contacto_comprobante(page)

        _click_selector_visible(
            page,
            ['button:has-text("Siguiente")', 'button:has-text("Ir al pago")'],
            force=True,
        )
        page.wait_for_timeout(400)

        _click_selector_visible(
            page,
            [
                'button:has-text("Proceder al pago")',
                'button:has-text("Proceed to payment")',
                'button:has-text("Ir al pago")',
            ],
            force=True,
        )

        page.wait_for_timeout(1200)

    _guardar_html_debug(page, "bloqueo_checkout")
    return False


def _rellenar_pasajero(page, pasajero, indice, total):
    print(f"--- Pasajero {indice}/{total} ({pasajero.get('tipo_pasajero', 'ADT')}) ---")
    _abrir_tarjeta_pasajero(page, pasajero, indice)
    page.wait_for_timeout(800)

    _rellenar_input_visible(
        page,
        ['[data-test="is-passengerForm-textFieldNamePax"] input', '[data-test="is-passengerForm-textFieldName"] input'],
        pasajero["nombre"],
        requerido=True,
    )
    _rellenar_input_visible(
        page,
        ['[data-test="is-passengerForm-textFieldLastname"] input'],
        pasajero["apellido"],
        requerido=True,
    )
    _rellenar_fecha_nacimiento(page, pasajero["fecha_nac"])

    if _click_selector_visible(page, ['[data-test="is-thirdStep-dropdownGender"]']):
        if not _seleccionar_opcion_dropdown(page, pasajero["genero"]):
            print(f"⚠️ No se pudo seleccionar género '{pasajero['genero']}'.")

    if _click_selector_visible(page, ['[data-test="is-thirdStep-dropdownCountryIssue"]']):
        if not _seleccionar_opcion_dropdown(page, pasajero["pais_emision"]):
            print(f"⚠️ No se pudo seleccionar país de emisión '{pasajero['pais_emision']}'.")

    if _click_selector_visible(page, ['[data-test="is-thirdStep-dropdownDocumentType"]']):
        if not _seleccionar_opcion_dropdown(page, pasajero["doc_tipo"]):
            print(f"⚠️ No se pudo seleccionar tipo de documento '{pasajero['doc_tipo']}'.")

    _rellenar_input_visible(
        page,
        ['[data-test="is-passengerForm-textFieldDocumentNumber"] input', '.card-passenger__passenger-form--fourth-row input'],
        pasajero["doc_numero"],
        requerido=True,
    )

    # Email/teléfono suelen existir para adultos; en CHD/INF pueden no estar visibles.
    _rellenar_input_visible(page, ['[data-test="is-passengerForm-textFieldEmail"] input'], pasajero["email"])
    _rellenar_input_visible(page, ['[data-test="is-passengerForm-textFieldPrefix"] input'], pasajero["prefijo_pais"])
    _rellenar_input_visible(page, ['[data-test="is-passengerForm-textFieldPhone"] input'], pasajero["telefono"])

    guardado = _click_selector_visible(
        page,
        ['[data-test="is-passengerForm-saveButton"]', 'button:has-text("Guardar datos")'],
        force=True,
    )
    if not guardado:
        raise RuntimeError(f"No se pudo guardar los datos del pasajero {indice}.")

    page.wait_for_timeout(900)


def _rellenar_todos_los_pasajeros(page):
    pasajeros = CFG["pasajeros_lista"]
    print(f"--- Llenando Datos Pasajero ({len(pasajeros)} en total) ---")
    _esperar_o_avanzar_hasta_pasajeros(page)
    if "checkout" in (page.url or ""):
        print("⚠️ Flujo ya está en checkout. Se omite carga de pasajeros.")
        return

    expect(page).to_have_url(re.compile(".*passenger-detail"), timeout=20000)
    page.wait_for_timeout(1500)

    for indice, pasajero in enumerate(pasajeros, start=1):
        _rellenar_pasajero(page, pasajero, indice, len(pasajeros))

    _forzar_guardado_tarjetas_pasajero(page, pasajeros)
    print("--- Avanzando a checkout desde pasajeros ---")
    _click_selector_visible(page, ['button:has-text("Siguiente")', 'button:has-text("Ir al pago")'], force=True)


def _obtener_contexto_cdp(browser, timeout_segundos=8):
    deadline = time.time() + timeout_segundos
    while time.time() < deadline:
        if browser.contexts:
            return browser.contexts[-1]
        time.sleep(0.2)

    try:
        return browser.new_context()
    except Exception as error:
        raise RuntimeError(
            "CDP conectado, pero no hay contexto de navegador listo todavía. "
            "Reintenta en unos segundos."
        ) from error


def _obtener_pagina_existente(context, timeout_segundos=3):
    deadline = time.time() + timeout_segundos
    while time.time() < deadline:
        if context.pages:
            pagina = context.pages[0]
            try:
                if not pagina.is_closed():
                    return pagina
            except Exception:
                pass
        time.sleep(0.2)
    return None


def _crear_sesion_navegador(playwright):
    if CFG.get("usar_chrome_existente"):
        cdp_url = CFG.get("cdp_url") or "http://127.0.0.1:9222"
        print(f"🔌 Conectando a Chrome existente por CDP: {cdp_url}")
        try:
            browser = playwright.chromium.connect_over_cdp(cdp_url)
        except Exception as error:
            raise RuntimeError(
                f"No se pudo conectar a Chrome por CDP en {cdp_url}. "
                "Inicia Chrome con --remote-debugging-port=9222 e inténtalo de nuevo."
            ) from error
        context = _obtener_contexto_cdp(browser)
        if CFG.get("cdp_reutilizar_primera_pestana"):
            page = _obtener_pagina_existente(context)
            if page and _es_pagina_reutilizable(page):
                try:
                    page.bring_to_front()
                except Exception:
                    pass
                print("🧭 CDP conectado: usando la primera pestaña disponible.")
            else:
                page = context.new_page()
                print("🧭 CDP conectado: pestaña inicial no reusable; se abrió una nueva.")
        else:
            page = context.new_page()
            print("🧭 CDP conectado: se abrió una pestaña nueva para esta ejecución.")
        return browser, context, page, True

    browser = playwright.chromium.launch(headless=CFG["headless"], slow_mo=CFG["slow_mo"])
    context = browser.new_context()
    page = context.new_page()
    return browser, context, page, False


def run(playwright: Playwright) -> None:
    browser = None
    context = None
    session_cdp = False

    try:
        browser, context, page, session_cdp = _crear_sesion_navegador(playwright)
        try:
            print(f"--- 🚀 Iniciando Test [{CFG['market']}]: {CFG['origen']} -> {CFG['destino']} ---")
            print(f"    Medio de pago: {CFG['medio_pago']}")
            print(f"    Tipo viaje: {CFG['tipo_viaje']} | Pax: {CFG['pasajeros']}")
            if CFG["modo_exploracion"]:
                print(f"    Modo exploración: ON | Evidencia en {EXPLORACION_DIR}")
            page.goto(CFG["url"])
            _cerrar_panel_login_si_abierto(page)
            _capturar_estado_ui(page, "landing")
            _esperar_home_lista(page)
            _cerrar_panel_login_si_abierto(page)
            _capturar_estado_ui(page, "landing_ready")

            # -------------------------------------------
            # 1. BÚSQUEDA DE VUELO
            # -------------------------------------------
            _seleccionar_tipo_viaje(page)
            _capturar_estado_ui(page, "tipo_viaje")

            # Origen
            _seleccionar_ciudad(page, "#origin-id", CFG["origen"])

            # Destino
            _seleccionar_ciudad(page, "#destination-id", CFG["destino"])

            _seleccionar_fechas(page)
            _configurar_pasajeros_busqueda(page)
            _capturar_estado_ui(page, "busqueda_configurada")

            _cerrar_panel_login_si_abierto(page)
            if not _click_selector_visible(
                page,
                ['button:has-text("Buscar vuelo")', 'button:has-text("Buscar voo")', 'button:has-text("Search")'],
                force=True,
                requerido=True,
                descripcion="botón Buscar vuelo",
            ):
                raise RuntimeError("No se pudo iniciar la búsqueda de vuelos.")
            page.wait_for_timeout(1500)
            _cerrar_panel_login_si_abierto(page)
            _capturar_estado_ui(page, "post_busqueda")

            if CFG["solo_exploracion"]:
                print("🧪 Solo exploración activo: flujo detenido tras búsqueda.")
                return

            # 🛑 Checkpoint: Después de búsqueda
            if pausar_en_checkpoint(page, "BUSQUEDA"):
                return

            # -------------------------------------------
            # 2. SELECCIÓN DE TARIFA
            # -------------------------------------------
            _seleccionar_vuelo_y_tarifa(page, "IDA")
            if CFG["tipo_viaje"] == "ROUND_TRIP":
                _seleccionar_vuelo_y_tarifa(page, "VUELTA")
                _capturar_estado_ui(page, "vuelo_vuelta_seleccionado")
            else:
                _capturar_estado_ui(page, "vuelo_ida_seleccionado")
            _saltar_extras(page)
            _capturar_estado_ui(page, "extras_saltados")

            # 🛑 Checkpoint: Después de selección de tarifa
            if pausar_en_checkpoint(page, "SELECCION_TARIFA"):
                return

            # -------------------------------------------
            # 3. DATOS DEL PASAJERO
            # -------------------------------------------
            _rellenar_todos_los_pasajeros(page)
            _capturar_estado_ui(page, "pasajeros_completados")

            # 🛑 Checkpoint: Después de datos del pasajero
            if pausar_en_checkpoint(page, "DATOS_PASAJERO"):
                return

            if not _avanzar_a_checkout(page, timeout_ms=90000):
                _capturar_estado_ui(page, "post_confirmacion")
                print("⚠️ No se pudo avanzar automáticamente a checkout.")
                print("🖱️ Activando modo manual - continúa tú desde aquí")
                _activar_modo_manual(page)
                return

            _capturar_estado_ui(page, "post_confirmacion")

            # -------------------------------------------
            # 4. CHECKOUT Y PAGO
            # -------------------------------------------
            print("--- Llegada al Checkout ---")
            _capturar_estado_ui(page, "checkout")

            try:
                expect(page).to_have_url(re.compile(".*checkout"), timeout=30000)
            except Exception as error:
                print(f"⚠️ No se pudo llegar al checkout en 30s: {error}")
                print("🖱️ Activando modo manual - continúa tú desde aquí")
                _activar_modo_manual(page)
                return

            # 🛑 Checkpoint: En el checkout
            if pausar_en_checkpoint(page, "CHECKOUT"):
                return

            medio = CFG["medio_pago"]
            market = CFG["market"]
            print(f"--- Iniciando Pago: {medio} ({market}) ---")

            try:
                if market == "PE":
                    _pagar_niubiz(page)
                elif market == "CL":
                    _pagar_webpay(page)
                elif market == "AR":
                    _pagar_mercadopago(page)
                elif market == "BR":
                    _pagar_cielo(page)
                else:
                    print(f"❌ Market '{market}' no tiene flujo de pago implementado.")
            except Exception as error:
                print(f"❌ Error en flujo de pago: {error}")
                screenshots_dir = "screenshots_pruebas"
                os.makedirs(screenshots_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                error_path = os.path.join(screenshots_dir, f"error_pago_{timestamp}.png")
                page.screenshot(path=error_path)
                print(f"📸 Screenshot de error guardado en: {error_path}")
                print("🖱️ Activando modo manual - continúa tú desde aquí")
                _activar_modo_manual(page)
                return

            # -------------------------------------------
            # 5. SCREENSHOT FINAL Y CIERRE
            # -------------------------------------------
            espera_final_segundos = CFG.get("espera_final_segundos", 600)
            if espera_final_segundos > 0:
                minutos, segundos = divmod(espera_final_segundos, 60)
                if segundos:
                    espera_legible = f"{minutos}m {segundos}s"
                else:
                    espera_legible = f"{minutos} minutos"
                print(f"⏳ Esperando {espera_legible} antes de tomar screenshot final...")
                print("   (Puedes cerrar el navegador manualmente si deseas salir antes)")
                page.wait_for_timeout(espera_final_segundos * 1000)
            else:
                print("⏩ Espera final deshabilitada (0 segundos).")

            screenshots_dir = "screenshots_pruebas"
            os.makedirs(screenshots_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(screenshots_dir, f"pago_exitoso_{timestamp}.png")

            print(f"📸 Tomando screenshot final: {screenshot_path}")
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"✅ Screenshot guardado exitosamente en: {screenshot_path}")
            print("✅ Fin del script.")
        except TargetClosedError:
            print("\n👋 Navegador cerrado manualmente por el usuario.")
            print("✅ Prueba finalizada correctamente.")

    finally:
        if session_cdp:
            print("🧹 Modo CDP activo: se mantiene abierto el Chrome existente.")
        else:
            print("🧹 Cerrando navegador y contexto...")
            if context:
                try:
                    context.close()
                except Exception as error:
                    print(f"⚠️ Error cerrando contexto: {error}")
            if browser:
                try:
                    browser.close()
                except Exception as error:
                    print(f"⚠️ Error cerrando navegador: {error}")


# ==========================================
# 💳 FLUJOS DE PAGO POR MARKET
# ==========================================

def _pagar_niubiz(page):
    """Perú — Niubiz"""
    try:
        page.wait_for_selector('text="Niubiz"', timeout=45000)
    except Exception as e:
        print(f"⚠️ Niubiz no apareció en 45s: {e}")
        print("🖱️ Activando modo manual - continúa tú desde aquí")
        _activar_modo_manual(page)
        return
    niubiz_btn = page.locator("div").filter(has_text="Niubiz").last
    niubiz_btn.scroll_into_view_if_needed()
    niubiz_btn.click(force=True)

    print("Esperando animación del formulario...")
    page.wait_for_timeout(5000)

    # Pre-llenado datos contacto
    try:
        page.locator("div").filter(has_text=re.compile(r"^Nombre$")).last.locator("input.input").fill(CFG["pasajero"]["nombre"])
        page.locator("div").filter(has_text=re.compile(r"^Apellido$")).last.locator("input.input").fill(CFG["pasajero"]["apellido"])
        page.locator("div").filter(has_text="Correo electrónico").last.locator("input.input").fill(CFG["pasajero"]["email"])
    except: pass

    input_tarjeta = _buscar_campo_tarjeta(page)
    if not input_tarjeta:
        print("❌ Error: Nunca apareció el campo 'Número de Tarjeta'.")
        return

    print("✅ Campo tarjeta detectado. Validando habilitación...")
    try:
        input_tarjeta.wait_for(state="visible", timeout=30000)
        expect(input_tarjeta).to_be_editable(timeout=30000)

        print(f"⏳ Pausa de seguridad ({CFG['pausa']}ms)...")
        page.wait_for_timeout(CFG["pausa"])

        input_tarjeta.click(force=True)
        input_tarjeta.fill(CFG["tarjeta"]["numero"])

        print("🎹 Tabs: Tarjeta -> Nombre -> Apellido -> Fecha")
        page.keyboard.press("Tab")  # Nombre
        page.keyboard.press("Tab")  # Apellido
        page.keyboard.press("Tab")  # Fecha

        fecha_limpia = CFG["tarjeta"]["fecha"].replace("/", "")
        print(f"⌨️ Fecha: {fecha_limpia}")
        page.keyboard.type(fecha_limpia, delay=100)

        print("🎹 Tab a CVV...")
        page.keyboard.press("Tab")
        print(f"⌨️ CVV: {CFG['tarjeta']['cvv']}")
        page.keyboard.type(CFG["tarjeta"]["cvv"], delay=100)

        if pausar_en_checkpoint(page, "PAGO"):
            return

        _finalizar_compra(page)
    except Exception as e:
        print(f"❌ Error Niubiz: {e}")
        page.screenshot(path="error_niubiz.png")


def _pagar_webpay(page):
    """Chile — Webpay (Transbank)
    Flujo: SKY checkout → portal Transbank → Tarjetas → datos → RUT/clave → Aceptar
    """

    # ── Paso 1: Seleccionar Webpay en el checkout de SKY ──
    page.wait_for_selector('text="Webpay"', timeout=45000)
    webpay_btn = page.locator("div").filter(has_text="Webpay").last
    webpay_btn.scroll_into_view_if_needed()
    webpay_btn.click(force=True)

    if pausar_en_checkpoint(page, "PAGO"):
        return

    # T&C + "Ir a pagar" en SKY (redirige a Transbank)
    _finalizar_compra(page)

    # ── Paso 2: Portal Transbank — Seleccionar "Tarjetas" ──
    print("🌐 Esperando portal Transbank...")
    page.wait_for_url(re.compile(r"transbank\.cl"), timeout=30000)
    page.wait_for_timeout(2000)

    print("🃏 Seleccionando 'Tarjetas'...")
    page.locator("button#tarjetas").click()
    page.wait_for_timeout(2000)

    # ── Paso 3: Llenar datos de tarjeta ──
    print("💳 Llenando datos de tarjeta...")
    # Número de tarjeta (input#card-number, tabindex=1)
    card_number = page.locator("input#card-number")
    card_number.wait_for(state="visible", timeout=15000)
    card_number.click()
    card_number.fill(CFG["tarjeta"]["numero"])
    
    # no existe un h1, hay que cliquear afuera del input 
    page.locator("body").click()
    page.wait_for_timeout(1000)

    # Fecha de expiración MM/AA (input#card-exp, tabindex=2)
    card_exp = page.locator("input#card-exp")
    card_exp.click()
    fecha = CFG["tarjeta"]["fecha"].replace("/", "")  # viene como "12/30" → MM/YY pero el input no acepta el slash, así que lo limpiamos a "1230"
    card_exp.type(fecha, delay=80)

    # CVV (input#card-cvv, tabindex=3)
    card_cvv = page.locator("input#card-cvv")
    card_cvv.click()
    card_cvv.type(CFG["tarjeta"]["cvv"], delay=80)

    # Cuotas: "Sin Cuotas" ya está seleccionado por defecto (botón disabled)
    # No se necesita interacción.

    # Botón "Pagar" (button.submit — filtrar el de texto "Pagar" para evitar el modal OneClick)
    print("🚀 Click en 'Pagar'...")
    btn_pagar_tbk = page.get_by_role("button", name="Pagar", exact=True)
    btn_pagar_tbk.wait_for(state="visible", timeout=10000)
    # Esperar a que se habilite (se quita el disabled tras llenar los campos)
    page.wait_for_timeout(1000)
    btn_pagar_tbk.click()

    # ── Paso 4: Autenticación — RUT y Clave ──
    print("🔐 Esperando página de autenticación...")
    page.wait_for_url(re.compile(r"authenticator"), timeout=30000)
    page.wait_for_timeout(1000)

    rut = CFG["tarjeta"].get("rut", "11.111.111-1")
    clave = CFG["tarjeta"].get("clave", "123")

    print(f"📝 RUT: {rut}")
    page.locator("input#rutClient").fill(rut)
    page.locator("input#passwordClient").fill(clave)

    # Click "Aceptar"
    page.locator('input[type="submit"][value="Aceptar"]').click()

    # ── Paso 5: Confirmación — "Elija una opcion" → Aceptar → Continuar ──
    print("✅ Esperando pantalla de confirmación...")
    page.wait_for_timeout(3000)

    # Select "Aceptar" (value="TSY") — ya viene seleccionado por defecto
    page.locator("select#vci").select_option("TSY")

    # Click "Continuar"
    page.locator('input[type="submit"][value="Continuar"]').click()

    print("🎉 ¡Webpay completado! Esperando redirección a SKY...")


def _pagar_mercadopago(page):
    """Argentina — Mercado Pago
    Campos en iframe (secure-fields.mercadopago.com): cardNumber, expirationDate, securityCode
    Campos regulares: cardholderName, docType, docNumber, email, installments
    """

    # ── Paso 1: Seleccionar Mercado Pago en el checkout de SKY ──
    mp_container = page.locator('[data-test="IS-paymentMethodList-cardFop-mercado-pago"]')
    mp_container.wait_for(state="visible", timeout=45000)
    mp_container.locator('[data-test="IS-cardFop-radioButton"]').click()

    print("Esperando formulario Mercado Pago...")
    page.wait_for_timeout(5000)

    # Pre-llenado datos contacto en SKY
    try:
        page.locator("div").filter(has_text=re.compile(r"^Nombre$")).last.locator("input.input").fill(CFG["pasajero"]["nombre"])
        page.locator("div").filter(has_text=re.compile(r"^Apellido$")).last.locator("input.input").fill(CFG["pasajero"]["apellido"])
        page.locator("div").filter(has_text="Correo electrónico").last.locator("input.input").fill(CFG["pasajero"]["email"])
    except Exception as e:
        print(f"⚠️ Pre-fill contact data MP: {e}")
        pass

    # ── Paso 2: Llenar formulario Mercado Pago ──
    print("💳 Llenando formulario Mercado Pago...")

    try:
        # --- Número de tarjeta (iframe name="cardNumber") ---
        print("🔢 Tarjeta (iframe)...")
        card_iframe = _buscar_iframe_mp(page, "cardNumber")
        if card_iframe:
            card_input = _input_visible_iframe(card_iframe)
            card_input.wait_for(state="visible", timeout=15000)
            card_input.click()
            card_input.type(CFG["tarjeta"]["numero"], delay=50)
        else:
            print("❌ No se encontró iframe de cardNumber")
            return

        page.wait_for_timeout(1000)

        # --- Nombre del titular ---
        print("👤 Titular...")
        titular = CFG["tarjeta"].get("titular", "APRO")
        holder_input = page.locator('[data-test="IS-mercadoPagoForm-inputCardHolderName"] input.input')
        holder_input.click()
        holder_input.fill(titular)

        page.wait_for_timeout(500)

        # --- Fecha de expiración (iframe name="expirationDate") ---
        #Page locator IS-mercadoPagoForm-inputExpirationDate
        print("📅 Fecha expiración (iframe)...")
        exp_iframe = _buscar_iframe_mp(page, "expirationDate")
        if exp_iframe:
            exp_input = _input_visible_iframe(exp_iframe)
            exp_input.wait_for(state="visible", timeout=15000)
            exp_input.click()
            exp_input.type(CFG["tarjeta"]["fecha"], delay=50)  # MM/YY
        else:
            print("❌ No se encontró iframe de expirationDate")
            return

        page.wait_for_timeout(500)
        

        # --- CVV / Código de seguridad (iframe name="securityCode") ---
        print("🔒 CVV (iframe)...")
        cvv_iframe = _buscar_iframe_mp(page, "securityCode")
        if cvv_iframe:
            cvv_input = _input_visible_iframe(cvv_iframe)
            cvv_input.wait_for(state="visible", timeout=15000)
            cvv_input.click()
            cvv_input.type(CFG["tarjeta"]["cvv"], delay=50)
        else:
            print("❌ No se encontró iframe de securityCode")
        page.wait_for_timeout(1000)

        # --- Cuotas (dropdown custom) → seleccionar "1 cuota" ---
        print("💰 Seleccionando cuotas...")
        cuotas_container = page.locator('[data-test="IS-mercadoPagoForm-selectInstallment"]')
        cuotas_container.locator(".textfield_input").click()
        page.wait_for_timeout(1000)
        # Buscar la opción "1 cuota" en el desplegable
        page.get_by_text(re.compile(r"1 cuota", re.IGNORECASE)).first.click()
        page.wait_for_timeout(500)

        # --- Tipo de documento (dropdown custom) → "DNI" ---
        print("📄 Tipo de documento...")
        doc_tipo = CFG["tarjeta"].get("doc_tipo", "DNI")
        doc_type_container = page.locator('[data-test="IS-mercadoPagoForm-selectDocType"]')
        doc_type_container.locator(".textfield_input").click()
        page.wait_for_timeout(500)
        page.get_by_text(doc_tipo, exact=True).first.click()
        page.wait_for_timeout(500)

        # --- Número de documento ---
        print("🆔 Número de documento...")
        doc_numero = CFG["tarjeta"].get("doc_numero", "")
        doc_input = page.locator('[data-test="IS-mercadoPagoForm-inputDocNumber"] input.input')
        doc_input.click()
        doc_input.fill(doc_numero)

        # --- Email ---
        print("📧 Email...")
        email_mp = CFG["tarjeta"].get("email", CFG["pasajero"]["email"])
        email_input = page.locator('[data-test="IS-mercadoPagoForm-inputEmail"] input.input')
        email_input.click()
        email_input.fill(email_mp)

        if pausar_en_checkpoint(page, "PAGO"):
            return

        # ── Paso 3: T&C + Pagar ──
        _finalizar_compra(page, boton_texto="Pagar")

    except Exception as e:
        print(f"❌ Error Mercado Pago: {e}")
        page.screenshot(path="error_mercadopago.png")


def _pagar_cielo(page):
    # TODO pendiente revision
    """Brasil — Cielo"""
    page.wait_for_selector('text="Cielo"', timeout=45000)
    cielo_btn = page.locator("div").filter(has_text="Cielo").last
    cielo_btn.scroll_into_view_if_needed()
    cielo_btn.click(force=True)

    print("Esperando formulario Cielo...")
    page.wait_for_timeout(5000)

    # Pre-llenado datos contacto
    try:
        page.locator("div").filter(has_text=re.compile(r"^Nombre$")).last.locator("input.input").fill(CFG["pasajero"]["nombre"])
        page.locator("div").filter(has_text=re.compile(r"^Apellido$")).last.locator("input.input").fill(CFG["pasajero"]["apellido"])
        page.locator("div").filter(has_text="Correo electrónico").last.locator("input.input").fill(CFG["pasajero"]["email"])
    except Exception as e:
        print(f"⚠️ Pre-fill contact data Cielo: {e}")
        pass

    input_tarjeta = _buscar_campo_tarjeta(page)
    if not input_tarjeta:
        print("❌ Error: Nunca apareció el campo tarjeta para Cielo.")
        return

    try:
        input_tarjeta.wait_for(state="visible", timeout=30000)
        expect(input_tarjeta).to_be_editable(timeout=30000)
        page.wait_for_timeout(CFG["pausa"])

        input_tarjeta.click(force=True)
        input_tarjeta.fill(CFG["tarjeta"]["numero"])

        # CVV
        page.keyboard.press("Tab")
        page.keyboard.type(CFG["tarjeta"]["cvv"], delay=100)

        # Fecha
        fecha_limpia = CFG["tarjeta"]["fecha"].replace("/", "")
        page.keyboard.press("Tab")
        page.keyboard.type(fecha_limpia, delay=100)

        # Seleccionar Débito si aplica
        tipo = CFG["tarjeta"].get("tipo", "")
        if tipo:
            try:
                page.get_by_text(tipo, exact=False).first.click()
            except: pass

        if pausar_en_checkpoint(page, "PAGO"):
            return

        _finalizar_compra(page, boton_texto="Pagar")

        # Código de autenticación (3DS)
        codigo = CFG["tarjeta"].get("codigo_auth", "")
        if codigo:
            print(f"🔑 Enviando código de autenticación: {codigo}")
            try:
                page.wait_for_timeout(3000)
                page.locator('input[name*="code"], input[placeholder*="ódigo"], input[type="password"]').first.fill(codigo)
                page.locator('button[type="submit"], input[type="submit"]').first.click()
                print("🎉 Código enviado!")
            except Exception as e:
                print(f"⚠️ Error en código auth Cielo: {e}")

    except Exception as e:
        print(f"❌ Error Cielo: {e}")
        page.screenshot(path="error_cielo.png")


# ==========================================
# 🔧 HELPERS DE PAGO
# ==========================================

def _buscar_iframe_mp(page, iframe_name):
    """Busca un iframe de Mercado Pago secure-fields por su atributo name."""
    print(f"   🔍 Buscando iframe '{iframe_name}'...")
    for attempt in range(15):
        for frame in page.frames:
            if frame.name == iframe_name:
                return frame
        if attempt % 5 == 0:
            print(f"   ... intento {attempt + 1} ...")
        page.wait_for_timeout(1000)
    return None


def _input_visible_iframe(frame):
    """Devuelve el input visible dentro de un iframe de MercadoPago secure-fields.
    Los iframes contienen un <input class='hide'> oculto y otro visible; filtramos el oculto."""
    return frame.locator("input:not(.hide)")


def _buscar_campo_tarjeta(page):
    """Busca el input 'Número de Tarjeta' en todos los frames (iframes de pasarelas)."""
    print("🕵️ Buscando campo Tarjeta...")
    input_tarjeta = None
    for i in range(20):
        for frame in page.frames:
            try:
                candidato = frame.get_by_placeholder(re.compile(r"Número de Tarjeta|Card Number|Número do Cartão", re.IGNORECASE))
                if candidato.count() > 0 and candidato.is_visible():
                    input_tarjeta = candidato
                    break
            except: continue
        if input_tarjeta:
            break
        if i % 5 == 0:
            print("   ... Buscando ...")
        page.wait_for_timeout(2000)
    return input_tarjeta

def _finalizar_compra(page, boton_texto="Ir a pagar"):
    """Checkbox T&C + botón de pago."""
    print("--- Finalizando Compra ---")

    # Checkbox "He leído y acepto"
    print("✅ Buscando checkbox...")
    checkbox_exacto = page.locator(".checkbox_icon").last
    checkbox_exacto.scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    checkbox_exacto.click()
    
    # Botón de pago
    print(f"🚀 Buscando botón '{boton_texto}'...")
    btn_pagar = page.locator("button").filter(has_text=boton_texto)
    btn_pagar.wait_for(state="visible", timeout=5000)
    btn_pagar.click()
    print("🎉 ¡CLICK EN PAGAR REALIZADO!")

try:
    with sync_playwright() as playwright:
        run(playwright)
except KeyboardInterrupt:
    print("\n\n👋 Ejecución interrumpida por el usuario (Ctrl+C). ¡Hasta la próxima!")
except Exception as error:
    print(f"\n❌ Error de ejecución: {error}")
