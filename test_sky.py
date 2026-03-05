import os
import re
from datetime import datetime

from playwright._impl._errors import TargetClosedError
from playwright.sync_api import Playwright, expect, sync_playwright

from cli import aplicar_args, parse_args
import core.state as state
from core.browser_session import _crear_sesion_navegador
from core.helpers import (
    _capturar_estado_ui,
    _click_selector_visible,
    _activar_modo_manual,
    pausar_en_checkpoint,
)
from core.search_flow import (
    _cerrar_panel_login_si_abierto,
    _esperar_home_lista,
    _seleccionar_tipo_viaje,
    _seleccionar_ciudad,
    _seleccionar_fechas,
    _configurar_pasajeros_busqueda,
    _seleccionar_vuelo_y_tarifa,
    _saltar_extras,
)
from core.passenger_flow import (
    _rellenar_todos_los_pasajeros,
    _avanzar_a_checkout,
)
from core.payment_flows import PAYMENT_DISPATCH

# Evita ruido deprecado del runtime Node usado por Playwright (DEP0169).
_node_options = os.environ.get("NODE_OPTIONS", "").strip()
if "--no-deprecation" not in _node_options.split():
    os.environ["NODE_OPTIONS"] = f"{_node_options} --no-deprecation".strip()

# Configuración resuelta (defaults + CLI overrides)
state.CFG.update(aplicar_args(parse_args()))
state.EXPLORACION_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
state.EXPLORACION_DIR = os.path.join("screenshots_pruebas", f"exploracion_{state.EXPLORACION_RUN_ID}")


def run(playwright: Playwright) -> None:
    browser = None
    context = None
    session_cdp = False

    try:
        browser, context, page, session_cdp = _crear_sesion_navegador(playwright)
        try:
            print(f"--- 🚀 Iniciando Test [{state.CFG['market']}]: {state.CFG['origen']} -> {state.CFG['destino']} ---")
            print(f"    Medio de pago: {state.CFG['medio_pago']}")
            print(f"    Tipo viaje: {state.CFG['tipo_viaje']} | Pax: {state.CFG['pasajeros']}")
            if state.CFG["modo_exploracion"]:
                print(f"    Modo exploración: ON | Evidencia en {state.EXPLORACION_DIR}")
            page.goto(state.CFG["url"])
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

            _seleccionar_ciudad(page, "#origin-id", state.CFG["origen"])
            _seleccionar_ciudad(page, "#destination-id", state.CFG["destino"])

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

            if state.CFG["solo_exploracion"]:
                print("🧪 Solo exploración activo: flujo detenido tras búsqueda.")
                return

            # 🛑 Checkpoint: Después de búsqueda
            if pausar_en_checkpoint(page, "BUSQUEDA"):
                return

            # -------------------------------------------
            # 2. SELECCIÓN DE TARIFA
            # -------------------------------------------
            _seleccionar_vuelo_y_tarifa(page, "IDA")
            if state.CFG["tipo_viaje"] == "ROUND_TRIP":
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

            medio = state.CFG["medio_pago"]
            market = state.CFG["market"]
            print(f"--- Iniciando Pago: {medio} ({market}) ---")

            try:
                pagar_fn = PAYMENT_DISPATCH.get(market)
                if pagar_fn:
                    pagar_fn(page)
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
            espera_final_segundos = state.CFG.get("espera_final_segundos", 600)
            if espera_final_segundos > 0:
                minutos, segundos = divmod(espera_final_segundos, 60)
                espera_legible = f"{minutos}m {segundos}s" if segundos else f"{minutos} minutos"
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


try:
    with sync_playwright() as playwright:
        run(playwright)
except KeyboardInterrupt:
    print("\n\n👋 Ejecución interrumpida por el usuario (Ctrl+C). ¡Hasta la próxima!")
except Exception as error:
    print(f"\n❌ Error de ejecución: {error}")
