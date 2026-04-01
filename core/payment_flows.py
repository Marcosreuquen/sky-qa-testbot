"""
Flujos de pago por market:
  - PE: Niubiz
  - CL: Webpay (Transbank)
  - AR: Mercado Pago
  - BR: Cielo

Para agregar un market: 1) implementar _pagar_<nombre>(page) aquí,
2) agregar entrada en PAYMENT_DISPATCH, 3) actualizar config/pago.py.
"""

import re
import time

from playwright.sync_api import expect

import core.state as state
from core.helpers import (
    _buscar_selector_visible,
    _click_selector_visible,
    _normalizar_texto,
    gestionar_pausa_edicion,
    pausar_en_checkpoint,
)


# ==========================================
# HELPERS DE PAGO
# ==========================================

def _esperar_selector_pago(page, selectores, timeout_ms=20000, contexto="esperando_selector_pago"):
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        gestionar_pausa_edicion(page, contexto)
        item = _buscar_selector_visible(page, selectores)
        if item:
            return item
        page.wait_for_timeout(350)
    return None


def _click_selector_pago(page, selectores, timeout_ms=15000, force=True, descripcion=None):
    deadline = time.monotonic() + timeout_ms / 1000
    ultimo_error = None
    while time.monotonic() < deadline:
        gestionar_pausa_edicion(page, f"click_{descripcion or 'selector_pago'}")
        item = _buscar_selector_visible(page, selectores)
        if item:
            try:
                item.scroll_into_view_if_needed()
            except Exception:
                pass
            try:
                item.click(force=force, timeout=2500)
                return True
            except Exception as error:
                ultimo_error = error
        page.wait_for_timeout(350)

    if ultimo_error:
        raise RuntimeError(f"No se pudo clickear '{descripcion or selectores}': {ultimo_error}")
    raise RuntimeError(f"No apareció '{descripcion or selectores}' dentro de {timeout_ms}ms.")


def _rellenar_input_pago(page, selectores, valor, timeout_ms=15000, descripcion=None, delay=None):
    campo = _esperar_selector_pago(
        page,
        selectores,
        timeout_ms=timeout_ms,
        contexto=f"input_{descripcion or 'pago'}",
    )
    if not campo:
        raise RuntimeError(f"No apareció input '{descripcion or selectores}'.")

    campo.click(force=True)
    try:
        campo.fill("")
    except Exception:
        pass

    if delay is not None:
        campo.type(str(valor), delay=delay)
    else:
        campo.fill(str(valor))
    return campo


def _esperar_url_que_contenga(page, fragmentos, timeout_ms=30000, contexto="esperando_url_pago"):
    deadline = time.monotonic() + timeout_ms / 1000
    fragmentos_normalizados = [fragmento.lower() for fragmento in fragmentos]
    while time.monotonic() < deadline:
        gestionar_pausa_edicion(page, contexto)
        url_actual = (page.url or "").lower()
        if any(fragmento in url_actual for fragmento in fragmentos_normalizados):
            return True
        page.wait_for_timeout(350)
    return False


def _seleccionar_autorizacion_webpay(page):
    selector_vci = _esperar_selector_pago(
        page,
        [
            "select#vci",
            'select[name="vci"]',
        ],
        timeout_ms=10000,
        contexto="webpay_autorizacion",
    )
    if not selector_vci:
        return False

    opciones = []
    opciones_locator = selector_vci.locator("option")
    for indice in range(opciones_locator.count()):
        opcion = opciones_locator.nth(indice)
        try:
            valor = opcion.get_attribute("value") or ""
            texto = _normalizar_texto(opcion.inner_text()).lower()
            if valor:
                opciones.append((valor, texto))
        except Exception:
            continue

    valor_preferido = None
    for valor, texto in opciones:
        if valor.upper() in {"TSY", "Y"} or any(
            patron in texto for patron in ("aprob", "author", "acept", "correct")
        ):
            valor_preferido = valor
            break

    if not valor_preferido and opciones:
        valor_preferido = opciones[0][0]

    if not valor_preferido:
        return False

    selector_vci.select_option(valor_preferido)
    return True


def _prefill_contacto(page):
    """Rellena nombre/apellido/email del pasajero en formularios de pasarela (best-effort)."""
    try:
        page.locator("div").filter(has_text=re.compile(r"^Nombre$")).last.locator("input.input").fill(state.CFG["pasajero"]["nombre"])
        page.locator("div").filter(has_text=re.compile(r"^Apellido$")).last.locator("input.input").fill(state.CFG["pasajero"]["apellido"])
        page.locator("div").filter(has_text="Correo electrónico").last.locator("input.input").fill(state.CFG["pasajero"]["email"])
    except Exception as e:
        print(f"⚠️ Pre-fill contacto: {e}")


def _expandir_mas_medios_pago(page):
    return bool(
        _buscar_selector_visible(
            page,
            [
                'button:has-text("Más medios de pago")',
                'button:has-text("Mas medios de pago")',
                'button:has-text("Otros medios de pago")',
                'button[aria-label*="payment methods" i]',
                'button[aria-label*="medios de pago" i]',
            ],
        )
    ) and (
        _buscar_selector_visible(
            page,
            [
                'button:has-text("Más medios de pago")',
                'button:has-text("Mas medios de pago")',
                'button:has-text("Otros medios de pago")',
                'button[aria-label*="payment methods" i]',
                'button[aria-label*="medios de pago" i]',
            ],
        ).click(force=True)
        is None
    )


def _esperar_medio_pago_visible(page, nombre_medio, timeout_ms=45000):
    deadline = time.monotonic() + timeout_ms / 1000
    selectores_medio = [
        f'text="{nombre_medio}"',
        f'div:has-text("{nombre_medio}")',
        f'[data-test*="{nombre_medio.lower().replace(" ", "-")}"]',
        f'[data-test*="{nombre_medio.lower()}"]',
    ]

    while time.monotonic() < deadline:
        gestionar_pausa_edicion(page, f"esperando_medio_pago_{nombre_medio.lower().replace(' ', '_')}")
        item = _buscar_selector_visible(page, selectores_medio)
        if item:
            return item
        _expandir_mas_medios_pago(page)
        page.wait_for_timeout(700)

    return None


def _seleccionar_medio_pago(page, nombre_medio, contenedor_selector=None, radio_selector=None):
    item = _esperar_medio_pago_visible(page, nombre_medio)
    if not item:
        raise RuntimeError(f"No apareció el medio de pago '{nombre_medio}'.")

    if contenedor_selector:
        try:
            contenedor = page.locator(contenedor_selector)
            contenedor.wait_for(state="visible", timeout=5000)
            if radio_selector:
                contenedor.locator(radio_selector).click(force=True)
            else:
                contenedor.click(force=True)
            return
        except Exception:
            pass

    try:
        item.scroll_into_view_if_needed()
    except Exception:
        pass
    item.click(force=True)


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
                if candidato.is_visible():
                    input_tarjeta = candidato
                    break
            except Exception:
                continue
        if input_tarjeta:
            break
        if i % 5 == 0:
            print("   ... Buscando ...")
        page.wait_for_timeout(2000)
    return input_tarjeta


def _finalizar_compra(page, boton_texto="Ir a pagar"):
    """Checkbox T&C + botón de pago."""
    print("--- Finalizando Compra ---")

    print("✅ Buscando checkbox...")
    checkbox_encontrado = any(
        _click_selector_visible(
            page,
            selectores,
            force=True,
            requerido=False,
        )
        for selectores in (
            [".checkbox_icon"],
            ['label:has(.checkbox_icon)'],
            ['label:has-text("Acepto")'],
            ['label:has-text("Términos")', 'label:has-text("Terminos")', 'label:has-text("Terms")'],
            ['input[type="checkbox"]'],
            ['[role="checkbox"]'],
        )
    )
    if not checkbox_encontrado:
        print("⚠️ No se encontró checkbox visible de términos. Se intenta continuar igual.")

    print(f"🚀 Buscando botón '{boton_texto}'...")
    _click_selector_pago(
        page,
        [
            f'button:has-text("{boton_texto}")',
            f'input[type="submit"][value*="{boton_texto}" i]',
            'button:has-text("Ir a pagar")',
            'button:has-text("Pagar")',
            'button:has-text("Pay")',
            'button[type="submit"]',
        ],
        timeout_ms=12000,
        descripcion=f"botón {boton_texto}",
    )
    print("🎉 ¡CLICK EN PAGAR REALIZADO!")


# ==========================================
# FLUJOS DE PAGO
# ==========================================

def _pagar_niubiz(page):
    """Perú — Niubiz"""
    try:
        _seleccionar_medio_pago(page, "Niubiz")
    except Exception as e:
        raise RuntimeError(f"Niubiz no apareció en checkout: {e}") from e

    print("Esperando animación del formulario...")
    page.wait_for_timeout(5000)

    _prefill_contacto(page)

    input_tarjeta = _buscar_campo_tarjeta(page)
    if not input_tarjeta:
        raise RuntimeError("Nunca apareció el campo 'Número de Tarjeta'.")

    print("✅ Campo tarjeta detectado. Validando habilitación...")
    try:
        input_tarjeta.wait_for(state="visible", timeout=30000)
        expect(input_tarjeta).to_be_editable(timeout=30000)

        print(f"⏳ Pausa de seguridad ({state.CFG['pausa']}ms)...")
        page.wait_for_timeout(state.CFG["pausa"])

        input_tarjeta.click(force=True)
        input_tarjeta.fill(state.CFG["tarjeta"]["numero"])

        print("🎹 Tabs: Tarjeta -> Nombre -> Apellido -> Fecha")
        page.keyboard.press("Tab")  # Nombre
        page.keyboard.press("Tab")  # Apellido
        page.keyboard.press("Tab")  # Fecha

        fecha_limpia = state.CFG["tarjeta"]["fecha"].replace("/", "")
        print(f"⌨️ Fecha: {fecha_limpia}")
        page.keyboard.type(fecha_limpia, delay=100)

        print("🎹 Tab a CVV...")
        page.keyboard.press("Tab")
        print(f"⌨️ CVV: {state.CFG['tarjeta']['cvv']}")
        page.keyboard.type(state.CFG["tarjeta"]["cvv"], delay=100)

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
    _seleccionar_medio_pago(page, "Webpay")

    if pausar_en_checkpoint(page, "PAGO"):
        return

    # T&C + "Ir a pagar" en SKY (redirige a Transbank)
    _finalizar_compra(page)

    # ── Paso 2: Portal Transbank — Seleccionar "Tarjetas" ──
    print("🌐 Esperando portal Transbank...")
    if not (
        _esperar_url_que_contenga(page, ["transbank.cl", "webpay"], timeout_ms=45000, contexto="webpay_portal")
        or _esperar_selector_pago(
            page,
            [
                'button:has-text("Crédito")',
                'button:has-text("Credito")',
                'button:has-text("Tarjetas")',
                'button:has-text("Tarjeta de crédito")',
                "button#credito",
                "button#tarjetas",
            ],
            timeout_ms=45000,
            contexto="webpay_portal",
        )
    ):
        raise RuntimeError("No apareció el portal Webpay/Transbank.")
    page.wait_for_timeout(1200)

    print("🃏 Seleccionando método de crédito...")
    _click_selector_pago(
        page,
        [
            'button:has-text("Crédito")',
            'button:has-text("Credito")',
            'button:has-text("Tarjetas")',
            'button:has-text("Tarjeta de crédito")',
            "button#credito",
            "button#tarjetas",
        ],
        timeout_ms=12000,
        descripcion="entrada crédito Webpay",
    )
    page.wait_for_timeout(1200)

    # ── Paso 3: Llenar datos de tarjeta ──
    print("💳 Llenando datos de tarjeta...")
    _rellenar_input_pago(
        page,
        [
            "input#card-number",
            'input[name="card-number"]',
            'input[autocomplete="cc-number"]',
            'input[placeholder*="número de tarjeta" i]',
            'input[placeholder*="card number" i]',
        ],
        state.CFG["tarjeta"]["numero"],
        timeout_ms=15000,
        descripcion="número tarjeta Webpay",
    )

    page.locator("body").click()
    page.wait_for_timeout(700)

    fecha = state.CFG["tarjeta"]["fecha"].replace("/", "")
    _rellenar_input_pago(
        page,
        [
            "input#card-exp",
            'input[name="card-exp"]',
            'input[autocomplete="cc-exp"]',
            'input[placeholder*="mm/yy" i]',
            'input[placeholder*="exp" i]',
        ],
        fecha,
        timeout_ms=12000,
        descripcion="fecha Webpay",
        delay=80,
    )

    _rellenar_input_pago(
        page,
        [
            "input#card-cvv",
            'input[name="card-cvv"]',
            'input[autocomplete="cc-csc"]',
            'input[placeholder*="cvv" i]',
            'input[placeholder*="cvc" i]',
            'input[placeholder*="seguridad" i]',
        ],
        state.CFG["tarjeta"]["cvv"],
        timeout_ms=12000,
        descripcion="cvv Webpay",
        delay=80,
    )

    print("🚀 Click en 'Pagar'...")
    _click_selector_pago(
        page,
        [
            'button:has-text("Pagar")',
            'input[type="submit"][value*="Pagar" i]',
            'button:has-text("Continuar")',
            'button[type="submit"]',
        ],
        timeout_ms=12000,
        descripcion="pagar Webpay",
    )

    # ── Paso 4: Autenticación — RUT y Clave ──
    print("🔐 Esperando página de autenticación...")
    if not (
        _esperar_url_que_contenga(
            page,
            ["authenticator", "autentic", "authorize"],
            timeout_ms=35000,
            contexto="webpay_auth_url",
        )
        or _esperar_selector_pago(
            page,
            [
                "input#rutClient",
                'input[name="rutClient"]',
                'input[placeholder*="rut" i]',
                "input#passwordClient",
                'input[type="password"]',
            ],
            timeout_ms=35000,
            contexto="webpay_auth_form",
        )
    ):
        raise RuntimeError("No apareció la pantalla de autenticación Webpay.")
    page.wait_for_timeout(800)

    rut = state.CFG["tarjeta"].get("rut", "11.111.111-1")
    clave = state.CFG["tarjeta"].get("clave", "123")

    print(f"📝 RUT: {rut}")
    _rellenar_input_pago(
        page,
        [
            "input#rutClient",
            'input[name="rutClient"]',
            'input[name*="rut" i]',
            'input[placeholder*="rut" i]',
        ],
        rut,
        timeout_ms=15000,
        descripcion="rut Webpay",
    )
    _rellenar_input_pago(
        page,
        [
            "input#passwordClient",
            'input[name="passwordClient"]',
            'input[type="password"]',
            'input[placeholder*="clave" i]',
            'input[placeholder*="password" i]',
        ],
        clave,
        timeout_ms=15000,
        descripcion="clave Webpay",
    )

    _click_selector_pago(
        page,
        [
            'input[type="submit"][value="Aceptar"]',
            'input[type="submit"][value*="Autorizar" i]',
            'button:has-text("Aceptar")',
            'button:has-text("Autorizar")',
            'button:has-text("Continuar")',
        ],
        timeout_ms=12000,
        descripcion="confirmación auth Webpay",
    )

    # ── Paso 5: Confirmación ──
    print("✅ Esperando pantalla de confirmación...")
    page.wait_for_timeout(2000)

    _seleccionar_autorizacion_webpay(page)
    try:
        _click_selector_pago(
            page,
            [
                'input[type="submit"][value="Continuar"]',
                'input[type="submit"][value*="Autorizar" i]',
                'button:has-text("Continuar")',
                'button:has-text("Autorizar")',
                'button:has-text("Volver a SKY")',
                'a:has-text("Volver a SKY")',
            ],
            timeout_ms=12000,
            descripcion="salida Webpay",
        )
    except Exception as error:
        print(f"⚠️ No se encontró CTA final explícito en Webpay: {error}")

    print("🎉 ¡Webpay completado! Esperando redirección a SKY...")


def _pagar_mercadopago(page):
    """Argentina — Mercado Pago
    Campos en iframe (secure-fields.mercadopago.com): cardNumber, expirationDate, securityCode
    Campos regulares: cardholderName, docType, docNumber, email, installments
    """

    # ── Paso 1: Seleccionar Mercado Pago en el checkout de SKY ──
    _seleccionar_medio_pago(
        page,
        "Mercado Pago",
        contenedor_selector='[data-test="IS-paymentMethodList-cardFop-mercado-pago"]',
        radio_selector='[data-test="IS-cardFop-radioButton"]',
    )

    print("Esperando formulario Mercado Pago...")
    page.wait_for_timeout(5000)

    _prefill_contacto(page)

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
            card_input.type(state.CFG["tarjeta"]["numero"], delay=50)
        else:
            raise RuntimeError("No se encontró iframe de cardNumber")

        page.wait_for_timeout(1000)

        # --- Nombre del titular ---
        print("👤 Titular...")
        titular = state.CFG["tarjeta"].get("titular", "APRO")
        holder_input = page.locator('[data-test="IS-mercadoPagoForm-inputCardHolderName"] input.input')
        holder_input.click()
        holder_input.fill(titular)

        page.wait_for_timeout(500)

        # --- Fecha de expiración (iframe name="expirationDate") ---
        print("📅 Fecha expiración (iframe)...")
        exp_iframe = _buscar_iframe_mp(page, "expirationDate")
        if exp_iframe:
            exp_input = _input_visible_iframe(exp_iframe)
            exp_input.wait_for(state="visible", timeout=15000)
            exp_input.click()
            exp_input.type(state.CFG["tarjeta"]["fecha"], delay=50)  # MM/YY
        else:
            raise RuntimeError("No se encontró iframe de expirationDate")

        page.wait_for_timeout(500)

        # --- CVV / Código de seguridad (iframe name="securityCode") ---
        print("🔒 CVV (iframe)...")
        cvv_iframe = _buscar_iframe_mp(page, "securityCode")
        if cvv_iframe:
            cvv_input = _input_visible_iframe(cvv_iframe)
            cvv_input.wait_for(state="visible", timeout=15000)
            cvv_input.click()
            cvv_input.type(state.CFG["tarjeta"]["cvv"], delay=50)
        else:
            print("❌ No se encontró iframe de securityCode")
        page.wait_for_timeout(1000)

        # --- Cuotas (dropdown custom) → seleccionar "1 cuota" ---
        print("💰 Seleccionando cuotas...")
        cuotas_container = page.locator('[data-test="IS-mercadoPagoForm-selectInstallment"]')
        cuotas_container.locator(".textfield_input").click()
        page.wait_for_timeout(1000)
        page.get_by_text(re.compile(r"1 cuota", re.IGNORECASE)).first.click()
        page.wait_for_timeout(500)

        # --- Tipo de documento (dropdown custom) → "DNI" ---
        print("📄 Tipo de documento...")
        doc_tipo = state.CFG["tarjeta"].get("doc_tipo", "DNI")
        doc_type_container = page.locator('[data-test="IS-mercadoPagoForm-selectDocType"]')
        doc_type_container.locator(".textfield_input").click()
        page.wait_for_timeout(500)
        page.get_by_text(doc_tipo, exact=True).first.click()
        page.wait_for_timeout(500)

        # --- Número de documento ---
        print("🆔 Número de documento...")
        doc_numero = state.CFG["tarjeta"].get("doc_numero", "")
        doc_input = page.locator('[data-test="IS-mercadoPagoForm-inputDocNumber"] input.input')
        doc_input.click()
        doc_input.fill(doc_numero)

        # --- Email ---
        print("📧 Email...")
        email_mp = state.CFG["tarjeta"].get("email", state.CFG["pasajero"]["email"])
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
    _seleccionar_medio_pago(page, "Cielo")

    print("Esperando formulario Cielo...")
    page.wait_for_timeout(5000)

    _prefill_contacto(page)

    input_tarjeta = _buscar_campo_tarjeta(page)
    if not input_tarjeta:
        raise RuntimeError("Nunca apareció el campo tarjeta para Cielo.")

    try:
        input_tarjeta.wait_for(state="visible", timeout=30000)
        expect(input_tarjeta).to_be_editable(timeout=30000)
        page.wait_for_timeout(state.CFG["pausa"])

        input_tarjeta.click(force=True)
        input_tarjeta.fill(state.CFG["tarjeta"]["numero"])

        # CVV
        page.keyboard.press("Tab")
        page.keyboard.type(state.CFG["tarjeta"]["cvv"], delay=100)

        # Fecha
        fecha_limpia = state.CFG["tarjeta"]["fecha"].replace("/", "")
        page.keyboard.press("Tab")
        page.keyboard.type(fecha_limpia, delay=100)

        # Seleccionar Débito si aplica
        tipo = state.CFG["tarjeta"].get("tipo", "")
        if tipo:
            try:
                page.get_by_text(tipo, exact=False).first.click()
            except Exception:
                pass

        if pausar_en_checkpoint(page, "PAGO"):
            return

        _finalizar_compra(page, boton_texto="Pagar")

        # Código de autenticación (3DS)
        codigo = state.CFG["tarjeta"].get("codigo_auth", "")
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


# Mapa market → función de pago (fuente de verdad para dispatch)
PAYMENT_DISPATCH = {
    "PE": _pagar_niubiz,
    "CL": _pagar_webpay,
    "AR": _pagar_mercadopago,
    "BR": _pagar_cielo,
}
