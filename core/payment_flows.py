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

from playwright.sync_api import expect

import core.state as state
from core.helpers import (
    _activar_modo_manual,
    _buscar_selector_visible,
    pausar_en_checkpoint,
)


# ==========================================
# HELPERS DE PAGO
# ==========================================

def _prefill_contacto(page):
    """Rellena nombre/apellido/email del pasajero en formularios de pasarela (best-effort)."""
    try:
        page.locator("div").filter(has_text=re.compile(r"^Nombre$")).last.locator("input.input").fill(state.CFG["pasajero"]["nombre"])
        page.locator("div").filter(has_text=re.compile(r"^Apellido$")).last.locator("input.input").fill(state.CFG["pasajero"]["apellido"])
        page.locator("div").filter(has_text="Correo electrónico").last.locator("input.input").fill(state.CFG["pasajero"]["email"])
    except Exception as e:
        print(f"⚠️ Pre-fill contacto: {e}")


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
    checkbox_exacto = page.locator(".checkbox_icon").last
    checkbox_exacto.scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    checkbox_exacto.click()

    print(f"🚀 Buscando botón '{boton_texto}'...")
    btn_pagar = page.locator("button").filter(has_text=boton_texto)
    btn_pagar.wait_for(state="visible", timeout=5000)
    btn_pagar.click()
    print("🎉 ¡CLICK EN PAGAR REALIZADO!")


# ==========================================
# FLUJOS DE PAGO
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

    _prefill_contacto(page)

    input_tarjeta = _buscar_campo_tarjeta(page)
    if not input_tarjeta:
        print("❌ Error: Nunca apareció el campo 'Número de Tarjeta'.")
        return

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
    card_number = page.locator("input#card-number")
    card_number.wait_for(state="visible", timeout=15000)
    card_number.click()
    card_number.fill(state.CFG["tarjeta"]["numero"])

    page.locator("body").click()
    page.wait_for_timeout(1000)

    card_exp = page.locator("input#card-exp")
    card_exp.click()
    fecha = state.CFG["tarjeta"]["fecha"].replace("/", "")
    card_exp.type(fecha, delay=80)

    card_cvv = page.locator("input#card-cvv")
    card_cvv.click()
    card_cvv.type(state.CFG["tarjeta"]["cvv"], delay=80)

    print("🚀 Click en 'Pagar'...")
    btn_pagar_tbk = page.get_by_role("button", name="Pagar", exact=True)
    btn_pagar_tbk.wait_for(state="visible", timeout=10000)
    page.wait_for_timeout(1000)
    btn_pagar_tbk.click()

    # ── Paso 4: Autenticación — RUT y Clave ──
    print("🔐 Esperando página de autenticación...")
    page.wait_for_url(re.compile(r"authenticator"), timeout=30000)
    page.wait_for_timeout(1000)

    rut = state.CFG["tarjeta"].get("rut", "11.111.111-1")
    clave = state.CFG["tarjeta"].get("clave", "123")

    print(f"📝 RUT: {rut}")
    page.locator("input#rutClient").fill(rut)
    page.locator("input#passwordClient").fill(clave)

    page.locator('input[type="submit"][value="Aceptar"]').click()

    # ── Paso 5: Confirmación ──
    print("✅ Esperando pantalla de confirmación...")
    page.wait_for_timeout(3000)

    page.locator("select#vci").select_option("TSY")
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
            print("❌ No se encontró iframe de cardNumber")
            return

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
    page.wait_for_selector('text="Cielo"', timeout=45000)
    cielo_btn = page.locator("div").filter(has_text="Cielo").last
    cielo_btn.scroll_into_view_if_needed()
    cielo_btn.click(force=True)

    print("Esperando formulario Cielo...")
    page.wait_for_timeout(5000)

    _prefill_contacto(page)

    input_tarjeta = _buscar_campo_tarjeta(page)
    if not input_tarjeta:
        print("❌ Error: Nunca apareció el campo tarjeta para Cielo.")
        return

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
