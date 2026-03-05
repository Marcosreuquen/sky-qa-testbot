"""
Flujo de datos de pasajero y avance a checkout:
  - rellenar formulario de pasajeros
  - avanzar desde extras/pasajero hasta checkout
"""

import re
import time

from playwright.sync_api import expect

import core.state as state
from core.helpers import (
    _buscar_visible,
    _buscar_selector_visible,
    _click_selector_visible,
    _click_todos_selectores_visibles,
    _rellenar_input_visible,
    _click_texto_visible,
    _click_ultimo_texto_visible,
    _guardar_html_debug,
)
from core.search_flow import _saltar_extras, _seleccionar_opcion_dropdown


# (selector, clave en pasajero, label para warning)
_DROPDOWNS_PASAJERO = [
    ('[data-test="is-thirdStep-dropdownGender"]', "genero", "género"),
    ('[data-test="is-thirdStep-dropdownCountryIssue"]', "pais_emision", "país de emisión"),
    ('[data-test="is-thirdStep-dropdownDocumentType"]', "doc_tipo", "tipo de documento"),
]


# ==========================================
# AVANCE ENTRE ETAPAS
# ==========================================

def _esperar_o_avanzar_hasta_pasajeros(page, timeout_ms=60000):
    deadline = time.monotonic() + timeout_ms / 1000

    while time.monotonic() < deadline:
        url_actual = page.url or ""
        if "passenger-detail" in url_actual or "checkout" in url_actual:
            return

        _saltar_extras(page)
        page.wait_for_timeout(1200)

    raise RuntimeError(
        f"No se pudo avanzar a passenger-detail/checkout dentro de {timeout_ms}ms. URL actual: {page.url}",
    )


def _avanzar_a_checkout_desde_passenger(page, timeout_ms=60000):
    deadline = time.monotonic() + timeout_ms / 1000

    while time.monotonic() < deadline:
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


def _avanzar_a_checkout(page, timeout_ms=60000):
    deadline = time.monotonic() + timeout_ms / 1000

    while time.monotonic() < deadline:
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


# ==========================================
# CONTACTO COMPROBANTE
# ==========================================

def _completar_contacto_comprobante(page):
    seccion = _buscar_visible(page.get_by_text("Contacto para recibir el comprobante"))
    if not seccion:
        return True

    mensaje_error = "Indica quién será el contacto que recibirá el comprobante."
    nombre = state.CFG["pasajero"].get("nombre", "").strip()
    apellido = state.CFG["pasajero"].get("apellido", "").strip()
    nombre_completo = f"{nombre} {apellido}".strip()
    candidatos_nombre = [valor for valor in [nombre_completo, nombre] if valor]

    for _ in range(5):
        if not _buscar_visible(page.get_by_text(mensaje_error)):
            return True

        try:
            seccion.scroll_into_view_if_needed()
        except Exception:
            pass

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

        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        page.wait_for_timeout(220)

        if _buscar_visible(page.get_by_text(mensaje_error)):
            for candidato in candidatos_nombre:
                if _click_ultimo_texto_visible(page.get_by_text(candidato, exact=True), force=True):
                    page.wait_for_timeout(200)
                    break

        _rellenar_input_visible(
            page,
            ['[data-test="is-reservationManagerForm-textFieldEmail"] input'],
            state.CFG["pasajero"]["email"],
        )
        _rellenar_input_visible(
            page,
            ['[data-test="is-reservationManagerForm-textFieldPhoneNumber"] input'],
            state.CFG["pasajero"]["telefono"],
        )
        _rellenar_input_visible(
            page,
            ['[data-test="is-reservationManagerForm-textFieldPrefixPhoneNumber"] input'],
            state.CFG["pasajero"]["prefijo_pais"],
        )

        _click_selector_visible(
            page,
            ['h3:has-text("Contacto para recibir el comprobante")'],
            force=True,
        )
        page.wait_for_timeout(250)

    return not _buscar_visible(page.get_by_text(mensaje_error))


# ==========================================
# FORMULARIO DE PASAJERO
# ==========================================

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

    for selector, clave, label in _DROPDOWNS_PASAJERO:
        if _click_selector_visible(page, [selector]):
            if not _seleccionar_opcion_dropdown(page, pasajero[clave]):
                print(f"⚠️ No se pudo seleccionar {label} '{pasajero[clave]}'.")

    _rellenar_input_visible(
        page,
        ['[data-test="is-passengerForm-textFieldDocumentNumber"] input', '.card-passenger__passenger-form--fourth-row input'],
        pasajero["doc_numero"],
        requerido=True,
    )

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
    pasajeros = state.CFG["pasajeros_lista"]
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
