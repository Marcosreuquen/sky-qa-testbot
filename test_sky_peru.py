import re
from playwright.sync_api import Playwright, sync_playwright, expect

# ==========================================
# ⚙️ CONFIGURACIÓN DE LA PRUEBA (EDITABLE)
# ==========================================

# 1. RUTA Y TIEMPOS
URL_INICIAL = "https://initial-sale-qa.skyairline.com/es/peru"
TIEMPO_PAUSA_SEGURIDAD = 1500  # 1.5 segundos (en milisegundos)
VELOCIDAD_VISUAL = 500         # Slow_mo para ver qué hace

# 2. DATOS DEL VUELO
VUELO_ORIGEN = "Santiago"
VUELO_DESTINO = "La Serena"
DIAS_A_FUTURO = 16  # Selecciona el día 16 disponible (o el último si hay menos)

# 3. DATOS DEL PASAJERO
PASAJERO = {
    "nombre": "Erick",
    "apellido": "Test",
    "email": "erickr@email.co",
    "doc_tipo": "DNI",
    "doc_numero": "19999",
    "telefono": "11322323",
    "prefijo_pais": "51",
    "genero": "Masculino",
    "pais_emision": "Argentina",
    "fecha_nac": "21/04/1999" # Formato DD/MM/AAAA
}

# 4. DATOS DE PAGO (VISA TEST)
TARJETA = {
    "numero": "371204534881155",
    "fecha": "03/28", # MM/YY
    "cvv": "111"
}

# 5. CHECKPOINT (PUNTO DE PAUSA)
# Opciones: "BUSQUEDA", "SELECCION_TARIFA", "DATOS_PASAJERO", "CHECKOUT", "PAGO", None
# Usa None para ejecutar el flujo completo sin pausas intermedias
CHECKPOINT = None  # Cambia esto para detenerte en una sección específica

# ==========================================
# 🤖 INICIO DEL BOT
# ==========================================

def pausar_en_checkpoint(page, checkpoint_actual):
    """Pausa el bot si se alcanza el checkpoint configurado"""
    if CHECKPOINT == checkpoint_actual:
        print(f"\n⏸️  CHECKPOINT ALCANZADO: {checkpoint_actual}")
        print("🖱️  Puedes interactuar manualmente con la página.")
        print("▶️  Presiona 'Resume' en el inspector para continuar o cerrar.\n")
        page.pause()
        return True
    return False

def run(playwright: Playwright) -> None:
    # Configuración del navegador
    browser = playwright.chromium.launch(headless=False, slow_mo=VELOCIDAD_VISUAL)
    context = browser.new_context()
    page = context.new_page()

    print(f"--- 🚀 Iniciando Test: {VUELO_ORIGEN} -> {VUELO_DESTINO} ---")
    page.goto(URL_INICIAL)
    
    # -------------------------------------------
    # 1. BÚSQUEDA DE VUELO
    # -------------------------------------------
    page.locator("label").filter(has_text="Solo ida").click()
    
    # Origen
    page.locator("#origin-id").click()
    page.locator("#origin-id input").first.fill(VUELO_ORIGEN)
    page.get_by_text(VUELO_ORIGEN).first.click()

    # Destino
    page.locator("#destination-id").click()
    page.locator("#destination-id input").first.fill(VUELO_DESTINO)
    page.get_by_text(VUELO_DESTINO).first.click()

    # Selección de Fecha
    page.wait_for_timeout(1000)
    dias = page.locator('div.vc-day-content[aria-disabled="false"]')
    # Fix por si el calendario no abrió
    if not dias.first.is_visible():
        page.get_by_text("Ida", exact=True).first.click()
        page.wait_for_timeout(500)
    
    # Lógica de días
    if dias.count() > DIAS_A_FUTURO: 
        dias.nth(DIAS_A_FUTURO).click()
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

    btns = page.locator('button:has-text("Elegir vuelo")')
    if btns.count() == 0: btns = page.locator('[data-test^="is-itinerary-selectFlight"]')
    
    seleccionado = False
    for i in range(btns.count()):
        try:
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
    page.locator('[data-test="is-passengerForm-textFieldNamePax"] input').fill(PASAJERO["nombre"])
    page.locator('[data-test="is-passengerForm-textFieldLastname"] input').fill(PASAJERO["apellido"])
    
    # Fecha Nacimiento
    d, m, a = PASAJERO["fecha_nac"].split("/")
    cf = page.locator('[data-test="is-passengerForm-textFieldBirthdate"]')
    cf.locator("input").nth(0).fill(d)
    cf.locator("input").nth(1).fill(m)
    cf.locator("input").nth(2).fill(a)
    
    # Dropdowns
    page.locator('[data-test="is-thirdStep-dropdownGender"]').click()
    page.get_by_text(PASAJERO["genero"], exact=True).click()
    page.locator('[data-test="is-thirdStep-dropdownCountryIssue"]').click()
    page.get_by_text(PASAJERO["pais_emision"], exact=True).click()
    page.locator('[data-test="is-thirdStep-dropdownDocumentType"]').click()
    page.get_by_text(PASAJERO["doc_tipo"], exact=True).click()
    
    # Documento y Contacto
    page.locator('.card-passenger__passenger-form--fourth-row input').last.fill(PASAJERO["doc_numero"])
    page.locator('[data-test="is-passengerForm-textFieldEmail"] input').fill(PASAJERO["email"])
    page.locator('[data-test="is-passengerForm-textFieldPhone"] input').fill(PASAJERO["telefono"])

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
            page.get_by_text(f"{PASAJERO['nombre']}").last.click()
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
    expect(page).to_have_url(re.compile(".*checkout"), timeout=30000)

    # 🛑 Checkpoint: En el checkout
    if pausar_en_checkpoint(page, "CHECKOUT"):
        return

    print("--- Iniciando Pago Niubiz ---")
    page.wait_for_selector('text="Niubiz"', timeout=45000)
    
    niubiz_btn = page.locator("div").filter(has_text="Niubiz").last
    niubiz_btn.scroll_into_view_if_needed()
    niubiz_btn.click(force=True)
    
    print("Esperando animación del formulario...")
    page.wait_for_timeout(5000) 

    # Pre-llenado datos contacto (Ayuda a los Tabs)
    try:
        page.locator("div").filter(has_text=re.compile(r"^Nombre$")).last.locator("input.input").fill(PASAJERO["nombre"])
        page.locator("div").filter(has_text=re.compile(r"^Apellido$")).last.locator("input.input").fill(PASAJERO["apellido"])
        page.locator("div").filter(has_text="Correo electrónico").last.locator("input.input").fill(PASAJERO["email"])
    except: pass

    # BUSCAR TARJETA (Punto de Entrada)
    print("🕵️ Buscando campo Tarjeta (Esperando visualización)...")
    input_tarjeta = None
    
    for i in range(20):
        for frame in page.frames:
            try:
                candidato = frame.get_by_placeholder(re.compile(r"Número de Tarjeta", re.IGNORECASE))
                if candidato.count() > 0 and candidato.is_visible():
                    input_tarjeta = candidato
                    break
            except: continue
        if input_tarjeta: break
        if i % 5 == 0: print("   ... Buscando ...")
        page.wait_for_timeout(2000)

    if input_tarjeta:
        print("✅ Texto detectado. Validando habilitación...")
        try:
            # 1. Validación estricta
            input_tarjeta.wait_for(state="visible", timeout=30000)
            expect(input_tarjeta).to_be_editable(timeout=30000)
            
            # 2. Pausa Configurable (1.5s)
            print(f"⏳ Pausa de seguridad ({TIEMPO_PAUSA_SEGURIDAD}ms)...")
            page.wait_for_timeout(TIEMPO_PAUSA_SEGURIDAD) 
            
            # 3. Click y Escritura
            input_tarjeta.click(force=True)
            input_tarjeta.fill(TARJETA["numero"])
            
            # 4. Secuencia de Tabs
            print("🎹 Ejecutando Tabs: Tarjeta -> Nombre -> Apellido -> Fecha")
            page.keyboard.press("Tab") # Nombre
            page.keyboard.press("Tab") # Apellido
            page.keyboard.press("Tab") # Fecha
            
            # Fecha
            fecha_limpia = TARJETA["fecha"].replace("/", "")
            print(f"⌨️ Fecha: {fecha_limpia}")
            page.keyboard.type(fecha_limpia, delay=100)
            
            # CVV
            print("🎹 Tab a CVV...")
            page.keyboard.press("Tab")
            print(f"⌨️ CVV: {TARJETA['cvv']}")
            page.keyboard.type(TARJETA["cvv"], delay=100)

            # 🛑 Checkpoint: Después de llenar datos de pago
            if pausar_en_checkpoint(page, "PAGO"):
                return

            # -------------------------------------------
            # 5. FINALIZAR COMPRA
            # -------------------------------------------
            print("--- Finalizando Compra ---")
            
            # A. Checkbox "He leído y acepto"
            print("✅ Buscando checkbox (click quirurgico en .checkbox_icon)...")
            # Usamos la clase exacta que me pasaste para no clickear el link
            checkbox_exacto = page.locator(".checkbox_icon").last
            checkbox_exacto.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            checkbox_exacto.click()
            
            # B. Botón "Ir a pagar"
            print("🚀 Buscando botón 'Ir a pagar'...")
            btn_pagar = page.locator("button").filter(has_text="Ir a pagar")
            # Esperamos a que esté habilitado (a veces tarda un segundo tras el checkbox)
            btn_pagar.wait_for(state="visible", timeout=5000)
            btn_pagar.click()
            
            print("🎉 ¡CLICK EN PAGAR REALIZADO!")

        except Exception as e:
            print(f"❌ Error durante la interacción final: {e}")
            page.screenshot(path="error_interaccion.png")
    else:
        print("❌ Error: Nunca apareció el texto 'Número de Tarjeta'.")

    # Pausa final para ver el resultado
    print("✅ Fin del script.")
    page.pause()
    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)