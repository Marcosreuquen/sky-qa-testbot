"""
Helpers genéricos de interacción con Playwright.
Incluye: utilidades de locator, checkpoint, modo manual y exploración de UI.
Sin dependencias de flujo de negocio — importar desde cualquier módulo.
"""

import os
import re
from datetime import datetime

import core.state as state


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
        return True
    return False


def _activar_modo_manual(page):
    if state.CFG.get("headless"):
        print("ℹ️ Modo headless: se omite page.pause().")
        return
    page.pause()


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
