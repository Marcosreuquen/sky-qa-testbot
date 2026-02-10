import re
from playwright.sync_api import Playwright, sync_playwright, expect

from cli import parse_args, aplicar_args

# ==========================================
# 🤖 INICIO DEL BOT
# ==========================================

# Configuración resuelta (defaults + CLI overrides)
CFG = aplicar_args(parse_args())


def pausar_en_checkpoint(page, checkpoint_actual):
    """Pausa el bot si se alcanza el checkpoint configurado"""
    if CFG["checkpoint"] == checkpoint_actual:
        print(f"\n⏸️  CHECKPOINT ALCANZADO: {checkpoint_actual}")
        print("🖱️  Puedes interactuar manualmente con la página.")
        print("▶️  Presiona 'Resume' en el inspector para continuar o cerrar.\n")
        page.pause()
        return True
    return False

def run(playwright: Playwright) -> None:
    # Configuración del navegador
    browser = playwright.chromium.launch(headless=CFG["headless"], slow_mo=CFG["slow_mo"])
    context = browser.new_context()
    page = context.new_page()

    print(f"--- 🚀 Iniciando Test [{CFG['market']}]: {CFG['origen']} -> {CFG['destino']} ---")
    print(f"    Medio de pago: {CFG['medio_pago']}")
    page.goto(CFG["url"])
    
    # -------------------------------------------
    # 1. BÚSQUEDA DE VUELO
    # -------------------------------------------
    page.locator("label").filter(has_text="Solo ida").click()
    
    # Origen
    page.locator("#origin-id").click()
    page.locator("#origin-id input").first.fill(CFG["origen"])
    page.get_by_text(CFG["origen"]).first.click()

    # Destino
    page.locator("#destination-id").click()
    page.locator("#destination-id input").first.fill(CFG["destino"])
    page.get_by_text(CFG["destino"]).first.click()

    # Selección de Fecha
    page.wait_for_timeout(1000)
    dias = page.locator('div.vc-day-content[aria-disabled="false"]')
    # Fix por si el calendario no abrió
    if not dias.first.is_visible():
        page.get_by_text("Ida", exact=True).first.click()
        page.wait_for_timeout(500)
    
    # Lógica de días
    if dias.count() > CFG["dias"]: 
        dias.nth(CFG["dias"]).click()
    else: 
        dias.last.click()  
    
    page.get_by_role("button", name="Buscar vuelo").click()

    # 🛑 Checkpoint: Después de búsqueda
    if pausar_en_checkpoint(page, "BUSQUEDA"):
        return

    # -------------------------------------------
    # 2. SELECCIÓN DE TARIFA
    # -------------------------------------------
    print("--- Seleccionando Vuelo ---")
    try:
        page.wait_for_selector('button:has-text("Elegir vuelo"), [data-test^="is-itinerary-selectFlight"]', timeout=30000)
    except: pass

    # Pausa adicional para que las cards terminen de cargar
    print("⏳ Esperando a que las cards de vuelo carguen completamente...")
    page.wait_for_timeout(2500)  # 2.5 segundos adicionales

    btns = page.locator('button:has-text("Elegir vuelo")')
    if btns.count() == 0: btns = page.locator('[data-test^="is-itinerary-selectFlight"]')
    
    seleccionado = False
    for i in range(btns.count()):
        try:
            btns.nth(i).scroll_into_view_if_needed()  # Asegurar visibilidad
            page.wait_for_timeout(500)  # Pequeña pausa después del scroll
            btns.nth(i).click(force=True)
            page.wait_for_selector('[data-test^="is-itinerary-selectRate"]', timeout=5000)
            seleccionado = True
            break
        except: continue
    
    # Fallback si no seleccionó botón
    if not seleccionado:
        page.locator('div').filter(has_text=re.compile(r"\d{2}:\d{2}")).first.click(force=True)

    # Tarifa (Plus o primera disponible)
    btns_sel = page.locator('[data-test^="is-itinerary-selectRate"]').first.get_by_role("button", name="Seleccionar")
    if btns_sel.count() > 1: btns_sel.nth(1).click()
    else: btns_sel.first.click()

    # Saltos de Marketing
    try:
        page.wait_for_timeout(1500)
        if page.get_by_role("button", name="Seguir con mi tarifa actual").is_visible():
            page.get_by_role("button", name="Seguir con mi tarifa actual").click()
    except: pass

    print("--- Saltando Extras ---")
    page.get_by_role("button", name="Continuar al siguiente vuelo").click()
    page.get_by_role("button", name="Continuar sin elegir").click()
    page.get_by_role("button", name="Continuar").click()

    # 🛑 Checkpoint: Después de selección de tarifa
    if pausar_en_checkpoint(page, "SELECCION_TARIFA"):
        return

    # -------------------------------------------
    # 3. DATOS DEL PASAJERO
    # -------------------------------------------
    print("--- Llenando Datos Pasajero ---")
    expect(page).to_have_url(re.compile(".*passenger-detail"))
    page.wait_for_timeout(1500)
    
    # Inputs de texto
    page.locator('[data-test="is-passengerForm-textFieldNamePax"] input').fill(CFG["pasajero"]["nombre"])
    page.locator('[data-test="is-passengerForm-textFieldLastname"] input').fill(CFG["pasajero"]["apellido"])
    
    # Fecha Nacimiento
    d, m, a = CFG["pasajero"]["fecha_nac"].split("/")
    cf = page.locator('[data-test="is-passengerForm-textFieldBirthdate"]')
    cf.locator("input").nth(0).fill(d)
    cf.locator("input").nth(1).fill(m)
    cf.locator("input").nth(2).fill(a)
    
    # Dropdowns
    page.locator('[data-test="is-thirdStep-dropdownGender"]').click()
    page.get_by_text(CFG["pasajero"]["genero"], exact=True).first.click()
    page.locator('[data-test="is-thirdStep-dropdownCountryIssue"]').click()
    page.get_by_text(CFG["pasajero"]["pais_emision"], exact=True).first.click()
    page.locator('[data-test="is-thirdStep-dropdownDocumentType"]').click()
    page.get_by_text(CFG["pasajero"]["doc_tipo"], exact=True).first.click()
    
    # Documento y Contacto
    page.locator('.card-passenger__passenger-form--fourth-row input').last.fill(CFG["pasajero"]["doc_numero"])
    page.locator('[data-test="is-passengerForm-textFieldEmail"] input').fill(CFG["pasajero"]["email"])
    page.locator('[data-test="is-passengerForm-textFieldPrefix"] input').fill(CFG["pasajero"]["prefijo_pais"])
    page.locator('[data-test="is-passengerForm-textFieldPhone"] input').fill(CFG["pasajero"]["telefono"])

    # Avanzar
    print("--- Avanzando ---")
    btn_sig = page.locator("button").filter(has_text="Siguiente")
    if btn_sig.count() > 0 and btn_sig.first.is_visible(): 
        btn_sig.first.click()
    else: 
        page.get_by_role("button", name="Guardar datos").click()

    # Comprobante (Opcional)
    try:
        if page.get_by_text("Contacto para recibir el comprobante").is_visible(timeout=3000):
            page.locator("div").filter(has_text="Nombre de quien recibirá el comprobante").last.click()
            page.get_by_text(f"{CFG['pasajero']['nombre']}").last.click()
            page.get_by_role("button", name="Ir al pago").click()
    except: pass

    # Confirmación y Modal
    try:
        ck = page.locator(".textfield_icon").first
        if ck.is_visible(timeout=2000): ck.click()
        btn_mod = page.locator("button").filter(has_text="Proceder al pago")
        if btn_mod.is_visible(timeout=5000): btn_mod.click(force=True)
    except: pass

    # 🛑 Checkpoint: Después de datos del pasajero
    if pausar_en_checkpoint(page, "DATOS_PASAJERO"):
        return

    # -------------------------------------------
    # 4. CHECKOUT Y PAGO
    # -------------------------------------------
    print("--- Llegada al Checkout ---")

    try:
        expect(page).to_have_url(re.compile(".*checkout"), timeout=30000)
    except Exception as e:
        print(f"⚠️ No se pudo llegar al checkout en 30s: {e}")
        print("🖱️ Activando modo manual - continúa tú desde aquí")
        page.pause()
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
    except Exception as e:
        print(f"❌ Error en flujo de pago: {e}")
        page.screenshot(path="error_pago.png")
        print("🖱️ Activando modo manual - continúa tú desde aquí")
        page.pause()

    # Pausa final para ver el resultado
    print("✅ Fin del script.")
    page.pause()
    context.close()
    browser.close()


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
        page.pause()
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
    except: pass

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
    except: pass

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