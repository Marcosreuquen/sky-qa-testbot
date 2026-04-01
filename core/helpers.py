"""
Helpers genéricos de interacción con Playwright.
Incluye: utilidades de locator, checkpoint, modo manual y exploración de UI.
Sin dependencias de flujo de negocio — importar desde cualquier módulo.
"""

import os
import re
import shutil
import time
from datetime import datetime

import core.state as state


_ETAPAS_ORDEN = {
    "BUSQUEDA": 1,
    "SELECCION_TARIFA": 2,
    "DATOS_PASAJERO": 3,
    "CHECKOUT": 4,
    "PAGO": 5,
    "DESCONOCIDA": 0,
}


def detectar_etapa_actual(page):
    url = (page.url or "").lower()

    if "checkout" in url:
        return "CHECKOUT"
    if "passenger-detail" in url:
        return "DATOS_PASAJERO"
    if "/seats" in url or "/additional-services" in url:
        return "SELECCION_TARIFA"

    if _buscar_selector_visible(
        page,
        [
            'button:has-text("Elegir vuelo")',
            '[data-test^="is-itinerary-selectFlight"]',
            '[data-test^="is-itinerary-selectRate"]',
        ],
    ):
        return "SELECCION_TARIFA"

    if _buscar_selector_visible(
        page,
        [
            "#origin-id",
            "#destination-id",
            'button:has-text("Buscar vuelo")',
            'button:has-text("Buscar vuelos")',
            'button:has-text("Buscar")',
            'button:has-text("Buscar voo")',
            'button:has-text("Search")',
            'button[type="submit"]',
            '[data-test*="search"]',
        ],
    ):
        return "BUSQUEDA"

    return "DESCONOCIDA"


def etapa_en_o_despues(etapa_actual, etapa_referencia):
    return _ETAPAS_ORDEN.get(etapa_actual, 0) >= _ETAPAS_ORDEN.get(etapa_referencia, 0)


def _control_path(nombre):
    control_dir = state.CFG.get("control_dir")
    if not control_dir:
        return None
    return os.path.join(control_dir, nombre)


def _write_control_file(nombre, contenido=""):
    path = _control_path(nombre)
    if not path:
        return None
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    return path


def _remove_control_file(nombre):
    path = _control_path(nombre)
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        return


def gestionar_pausa_edicion(page, contexto=""):
    pause_request = _control_path("pause.request")
    if not pause_request or not os.path.exists(pause_request):
        return detectar_etapa_actual(page)

    etapa_actual = detectar_etapa_actual(page)
    _remove_control_file("pause.request")
    _remove_control_file("continue.request")
    _write_control_file(
        "paused.state",
        f"stage={etapa_actual}\nurl={page.url}\ncontext={contexto}\ntimestamp={datetime.now().isoformat()}\n",
    )
    print(f"⏸️ Pausa para edición activada ({contexto or 'sin contexto'}).")
    print(f"🖱️ Etapa actual detectada: {etapa_actual}")
    print("▶️ Esperando 'Continuar' desde la GUI...")

    while True:
        continue_request = _control_path("continue.request")
        if continue_request and os.path.exists(continue_request):
            _remove_control_file("continue.request")
            _remove_control_file("paused.state")
            etapa_reanudada = detectar_etapa_actual(page)
            print(f"▶️ Continuando ejecución desde etapa detectada: {etapa_reanudada}")
            return etapa_reanudada
        page.wait_for_timeout(250)


def esperar_correccion_runtime(page, motivo=""):
    etapa_actual = detectar_etapa_actual(page)
    print(f"🛠️ Corrección en runtime activada ({motivo or 'sin motivo'}).")
    print(f"🖱️ Etapa actual detectada: {etapa_actual}")

    if state.CFG.get("control_dir"):
        _remove_control_file("continue.request")
        _write_control_file(
            "paused.state",
            f"stage={etapa_actual}\nurl={page.url}\ncontext=recovery:{motivo}\ntimestamp={datetime.now().isoformat()}\n",
        )
        print("▶️ Corrige lo necesario en el navegador y presiona 'Continuar' en la GUI.")
        while True:
            continue_request = _control_path("continue.request")
            if continue_request and os.path.exists(continue_request):
                _remove_control_file("continue.request")
                _remove_control_file("paused.state")
                etapa_reanudada = detectar_etapa_actual(page)
                print(f"▶️ Reintentando desde etapa detectada: {etapa_reanudada}")
                return etapa_reanudada
            page.wait_for_timeout(250)

    if state.CFG.get("headless"):
        print("ℹ️ Headless activo: no se puede corregir manualmente en runtime.")
        return etapa_actual

    print("▶️ Corrige lo necesario en el navegador y presiona 'Resume' en el inspector.")
    page.pause()
    etapa_reanudada = detectar_etapa_actual(page)
    print(f"▶️ Reintentando desde etapa detectada: {etapa_reanudada}")
    return etapa_reanudada


# ==========================================
# CHECKPOINT Y MODO MANUAL
# ==========================================

def pausar_en_checkpoint(page, checkpoint_actual):
    """Pausa el bot si se alcanza el checkpoint configurado."""
    if state.CFG["checkpoint"] == checkpoint_actual:
        print(f"\n⏸️  CHECKPOINT ALCANZADO: {checkpoint_actual}")
        print("🖱️  Puedes interactuar manualmente con la página.")
        print("▶️  Presiona 'Resume' en el inspector para continuar o cerrar.\n")
        if state.CFG.get("headless"):
            print("ℹ️  Headless activo: se omite page.pause() y se detiene la ejecución en el checkpoint.")
            return True
        page.pause()
        etapa_detectada = detectar_etapa_actual(page)
        print(f"▶️ Reanudando ejecución desde etapa detectada: {etapa_detectada}")
        return False
    return False


def _activar_modo_manual(page):
    if state.CFG.get("headless"):
        print("ℹ️ Modo headless: se omite page.pause().")
        return detectar_etapa_actual(page)
    page.pause()
    etapa_detectada = detectar_etapa_actual(page)
    print(f"▶️ Reanudando desde modo manual en etapa detectada: {etapa_detectada}")
    return etapa_detectada


# ==========================================
# EXPLORACIÓN DE UI
# ==========================================

def _capturar_estado_ui(page, etapa):
    if not state.CFG.get("modo_exploracion"):
        return

    os.makedirs(state.EXPLORACION_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefijo = os.path.join(state.EXPLORACION_DIR, f"{timestamp}_{etapa}")

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
    base_dir = state.EXPLORACION_DIR if state.CFG.get("modo_exploracion") else "screenshots_pruebas"
    os.makedirs(base_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = os.path.join(base_dir, f"{timestamp}_{etapa}.html")
    try:
        with open(html_path, "w", encoding="utf-8") as archivo:
            archivo.write(page.content())
        print(f"🧾 HTML debug [{etapa}] -> {html_path}")
    except Exception as error:
        print(f"⚠️ No se pudo guardar HTML debug [{etapa}]: {error}")


def _tamano_ruta_bytes(path):
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

    total = 0
    for root, _, files in os.walk(path):
        for nombre in files:
            archivo = os.path.join(root, nombre)
            try:
                total += os.path.getsize(archivo)
            except OSError:
                continue
    return total


def _formatear_bytes(cantidad):
    if cantidad < 1024:
        return f"{cantidad} B"

    unidades = ["KB", "MB", "GB", "TB"]
    valor = float(cantidad)
    for unidad in unidades:
        valor /= 1024.0
        if valor < 1024 or unidad == unidades[-1]:
            return f"{valor:.1f} {unidad}"
    return f"{cantidad} B"


def limpiar_evidencias_antiguas(base_dir="screenshots_pruebas", semanas_retencion=2, habilitado=True):
    if not habilitado or semanas_retencion <= 0:
        return

    if not os.path.isdir(base_dir):
        return

    limite = time.time() - (semanas_retencion * 7 * 24 * 60 * 60)
    eliminados = 0
    recuperado_bytes = 0
    errores = 0

    for entrada in os.scandir(base_dir):
        try:
            if entrada.stat().st_mtime >= limite:
                continue

            recuperado_bytes += _tamano_ruta_bytes(entrada.path)
            if entrada.is_dir(follow_symlinks=False):
                shutil.rmtree(entrada.path)
            else:
                os.remove(entrada.path)
            eliminados += 1
        except Exception as error:
            errores += 1
            print(f"⚠️ No se pudo limpiar evidencia antigua '{entrada.path}': {error}")

    if eliminados:
        print(
            "🧹 Limpieza de evidencias: "
            f"{eliminados} entradas eliminadas (> {semanas_retencion} semanas, {_formatear_bytes(recuperado_bytes)}).",
        )
    elif errores:
        print("⚠️ Limpieza de evidencias finalizó con errores y sin elementos eliminados.")


# ==========================================
# HELPERS GENÉRICOS DE PLAYWRIGHT
# ==========================================

def _normalizar_texto(texto):
    return " ".join((texto or "").split())


def _listar_valores_visibles(locator, extractor, limite=25):
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
            valor = _normalizar_texto(extractor(item))
            if valor and valor not in valores:
                valores.append(valor)
        except Exception:
            continue
    return valores


def _listar_textos_visibles(locator, limite=25):
    return _listar_valores_visibles(locator, lambda item: item.inner_text(), limite)


def _listar_aria_labels(locator, limite=25):
    return _listar_valores_visibles(locator, lambda item: item.get_attribute("aria-label"), limite)


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


def _error_transitorio_locator(error):
    texto = str(error).lower()
    return any(
        patron in texto
        for patron in (
            "not attached to the dom",
            "element is not attached",
            "element handle is detached",
            "stale",
        )
    )


def _click_selector_visible(page, selectores, force=False, descripcion=None, requerido=False):
    ultimo_error = None
    for _ in range(3):
        item = _buscar_selector_visible(page, selectores)
        if not item:
            if requerido:
                raise RuntimeError(f"No se encontró elemento visible: {descripcion or selectores}")
            return False
        try:
            item.scroll_into_view_if_needed()
            item.click(force=force)
            return True
        except Exception as error:
            ultimo_error = error
            if not _error_transitorio_locator(error):
                raise
            page.wait_for_timeout(150)

    if requerido and ultimo_error:
        raise RuntimeError(f"No se pudo clickear elemento visible: {descripcion or selectores} ({ultimo_error})")
    return False


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
                try:
                    item.scroll_into_view_if_needed()
                    item.click(force=force)
                except Exception as error:
                    if _error_transitorio_locator(error):
                        page.wait_for_timeout(120)
                        continue
                    raise
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
            if item.is_visible():
                item.scroll_into_view_if_needed()
                item.click(force=force)
                return True
    except Exception:
        pass
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
