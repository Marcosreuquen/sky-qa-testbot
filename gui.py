import json
import queue
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from config import (
    CANTIDAD_ADULTOS,
    CANTIDAD_INFANTES,
    CANTIDAD_NINOS,
    CHECKPOINT,
    DIAS_A_FUTURO,
    DIAS_RETORNO_DESDE_IDA,
    ESPERA_FINAL_SEGUNDOS,
    HOME_MARKET,
    PASAJERO,
    TARJETA_POR_MARKET,
    TIEMPO_PAUSA_SEGURIDAD,
    TIPO_VIAJE,
    VELOCIDAD_VISUAL,
    VUELO_DESTINO,
    VUELO_ORIGEN,
)

PROJECT_ROOT = Path(__file__).resolve().parent
PYTHON_EXEC = sys.executable

NO_CHECKPOINT = "NINGUNO"
CDP_URL_DEFAULT = "http://127.0.0.1:9222"
CDP_START_TIMEOUT_SEGUNDOS = 12
GUI_SETTINGS_PATH = PROJECT_ROOT / ".sky_gui_settings.json"
MARKET_LABEL_TO_CODE = {
    "Perú": "PE",
    "Argentina": "AR",
    "Chile": "CL",
    "Brasil": "BR",
}
MARKET_CODE_TO_LABEL = {v: k for k, v in MARKET_LABEL_TO_CODE.items()}

TRIP_LABEL_TO_CODE = {
    "Solo ida": "ONE_WAY",
    "Ida y vuelta": "ROUND_TRIP",
}
TRIP_CODE_TO_LABEL = {v: k for k, v in TRIP_LABEL_TO_CODE.items()}

CHECKPOINT_LABEL_TO_CODE = {
    "Ninguno (flujo completo)": NO_CHECKPOINT,
    "Pausar después de búsqueda": "BUSQUEDA",
    "Pausar después de selección de tarifa": "SELECCION_TARIFA",
    "Pausar después de datos del pasajero": "DATOS_PASAJERO",
    "Pausar en checkout": "CHECKOUT",
    "Pausar en pago": "PAGO",
}
CHECKPOINT_CODE_TO_LABEL = {v: k for k, v in CHECKPOINT_LABEL_TO_CODE.items()}

DEFAULT_PRESET_NAME = "Inicial: Solo ida, Perú, 1 adulto"
CUSTOM_PRESET_NAME = "Personalizado"
DEFAULT_PRESETS = {
    DEFAULT_PRESET_NAME: {
        "market": "Perú",
        "tipo_viaje": "Solo ida",
        "adultos": 1,
        "ninos": 0,
        "infantes": 0,
        "checkpoint": "Ninguno (flujo completo)",
        "usar_chrome_existente": True,
    },
    CUSTOM_PRESET_NAME: {},
    "1) Solo ida, Perú, 1 adulto (checkout)": {
        "market": "Perú",
        "tipo_viaje": "Solo ida",
        "adultos": 1,
        "ninos": 0,
        "infantes": 0,
        "checkpoint": "Pausar en checkout",
    },
    "2) Ida y vuelta, Perú, 1 adulto (checkout)": {
        "market": "Perú",
        "tipo_viaje": "Ida y vuelta",
        "adultos": 1,
        "ninos": 0,
        "infantes": 0,
        "checkpoint": "Pausar en checkout",
    },
    "3) Solo ida, Perú, 2 adultos, 1 niño (checkout)": {
        "market": "Perú",
        "tipo_viaje": "Solo ida",
        "adultos": 2,
        "ninos": 1,
        "infantes": 0,
        "checkpoint": "Pausar en checkout",
    },
    "4) Ida y vuelta, Perú, 2 adultos, 1 infante (checkout)": {
        "market": "Perú",
        "tipo_viaje": "Ida y vuelta",
        "adultos": 2,
        "ninos": 0,
        "infantes": 1,
        "checkpoint": "Pausar en checkout",
    },
    "5) Exploración UI, Perú, ida y vuelta (checkout)": {
        "market": "Perú",
        "tipo_viaje": "Ida y vuelta",
        "adultos": 1,
        "ninos": 0,
        "infantes": 0,
        "checkpoint": "Pausar en checkout",
        "modo_exploracion": True,
    },
}


class SkyBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sky QA TestBot - Interfaz Visual")
        self.root.geometry("1180x860")
        self.root.minsize(980, 700)

        self.process = None
        self.queue = queue.Queue()
        self.cdp_iniciado_automaticamente = False
        self._suspend_preset_tracking = False

        self._crear_variables()
        self.presets = self._presets_por_defecto()
        self._cargar_settings()
        self._construir_ui()
        self._registrar_tracking_cambios_preset()
        self._inicializar_scroll_global()
        self._procesar_cola()

        self.root.protocol("WM_DELETE_WINDOW", self._al_cerrar_ventana)

    def _crear_variables(self):
        checkpoint_default = "Ninguno (flujo completo)"

        self.preset_var = tk.StringVar(value=DEFAULT_PRESET_NAME)
        self.market_var = tk.StringVar(value="Perú")
        self.tipo_viaje_var = tk.StringVar(value="Solo ida")
        self.origen_var = tk.StringVar(value=VUELO_ORIGEN)
        self.destino_var = tk.StringVar(value=VUELO_DESTINO)
        self.dias_var = tk.IntVar(value=DIAS_A_FUTURO)
        self.dias_retorno_var = tk.IntVar(value=DIAS_RETORNO_DESDE_IDA)
        self.adultos_var = tk.IntVar(value=1)
        self.ninos_var = tk.IntVar(value=0)
        self.infantes_var = tk.IntVar(value=0)
        self.checkpoint_var = tk.StringVar(value=checkpoint_default)

        self.pausa_var = tk.IntVar(value=TIEMPO_PAUSA_SEGURIDAD)
        self.slow_mo_var = tk.IntVar(value=VELOCIDAD_VISUAL)
        self.espera_final_var = tk.IntVar(value=ESPERA_FINAL_SEGUNDOS)
        self.cdp_url_var = tk.StringVar(value=CDP_URL_DEFAULT)

        self.headless_var = tk.BooleanVar(value=False)
        self.usar_chrome_existente_var = tk.BooleanVar(value=True)
        self.modo_exploracion_var = tk.BooleanVar(value=False)
        self.solo_exploracion_var = tk.BooleanVar(value=False)
        self.log_limpio_var = tk.BooleanVar(value=True)

        # Overrides opcionales de pasajero/pagador
        self.nombre_override_var = tk.StringVar(value=PASAJERO.get("nombre", ""))
        self.apellido_override_var = tk.StringVar(value=PASAJERO.get("apellido", ""))
        self.email_override_var = tk.StringVar(value=PASAJERO.get("email", ""))
        self.doc_tipo_override_var = tk.StringVar(value=PASAJERO.get("doc_tipo", ""))
        self.doc_numero_override_var = tk.StringVar(value=PASAJERO.get("doc_numero", ""))
        self.telefono_override_var = tk.StringVar(value=PASAJERO.get("telefono", ""))
        self.prefijo_pais_override_var = tk.StringVar(value=PASAJERO.get("prefijo_pais", ""))
        self.genero_override_var = tk.StringVar(value=PASAJERO.get("genero", ""))
        self.pais_emision_override_var = tk.StringVar(value=PASAJERO.get("pais_emision", ""))
        self.fecha_nac_override_var = tk.StringVar(value=PASAJERO.get("fecha_nac", ""))

        # Overrides opcionales de tarjeta
        market_code_default = self._market_code_from_label(self.market_var.get())
        tarjeta_default = TARJETA_POR_MARKET.get(market_code_default, {})
        self.tarjeta_numero_override_var = tk.StringVar(value=tarjeta_default.get("numero", ""))
        self.tarjeta_fecha_override_var = tk.StringVar(value=tarjeta_default.get("fecha", ""))
        self.tarjeta_cvv_override_var = tk.StringVar(value=tarjeta_default.get("cvv", ""))

        self.status_var = tk.StringVar(value="Listo para ejecutar")

    def _presets_por_defecto(self):
        presets = {}
        for nombre, valores in DEFAULT_PRESETS.items():
            if isinstance(valores, dict):
                presets[nombre] = dict(valores)
        if CUSTOM_PRESET_NAME not in presets:
            presets[CUSTOM_PRESET_NAME] = {}
        return presets

    def _serializar_presets(self):
        data = {}
        for nombre, valores in self.presets.items():
            if nombre == CUSTOM_PRESET_NAME:
                continue
            if nombre == DEFAULT_PRESET_NAME:
                continue
            if isinstance(valores, dict):
                data[nombre] = dict(valores)
        return data

    def _cargar_presets_desde_data(self, presets_data):
        presets = self._presets_por_defecto()
        if isinstance(presets_data, dict):
            # Si existen presets guardados, respeta exactamente ese set editable.
            base = {
                DEFAULT_PRESET_NAME: dict(DEFAULT_PRESETS.get(DEFAULT_PRESET_NAME, {})),
                CUSTOM_PRESET_NAME: {},
            }
            for nombre, valores in presets_data.items():
                if not isinstance(nombre, str) or not isinstance(valores, dict):
                    continue
                nombre = nombre.strip()
                if not nombre or nombre in {DEFAULT_PRESET_NAME, CUSTOM_PRESET_NAME}:
                    continue
                base[nombre] = dict(valores)
            self.presets = base
            return
        self.presets = presets

    def _estado_actual_para_preset(self):
        return {
            "market": self.market_var.get(),
            "tipo_viaje": self.tipo_viaje_var.get(),
            "origen": self.origen_var.get(),
            "destino": self.destino_var.get(),
            "dias": int(self.dias_var.get()),
            "dias_retorno": int(self.dias_retorno_var.get()),
            "adultos": int(self.adultos_var.get()),
            "ninos": int(self.ninos_var.get()),
            "infantes": int(self.infantes_var.get()),
            "checkpoint": self.checkpoint_var.get(),
            "pausa": int(self.pausa_var.get()),
            "slow_mo": int(self.slow_mo_var.get()),
            "espera_final": int(self.espera_final_var.get()),
            "cdp_url": self.cdp_url_var.get(),
            "headless": bool(self.headless_var.get()),
            "usar_chrome_existente": bool(self.usar_chrome_existente_var.get()),
            "modo_exploracion": bool(self.modo_exploracion_var.get()),
            "solo_exploracion": bool(self.solo_exploracion_var.get()),
            "log_limpio": bool(self.log_limpio_var.get()),
            "nombre_override": self.nombre_override_var.get(),
            "apellido_override": self.apellido_override_var.get(),
            "email_override": self.email_override_var.get(),
            "doc_tipo_override": self.doc_tipo_override_var.get(),
            "doc_numero_override": self.doc_numero_override_var.get(),
            "telefono_override": self.telefono_override_var.get(),
            "prefijo_pais_override": self.prefijo_pais_override_var.get(),
            "genero_override": self.genero_override_var.get(),
            "pais_emision_override": self.pais_emision_override_var.get(),
            "fecha_nac_override": self.fecha_nac_override_var.get(),
            "tarjeta_numero_override": self.tarjeta_numero_override_var.get(),
            "tarjeta_fecha_override": self.tarjeta_fecha_override_var.get(),
            "tarjeta_cvv_override": self.tarjeta_cvv_override_var.get(),
        }

    def _normalizar_preset_comparable(self, data):
        base = dict(DEFAULT_PRESETS.get(DEFAULT_PRESET_NAME, {}))
        if isinstance(data, dict):
            base.update(data)
        keys = self._estado_actual_para_preset().keys()
        return {k: base.get(k) for k in keys}

    def _registrar_tracking_cambios_preset(self):
        vars_a_trackear = [
            self.market_var,
            self.tipo_viaje_var,
            self.origen_var,
            self.destino_var,
            self.dias_var,
            self.dias_retorno_var,
            self.adultos_var,
            self.ninos_var,
            self.infantes_var,
            self.checkpoint_var,
            self.pausa_var,
            self.slow_mo_var,
            self.espera_final_var,
            self.cdp_url_var,
            self.headless_var,
            self.usar_chrome_existente_var,
            self.modo_exploracion_var,
            self.solo_exploracion_var,
            self.log_limpio_var,
            self.nombre_override_var,
            self.apellido_override_var,
            self.email_override_var,
            self.doc_tipo_override_var,
            self.doc_numero_override_var,
            self.telefono_override_var,
            self.prefijo_pais_override_var,
            self.genero_override_var,
            self.pais_emision_override_var,
            self.fecha_nac_override_var,
            self.tarjeta_numero_override_var,
            self.tarjeta_fecha_override_var,
            self.tarjeta_cvv_override_var,
        ]
        for variable in vars_a_trackear:
            variable.trace_add("write", self._on_cambio_config_para_preset)

    def _on_cambio_config_para_preset(self, *_args):
        if self._suspend_preset_tracking:
            return
        nombre = self.preset_var.get()
        if not nombre or nombre == CUSTOM_PRESET_NAME:
            return
        preset = self.presets.get(nombre)
        if not isinstance(preset, dict):
            return

        actual = self._normalizar_preset_comparable(self._estado_actual_para_preset())
        esperado = self._normalizar_preset_comparable(preset)
        if actual == esperado:
            return

        self._suspend_preset_tracking = True
        try:
            self.preset_var.set(CUSTOM_PRESET_NAME)
        finally:
            self._suspend_preset_tracking = False

    def _actualizar_combo_presets(self):
        if hasattr(self, "preset_combo") and self.preset_combo is not None:
            self.preset_combo.configure(values=list(self.presets.keys()))
        if self.preset_var.get() not in self.presets:
            self.preset_var.set(CUSTOM_PRESET_NAME)

    def _nombre_preset_valido(self, nombre):
        valor = (nombre or "").strip()
        if not valor:
            return None
        if valor == DEFAULT_PRESET_NAME:
            messagebox.showwarning("Caso inmutable", f"'{DEFAULT_PRESET_NAME}' es inmutable.")
            return None
        if valor == CUSTOM_PRESET_NAME:
            messagebox.showwarning("Nombre reservado", f"'{CUSTOM_PRESET_NAME}' está reservado.")
            return None
        return valor

    def _guardar_preset(self):
        actual = self.preset_var.get()
        sugerido = "" if actual in {CUSTOM_PRESET_NAME, DEFAULT_PRESET_NAME} else actual
        nombre = simpledialog.askstring("Guardar caso", "Nombre del caso de uso:", initialvalue=sugerido, parent=self.root)
        nombre = self._nombre_preset_valido(nombre)
        if not nombre:
            return

        if nombre in self.presets and nombre != actual:
            reemplazar = messagebox.askyesno("Reemplazar caso", f"Ya existe '{nombre}'. ¿Quieres reemplazarlo?")
            if not reemplazar:
                return

        self.presets[nombre] = self._estado_actual_para_preset()
        self._actualizar_combo_presets()
        self._suspend_preset_tracking = True
        try:
            self.preset_var.set(nombre)
        finally:
            self._suspend_preset_tracking = False
        self.status_var.set(f"Caso guardado: {nombre}")
        self._guardar_settings()

    def _renombrar_preset(self):
        actual = self.preset_var.get()
        if actual in {DEFAULT_PRESET_NAME, CUSTOM_PRESET_NAME}:
            messagebox.showwarning("Renombrar caso", "Selecciona un caso guardado para renombrar.")
            return
        if actual not in self.presets:
            messagebox.showwarning("Renombrar caso", "El caso seleccionado no existe.")
            return

        nuevo = simpledialog.askstring("Renombrar caso", "Nuevo nombre:", initialvalue=actual, parent=self.root)
        nuevo = self._nombre_preset_valido(nuevo)
        if not nuevo or nuevo == actual:
            return

        if nuevo in self.presets:
            reemplazar = messagebox.askyesno("Reemplazar caso", f"Ya existe '{nuevo}'. ¿Quieres reemplazarlo?")
            if not reemplazar:
                return

        nuevos = {}
        for nombre, valores in self.presets.items():
            if nombre == actual:
                continue
            if nombre == nuevo:
                continue
            nuevos[nombre] = valores
        nuevos[nuevo] = self.presets[actual]
        self.presets = nuevos
        self._actualizar_combo_presets()
        self._suspend_preset_tracking = True
        try:
            self.preset_var.set(nuevo)
        finally:
            self._suspend_preset_tracking = False
        self.status_var.set(f"Caso renombrado a: {nuevo}")
        self._guardar_settings()

    def _eliminar_preset(self):
        actual = self.preset_var.get()
        if actual in {DEFAULT_PRESET_NAME, CUSTOM_PRESET_NAME}:
            messagebox.showwarning("Eliminar caso", "Selecciona un caso guardado para eliminar.")
            return
        if actual not in self.presets:
            messagebox.showwarning("Eliminar caso", "El caso seleccionado no existe.")
            return

        confirmar = messagebox.askyesno("Eliminar caso", f"¿Eliminar el caso '{actual}'?")
        if not confirmar:
            return

        self.presets.pop(actual, None)
        self._actualizar_combo_presets()
        self._suspend_preset_tracking = True
        try:
            self.preset_var.set(CUSTOM_PRESET_NAME)
        finally:
            self._suspend_preset_tracking = False
        self.status_var.set(f"Caso eliminado: {actual}")
        self._guardar_settings()

    def _construir_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)
        self.scroll_canvas, sections_root = self._crear_area_scrollable(main)

        casos_section = self._crear_seccion_desplegable(sections_root, "Caso de uso", expanded=True)
        casos_header = ttk.Frame(casos_section)
        casos_header.pack(fill=tk.X)
        self.preset_combo = ttk.Combobox(
            casos_header,
            textvariable=self.preset_var,
            values=list(self.presets.keys()),
            state="readonly",
            width=34,
        )
        self.preset_combo.pack(side=tk.LEFT, padx=(0, 8), pady=2)
        self.preset_combo.bind("<MouseWheel>", self._on_combo_scroll_protegido, add="+")
        self.preset_combo.bind("<Button-4>", self._on_combo_scroll_protegido, add="+")
        self.preset_combo.bind("<Button-5>", self._on_combo_scroll_protegido, add="+")
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_combo_selected, add="+")
        ttk.Button(casos_header, text="Restablecer", command=self._restablecer).pack(side=tk.LEFT)
        ttk.Button(casos_header, text="Guardar caso", command=self._guardar_preset).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Button(casos_header, text="Renombrar", command=self._renombrar_preset).pack(side=tk.LEFT, padx=4)
        ttk.Button(casos_header, text="Eliminar", command=self._eliminar_preset).pack(side=tk.LEFT, padx=4)
        ayuda_tooltips = ttk.Label(
            casos_header,
            text="ⓘ Hover sobre controles para ver ayuda",
        )
        ayuda_tooltips.pack(side=tk.RIGHT)
        self._add_tooltip(
            ayuda_tooltips,
            "Pasa el cursor sobre opciones clave para ver una explicación rápida.",
        )

        principal_section = self._crear_seccion_desplegable(sections_root, "Configuración principal", expanded=True)
        principal_layout = ttk.Frame(principal_section)
        principal_layout.pack(fill=tk.X)
        principal_layout.grid_columnconfigure(0, weight=1, uniform="principal")
        principal_layout.grid_columnconfigure(1, weight=1, uniform="principal")

        flujo = ttk.LabelFrame(principal_layout, text="Flujo")
        flujo.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        combo_market = self._add_combo(flujo, "País", self.market_var, list(MARKET_LABEL_TO_CODE.keys()), row=0)
        combo_tipo_viaje = self._add_combo(flujo, "Tipo de viaje", self.tipo_viaje_var, list(TRIP_LABEL_TO_CODE.keys()), row=1)
        combo_checkpoint = self._add_combo(
            flujo,
            "Checkpoint",
            self.checkpoint_var,
            list(CHECKPOINT_LABEL_TO_CODE.keys()),
            row=2,
        )
        tooltip_market = "País del sitio y medio de pago a usar (Perú, Argentina, Chile o Brasil)."
        tooltip_tipo_viaje = "Solo ida o ida y vuelta."
        tooltip_checkpoint = "Punto donde el flujo se pausa para inspección manual."
        self._add_tooltip(combo_market, tooltip_market)
        self._add_tooltip(combo_tipo_viaje, tooltip_tipo_viaje)
        self._add_tooltip(combo_checkpoint, tooltip_checkpoint)
        self._add_help_icon_grid(flujo, row=0, column=2, tooltip_text=tooltip_market)
        self._add_help_icon_grid(flujo, row=1, column=2, tooltip_text=tooltip_tipo_viaje)
        self._add_help_icon_grid(flujo, row=2, column=2, tooltip_text=tooltip_checkpoint)

        viaje = ttk.LabelFrame(principal_layout, text="Vuelo y pasajeros")
        viaje.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._add_entry(viaje, "Origen", self.origen_var, row=0)
        self._add_entry(viaje, "Destino", self.destino_var, row=1)
        self._add_spin(viaje, "Días a futuro", self.dias_var, 0, 365, row=2)
        self._add_spin(viaje, "Días retorno", self.dias_retorno_var, 1, 60, row=3)
        self._add_spin(viaje, "Adultos", self.adultos_var, 1, 9, row=4)
        self._add_spin(viaje, "Niños", self.ninos_var, 0, 9, row=5)
        self._add_spin(viaje, "Infantes", self.infantes_var, 0, 9, row=6)

        opcional_section = self._crear_seccion_desplegable(
            sections_root,
            "Datos opcionales de pasajero y tarjeta",
            expanded=False,
            subtitle="Se aplican siempre (puedes editar cualquier campo)",
        )
        ttk.Label(
            opcional_section,
            text="Estos valores ya vienen precargados y el bot los usará en cada ejecución.",
        ).pack(anchor="w", pady=(0, 6))

        opc_layout = ttk.Frame(opcional_section)
        opc_layout.pack(fill=tk.X)
        opc_layout.grid_columnconfigure(0, weight=1, uniform="opc")
        opc_layout.grid_columnconfigure(1, weight=1, uniform="opc")

        pax_frame = ttk.LabelFrame(opc_layout, text="Pasajero/Pagador")
        pax_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._add_entry(pax_frame, "Nombre", self.nombre_override_var, row=0)
        self._add_entry(pax_frame, "Apellido", self.apellido_override_var, row=1)
        self._add_entry(pax_frame, "Email", self.email_override_var, row=2)
        self._add_entry(pax_frame, "Doc tipo", self.doc_tipo_override_var, row=3)
        self._add_entry(pax_frame, "Doc número", self.doc_numero_override_var, row=4)
        self._add_entry(pax_frame, "Teléfono", self.telefono_override_var, row=5)
        self._add_entry(pax_frame, "Prefijo país", self.prefijo_pais_override_var, row=6)
        self._add_combo(pax_frame, "Género", self.genero_override_var, ["", "Masculino", "Femenino"], row=7)
        self._add_entry(pax_frame, "País emisión", self.pais_emision_override_var, row=8)
        self._add_entry(pax_frame, "Fecha nac (DD/MM/AAAA)", self.fecha_nac_override_var, row=9)

        tarjeta_frame = ttk.LabelFrame(opc_layout, text="Tarjeta")
        tarjeta_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._add_entry(tarjeta_frame, "Número", self.tarjeta_numero_override_var, row=0)
        self._add_entry(tarjeta_frame, "Fecha (MM/YY)", self.tarjeta_fecha_override_var, row=1)
        self._add_entry(tarjeta_frame, "CVV", self.tarjeta_cvv_override_var, row=2)
        ttk.Label(
            tarjeta_frame,
            text="Si no los cambias, se usan tal como están cargados.",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 8))

        avanzado_section = self._crear_seccion_desplegable(
            sections_root,
            "Configuración avanzada",
            expanded=False,
            subtitle="Debug y opciones técnicas",
        )
        advanced_grid = ttk.Frame(avanzado_section)
        advanced_grid.pack(fill=tk.X)
        advanced_grid.grid_columnconfigure(0, weight=1, uniform="adv")
        advanced_grid.grid_columnconfigure(1, weight=1, uniform="adv")

        ejecucion = ttk.LabelFrame(advanced_grid, text="Ejecución")
        ejecucion.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ck_usar_chrome = ttk.Checkbutton(
            ejecucion,
            text="Usar Chrome abierto (recomendado)",
            variable=self.usar_chrome_existente_var,
        )
        ck_usar_chrome.grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2)
        )
        ck_headless = ttk.Checkbutton(ejecucion, text="Headless", variable=self.headless_var)
        ck_headless.grid(
            row=1, column=0, sticky="w", padx=8, pady=2
        )
        ck_modo_exploracion = ttk.Checkbutton(
            ejecucion,
            text="Modo exploración (capturas)",
            variable=self.modo_exploracion_var,
        )
        ck_modo_exploracion.grid(
            row=2, column=0, columnspan=2, sticky="w", padx=8, pady=2
        )
        ck_solo_exploracion = ttk.Checkbutton(
            ejecucion,
            text="Solo exploración (sin pago)",
            variable=self.solo_exploracion_var,
        )
        ck_solo_exploracion.grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(2, 8))
        ck_log_limpio = ttk.Checkbutton(
            ejecucion,
            text="Modo log limpio (recomendado)",
            variable=self.log_limpio_var,
        )
        ck_log_limpio.grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8))

        tecnico = ttk.LabelFrame(advanced_grid, text="Conexión y tiempos")
        tecnico.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        lbl_cdp = ttk.Label(tecnico, text="Conexión Chrome (CDP URL)")
        lbl_cdp.grid(row=0, column=0, sticky="w", padx=8, pady=5)
        entry_cdp = ttk.Entry(tecnico, textvariable=self.cdp_url_var, width=24)
        entry_cdp.grid(row=0, column=1, sticky="ew", padx=8, pady=5)
        btn_preparar_cdp = ttk.Button(
            tecnico,
            text="Abrir/Preparar Chrome para automatización",
            command=self._iniciar_chrome_cdp_manual,
        )
        btn_preparar_cdp.grid(row=1, column=0, sticky="w", padx=8, pady=(2, 4))
        self._add_spin(tecnico, "Pausa seguridad (ms)", self.pausa_var, 0, 30000, row=2)
        self._add_spin(tecnico, "Slow mo (ms)", self.slow_mo_var, 0, 5000, row=3)
        self._add_spin(tecnico, "Espera final (seg)", self.espera_final_var, 0, 3600, row=4)

        tooltip_modo_exploracion = "Captura screenshots y reportes de UI por etapa para debugging."
        tooltip_solo_exploracion = "Detiene el flujo tras la búsqueda: no selecciona tarifa ni llega al pago."
        tooltip_log_limpio = "Muestra solo eventos relevantes y oculta líneas técnicas/ruido del runtime."
        tooltip_chrome = "Conecta al Chrome abierto. Si Chrome se inicia automáticamente en esta ejecución, usa la primera pestaña."
        tooltip_headless = "Ejecuta sin mostrar ventana de navegador."
        tooltip_cdp = "Dirección para conectarse al Chrome abierto. Normalmente: http://127.0.0.1:9222"
        tooltip_preparar_cdp = "Abre o prepara Chrome con debugging remoto para automatización por CDP."

        self._add_tooltip(ck_modo_exploracion, tooltip_modo_exploracion)
        self._add_tooltip(ck_solo_exploracion, tooltip_solo_exploracion)
        self._add_tooltip(ck_log_limpio, tooltip_log_limpio)
        self._add_tooltip(ck_usar_chrome, tooltip_chrome)
        self._add_tooltip(ck_headless, tooltip_headless)
        self._add_tooltip(lbl_cdp, tooltip_cdp)
        self._add_tooltip(entry_cdp, "No cambiar salvo que uses otro puerto o host.")
        self._add_tooltip(btn_preparar_cdp, tooltip_preparar_cdp)

        self._add_help_icon_grid(ejecucion, row=0, column=2, tooltip_text=tooltip_chrome, pady=(6, 2))
        self._add_help_icon_grid(ejecucion, row=1, column=2, tooltip_text=tooltip_headless, pady=2)
        self._add_help_icon_grid(ejecucion, row=2, column=2, tooltip_text=tooltip_modo_exploracion, pady=2)
        self._add_help_icon_grid(ejecucion, row=3, column=2, tooltip_text=tooltip_solo_exploracion, pady=(2, 8))
        self._add_help_icon_grid(ejecucion, row=4, column=2, tooltip_text=tooltip_log_limpio, pady=(0, 8))
        self._add_help_icon_grid(tecnico, row=0, column=2, tooltip_text=tooltip_cdp, pady=5)
        self._add_help_icon_grid(tecnico, row=1, column=2, tooltip_text=tooltip_preparar_cdp, pady=(2, 4))

        self.acciones_frame = ttk.Frame(main)
        self.acciones_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(self.acciones_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        self.run_button = ttk.Button(
            self.acciones_frame,
            text="Ejecutar",
            command=self._iniciar_ejecucion,
            style="Primary.TButton",
        )
        self.run_button.pack(side=tk.RIGHT, padx=(8, 0))
        self.stop_button = ttk.Button(self.acciones_frame, text="Detener", command=self._detener_ejecucion, state=tk.DISABLED)
        self.stop_button.pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(self.acciones_frame, text="Limpiar log", command=self._limpiar_log).pack(side=tk.RIGHT, padx=(8, 0))

        log_frame = ttk.LabelFrame(main, text="Salida")
        log_frame.pack(fill=tk.X, expand=False)
        self.log_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            height=6,
            bg="#111827",
            fg="#f8fafc",
            insertbackground="#f8fafc",
            selectbackground="#334155",
            relief="flat",
            padx=8,
            pady=8,
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scroll.set)

    def _crear_area_scrollable(self, parent):
        wrap = ttk.Frame(parent)
        wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        canvas = tk.Canvas(
            wrap,
            highlightthickness=0,
            borderwidth=0,
            bg=self.root.cget("bg"),
        )
        scrollbar = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        content = ttk.Frame(canvas)
        window_id = canvas.create_window((0, 0), window=content, anchor="nw")
        self._scroll_window_id = window_id

        content.bind("<Configure>", self._on_scroll_content_configure)
        canvas.bind("<Configure>", self._on_scroll_canvas_configure)

        return canvas, content

    def _on_scroll_content_configure(self, _event=None):
        self._actualizar_scrollregion()

    def _on_scroll_canvas_configure(self, event):
        if not hasattr(self, "scroll_canvas") or self.scroll_canvas is None:
            return
        if hasattr(self, "_scroll_window_id"):
            self.scroll_canvas.itemconfigure(self._scroll_window_id, width=event.width)
            self.scroll_canvas.coords(self._scroll_window_id, 0, 0)
        self._actualizar_scrollregion()

    def _actualizar_scrollregion(self):
        if not hasattr(self, "scroll_canvas") or self.scroll_canvas is None:
            return

        self.root.update_idletasks()
        canvas = self.scroll_canvas
        bbox = canvas.bbox("all")
        if not bbox:
            return

        x1, y1, x2, y2 = bbox
        canvas_w = max(1, canvas.winfo_width())
        canvas_h = max(1, canvas.winfo_height())
        content_w = max(1, x2 - x1)
        content_h = max(1, y2 - y1)

        region_w = max(content_w, canvas_w)
        region_h = max(content_h, canvas_h)
        canvas.configure(scrollregion=(0, 0, region_w, region_h))

        # Si el contenido no supera la altura visible, evita desplazamiento fantasma.
        if content_h <= canvas_h:
            canvas.yview_moveto(0.0)

    def _crear_seccion_desplegable(self, parent, title, expanded=True, subtitle=""):
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill=tk.X, pady=(0, 10))

        state = {"expanded": expanded}
        header = ttk.Frame(wrapper)
        header.pack(fill=tk.X)
        title_var = tk.StringVar()

        def refresh():
            prefijo = "▼" if state["expanded"] else "▶"
            title_var.set(f"{prefijo} {title}")
            if state["expanded"]:
                body.pack(fill=tk.X, pady=(6, 0))
            else:
                body.pack_forget()
            self.root.after_idle(self._actualizar_scrollregion)

        def toggle():
            state["expanded"] = not state["expanded"]
            refresh()

        ttk.Button(header, textvariable=title_var, style="Section.TButton", command=toggle).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        if subtitle:
            ttk.Label(header, text=subtitle).pack(side=tk.LEFT, padx=(8, 0))

        body = ttk.Frame(wrapper)
        refresh()
        return body

    def _add_help_icon_grid(self, parent, row, column, tooltip_text, pady=5):
        icon = ttk.Label(parent, text="ⓘ", style="HintIcon.TLabel")
        icon.grid(row=row, column=column, sticky="w", padx=(6, 0), pady=pady)
        self._add_tooltip(icon, tooltip_text)
        return icon

    def _inicializar_scroll_global(self):
        self.root.bind_all("<MouseWheel>", self._on_scroll_formulario, add="+")
        self.root.bind_all("<Button-4>", self._on_scroll_formulario, add="+")
        self.root.bind_all("<Button-5>", self._on_scroll_formulario, add="+")

    def _widget_bajo_cursor(self):
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        return self.root.winfo_containing(x, y)

    def _es_descendiente(self, widget, ancestor):
        current = widget
        while current is not None:
            if current == ancestor:
                return True
            try:
                parent_name = current.winfo_parent()
            except Exception:
                return False
            if not parent_name:
                return False
            try:
                current = current.nametowidget(parent_name)
            except Exception:
                return False
        return False

    def _evento_en_formulario_scrollable(self):
        if not hasattr(self, "scroll_canvas") or self.scroll_canvas is None:
            return False
        widget = self._widget_bajo_cursor()
        if widget is None:
            return False
        return self._es_descendiente(widget, self.scroll_canvas)

    def _on_scroll_formulario(self, event):
        if not self._evento_en_formulario_scrollable():
            return
        self._scroll_canvas_por_evento(event)

    def _scroll_canvas_por_evento(self, event):
        if not hasattr(self, "scroll_canvas") or self.scroll_canvas is None:
            return
        bbox = self.scroll_canvas.bbox("all")
        if bbox:
            _, y1, _, y2 = bbox
            content_h = max(1, y2 - y1)
            canvas_h = max(1, self.scroll_canvas.winfo_height())
            if content_h <= canvas_h:
                self.scroll_canvas.yview_moveto(0.0)
                return
        if getattr(event, "num", None) == 4:
            self.scroll_canvas.yview_scroll(-3, "units")
            return
        if getattr(event, "num", None) == 5:
            self.scroll_canvas.yview_scroll(3, "units")
            return

        delta = getattr(event, "delta", 0)
        if delta == 0:
            return
        if sys.platform == "darwin":
            steps = -1 if delta > 0 else 1
        else:
            steps = int(-(delta / 120))
        if steps == 0:
            steps = -1 if delta > 0 else 1
        self.scroll_canvas.yview_scroll(steps, "units")

    def _on_combo_scroll_protegido(self, event):
        if self._evento_en_formulario_scrollable():
            self._scroll_canvas_por_evento(event)
        return "break"

    def _add_tooltip(self, widget, text, delay_ms=500):
        if not text:
            return
        state = {"after_id": None, "win": None}
        try:
            widget.configure(cursor="question_arrow")
        except Exception:
            pass

        def _hide(_event=None):
            if state["after_id"]:
                try:
                    widget.after_cancel(state["after_id"])
                except Exception:
                    pass
                state["after_id"] = None
            if state["win"] is not None:
                try:
                    state["win"].destroy()
                except Exception:
                    pass
                state["win"] = None

        def _show():
            if state["win"] is not None:
                return
            x = widget.winfo_rootx() + 12
            y = widget.winfo_rooty() + widget.winfo_height() + 8
            win = tk.Toplevel(widget)
            win.wm_overrideredirect(True)
            try:
                win.wm_attributes("-topmost", True)
            except Exception:
                pass
            win.wm_geometry(f"+{x}+{y}")
            label = tk.Label(
                win,
                text=text,
                justify="left",
                bg="#1f1f1f",
                fg="#f2f2f2",
                padx=8,
                pady=6,
                relief="solid",
                borderwidth=1,
                wraplength=340,
            )
            label.pack()
            state["win"] = win

        def _schedule(_event=None):
            _hide()
            state["after_id"] = widget.after(delay_ms, _show)

        widget.bind("<Enter>", _schedule, add="+")
        widget.bind("<Leave>", _hide, add="+")
        widget.bind("<ButtonPress>", _hide, add="+")
        widget.bind("<FocusOut>", _hide, add="+")

    def _add_combo(self, parent, label, variable, values, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=5)
        values_list = [str(v) for v in values]
        width = max(10, min(max((len(v) for v in values_list), default=10) + 1, 32))
        combo = ttk.Combobox(parent, textvariable=variable, values=values_list, state="readonly", width=width)
        combo.grid(
            row=row, column=1, sticky="w", padx=8, pady=5
        )
        combo.bind("<MouseWheel>", self._on_combo_scroll_protegido, add="+")
        combo.bind("<Button-4>", self._on_combo_scroll_protegido, add="+")
        combo.bind("<Button-5>", self._on_combo_scroll_protegido, add="+")
        return combo

    def _add_entry(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=5)
        ttk.Entry(parent, textvariable=variable, width=24).grid(row=row, column=1, sticky="ew", padx=8, pady=5)
        parent.grid_columnconfigure(1, weight=1)

    def _add_spin(self, parent, label, variable, min_v, max_v, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=5)
        ttk.Spinbox(parent, textvariable=variable, from_=min_v, to=max_v, width=10).grid(
            row=row, column=1, sticky="w", padx=8, pady=5
        )

    def _market_code_from_label(self, value):
        if value in MARKET_LABEL_TO_CODE:
            return MARKET_LABEL_TO_CODE[value]
        if value in MARKET_CODE_TO_LABEL:
            return value
        return HOME_MARKET

    def _market_label_from_value(self, value):
        if value in MARKET_LABEL_TO_CODE:
            return value
        return MARKET_CODE_TO_LABEL.get(value, "Perú")

    def _trip_code_from_label(self, value):
        if value in TRIP_LABEL_TO_CODE:
            return TRIP_LABEL_TO_CODE[value]
        if value in TRIP_CODE_TO_LABEL:
            return value
        return TIPO_VIAJE

    def _trip_label_from_value(self, value):
        if value in TRIP_LABEL_TO_CODE:
            return value
        return TRIP_CODE_TO_LABEL.get(value, "Solo ida")

    def _checkpoint_code_from_label(self, value):
        if value in CHECKPOINT_LABEL_TO_CODE:
            return CHECKPOINT_LABEL_TO_CODE[value]
        if value in CHECKPOINT_CODE_TO_LABEL:
            return value
        return NO_CHECKPOINT

    def _checkpoint_label_from_value(self, value):
        if value in CHECKPOINT_LABEL_TO_CODE:
            return value
        return CHECKPOINT_CODE_TO_LABEL.get(value, "Ninguno (flujo completo)")

    def _snapshot_settings(self):
        return {
            "preset": self.preset_var.get(),
            "presets_guardados": self._serializar_presets(),
            "market": self.market_var.get(),
            "tipo_viaje": self.tipo_viaje_var.get(),
            "origen": self.origen_var.get(),
            "destino": self.destino_var.get(),
            "dias": int(self.dias_var.get()),
            "dias_retorno": int(self.dias_retorno_var.get()),
            "adultos": int(self.adultos_var.get()),
            "ninos": int(self.ninos_var.get()),
            "infantes": int(self.infantes_var.get()),
            "checkpoint": self.checkpoint_var.get(),
            "pausa": int(self.pausa_var.get()),
            "slow_mo": int(self.slow_mo_var.get()),
            "espera_final": int(self.espera_final_var.get()),
            "cdp_url": self.cdp_url_var.get(),
            "headless": bool(self.headless_var.get()),
            "usar_chrome_existente": bool(self.usar_chrome_existente_var.get()),
            "modo_exploracion": bool(self.modo_exploracion_var.get()),
            "solo_exploracion": bool(self.solo_exploracion_var.get()),
            "log_limpio": bool(self.log_limpio_var.get()),
            "nombre_override": self.nombre_override_var.get(),
            "apellido_override": self.apellido_override_var.get(),
            "email_override": self.email_override_var.get(),
            "doc_tipo_override": self.doc_tipo_override_var.get(),
            "doc_numero_override": self.doc_numero_override_var.get(),
            "telefono_override": self.telefono_override_var.get(),
            "prefijo_pais_override": self.prefijo_pais_override_var.get(),
            "genero_override": self.genero_override_var.get(),
            "pais_emision_override": self.pais_emision_override_var.get(),
            "fecha_nac_override": self.fecha_nac_override_var.get(),
            "tarjeta_numero_override": self.tarjeta_numero_override_var.get(),
            "tarjeta_fecha_override": self.tarjeta_fecha_override_var.get(),
            "tarjeta_cvv_override": self.tarjeta_cvv_override_var.get(),
        }

    def _aplicar_settings(self, settings):
        if not isinstance(settings, dict):
            return

        def _set_str(var, key):
            value = settings.get(key)
            if value is not None:
                var.set(str(value))

        def _set_int(var, key):
            value = settings.get(key)
            if value is None:
                return
            try:
                var.set(int(value))
            except Exception:
                return

        def _set_bool(var, key):
            value = settings.get(key)
            if value is not None:
                var.set(bool(value))

        _set_str(self.preset_var, "preset")
        _set_str(self.market_var, "market")
        _set_str(self.tipo_viaje_var, "tipo_viaje")
        _set_str(self.origen_var, "origen")
        _set_str(self.destino_var, "destino")
        _set_int(self.dias_var, "dias")
        _set_int(self.dias_retorno_var, "dias_retorno")
        _set_int(self.adultos_var, "adultos")
        _set_int(self.ninos_var, "ninos")
        _set_int(self.infantes_var, "infantes")
        _set_str(self.checkpoint_var, "checkpoint")
        _set_int(self.pausa_var, "pausa")
        _set_int(self.slow_mo_var, "slow_mo")
        _set_int(self.espera_final_var, "espera_final")
        _set_str(self.cdp_url_var, "cdp_url")
        _set_bool(self.headless_var, "headless")
        _set_bool(self.usar_chrome_existente_var, "usar_chrome_existente")
        _set_bool(self.modo_exploracion_var, "modo_exploracion")
        _set_bool(self.solo_exploracion_var, "solo_exploracion")
        _set_bool(self.log_limpio_var, "log_limpio")

        _set_str(self.nombre_override_var, "nombre_override")
        _set_str(self.apellido_override_var, "apellido_override")
        _set_str(self.email_override_var, "email_override")
        _set_str(self.doc_tipo_override_var, "doc_tipo_override")
        _set_str(self.doc_numero_override_var, "doc_numero_override")
        _set_str(self.telefono_override_var, "telefono_override")
        _set_str(self.prefijo_pais_override_var, "prefijo_pais_override")
        _set_str(self.genero_override_var, "genero_override")
        _set_str(self.pais_emision_override_var, "pais_emision_override")
        _set_str(self.fecha_nac_override_var, "fecha_nac_override")
        _set_str(self.tarjeta_numero_override_var, "tarjeta_numero_override")
        _set_str(self.tarjeta_fecha_override_var, "tarjeta_fecha_override")
        _set_str(self.tarjeta_cvv_override_var, "tarjeta_cvv_override")

        if self.preset_var.get() not in self.presets:
            self.preset_var.set(CUSTOM_PRESET_NAME)
        self.market_var.set(self._market_label_from_value(self.market_var.get()))
        self.tipo_viaje_var.set(self._trip_label_from_value(self.tipo_viaje_var.get()))
        self.checkpoint_var.set(self._checkpoint_label_from_value(self.checkpoint_var.get()))
        if self.genero_override_var.get() not in {"", "Masculino", "Femenino"}:
            self.genero_override_var.set("")
        self.cdp_url_var.set(self._normalizar_cdp_url(self.cdp_url_var.get()))

    def _cargar_settings(self):
        if not GUI_SETTINGS_PATH.exists():
            return
        try:
            data = json.loads(GUI_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            self.status_var.set("No se pudo leer la configuración previa")
            return
        self._cargar_presets_desde_data(data.get("presets_guardados"))
        self._aplicar_settings(data)
        self.status_var.set("Configuración previa cargada")

    def _guardar_settings(self):
        try:
            data = self._snapshot_settings()
            GUI_SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
        except Exception as error:
            self._append_log(f"⚠️ No se pudo guardar configuración GUI: {error}")

    def _aplicar_preset(self):
        preset = self.presets.get(self.preset_var.get(), {})
        if not preset:
            self.status_var.set("Caso personalizado activo")
            return

        self._suspend_preset_tracking = True
        try:
            self._aplicar_settings(preset)
        finally:
            self._suspend_preset_tracking = False
        self.status_var.set(f"Caso aplicado: {self.preset_var.get()}")

    def _on_preset_combo_selected(self, _event=None):
        self._aplicar_preset()

    def _restablecer(self):
        self._suspend_preset_tracking = True
        try:
            self.preset_var.set(DEFAULT_PRESET_NAME)
            self.market_var.set("Perú")
            self.tipo_viaje_var.set("Solo ida")
            self.origen_var.set(VUELO_ORIGEN)
            self.destino_var.set(VUELO_DESTINO)
            self.dias_var.set(DIAS_A_FUTURO)
            self.dias_retorno_var.set(DIAS_RETORNO_DESDE_IDA)
            self.adultos_var.set(1)
            self.ninos_var.set(0)
            self.infantes_var.set(0)
            self.checkpoint_var.set("Ninguno (flujo completo)")
            self.pausa_var.set(TIEMPO_PAUSA_SEGURIDAD)
            self.slow_mo_var.set(VELOCIDAD_VISUAL)
            self.espera_final_var.set(ESPERA_FINAL_SEGUNDOS)
            self.cdp_url_var.set(CDP_URL_DEFAULT)
            self.headless_var.set(False)
            self.usar_chrome_existente_var.set(True)
            self.modo_exploracion_var.set(False)
            self.solo_exploracion_var.set(False)
            self.log_limpio_var.set(True)
            self.nombre_override_var.set(PASAJERO.get("nombre", ""))
            self.apellido_override_var.set(PASAJERO.get("apellido", ""))
            self.email_override_var.set(PASAJERO.get("email", ""))
            self.doc_tipo_override_var.set(PASAJERO.get("doc_tipo", ""))
            self.doc_numero_override_var.set(PASAJERO.get("doc_numero", ""))
            self.telefono_override_var.set(PASAJERO.get("telefono", ""))
            self.prefijo_pais_override_var.set(PASAJERO.get("prefijo_pais", ""))
            self.genero_override_var.set(PASAJERO.get("genero", ""))
            self.pais_emision_override_var.set(PASAJERO.get("pais_emision", ""))
            self.fecha_nac_override_var.set(PASAJERO.get("fecha_nac", ""))
            tarjeta_default = TARJETA_POR_MARKET.get("PE", {})
            self.tarjeta_numero_override_var.set(tarjeta_default.get("numero", ""))
            self.tarjeta_fecha_override_var.set(tarjeta_default.get("fecha", ""))
            self.tarjeta_cvv_override_var.set(tarjeta_default.get("cvv", ""))
        finally:
            self._suspend_preset_tracking = False
        self.status_var.set("Valores restablecidos")
        self._guardar_settings()

    def _validar_numeros(self):
        try:
            adultos = int(self.adultos_var.get())
            ninos = int(self.ninos_var.get())
            infantes = int(self.infantes_var.get())
            dias = int(self.dias_var.get())
            dias_retorno = int(self.dias_retorno_var.get())
            pausa = int(self.pausa_var.get())
            slow_mo = int(self.slow_mo_var.get())
            espera_final = int(self.espera_final_var.get())
        except Exception as error:
            raise ValueError(f"Hay un valor numérico inválido: {error}")

        if adultos <= 0:
            raise ValueError("Adultos debe ser mayor a 0.")
        if min(ninos, infantes, dias, dias_retorno, pausa, slow_mo, espera_final) < 0:
            raise ValueError("No se permiten valores negativos.")
        if infantes > adultos:
            raise ValueError("Infantes no puede ser mayor que adultos.")
        return {
            "adultos": adultos,
            "ninos": ninos,
            "infantes": infantes,
            "dias": dias,
            "dias_retorno": dias_retorno,
            "pausa": pausa,
            "slow_mo": slow_mo,
            "espera_final": espera_final,
        }

    def _cdp_disponible(self, cdp_url):
        endpoint = f"{cdp_url.rstrip('/')}/json/version"
        try:
            with urllib.request.urlopen(endpoint, timeout=1.5) as response:
                return response.status == 200
        except Exception:
            return False

    def _normalizar_cdp_url(self, cdp_url):
        valor = (cdp_url or "").strip()
        if not valor:
            return CDP_URL_DEFAULT
        if "://" not in valor:
            valor = f"http://{valor}"
        return valor

    def _detectar_binario_chrome(self):
        if sys.platform == "darwin":
            candidatos = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]
            for ruta in candidatos:
                if Path(ruta).exists():
                    return ruta
            return None

        if sys.platform.startswith("linux"):
            for comando in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
                ruta = shutil.which(comando)
                if ruta:
                    return ruta
            return None

        if sys.platform == "win32":
            for comando in ("chrome", "chromium"):
                ruta = shutil.which(comando)
                if ruta:
                    return ruta
            return None

        return None

    def _iniciar_chrome_cdp(self, cdp_url):
        parsed = urllib.parse.urlparse(cdp_url)
        host = (parsed.hostname or "").lower()
        puerto = parsed.port or 9222
        if host not in {"127.0.0.1", "localhost"}:
            return False, "Auto-inicio CDP solo soporta localhost/127.0.0.1."

        chrome_bin = self._detectar_binario_chrome()
        if not chrome_bin:
            return False, "No se encontró Chrome/Chromium instalado en el sistema."

        if sys.platform == "win32":
            profile_dir = Path.home() / "AppData" / "Local" / "Temp" / "chrome-cdp-sky"
        else:
            profile_dir = Path("/tmp/chrome-cdp-sky")
        args = [
            chrome_bin,
            f"--remote-debugging-port={puerto}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        try:
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as error:
            return False, f"No se pudo iniciar Chrome CDP: {error}"

        deadline = time.time() + CDP_START_TIMEOUT_SEGUNDOS
        while time.time() < deadline:
            if self._cdp_disponible(cdp_url):
                return True, "Chrome CDP listo."
            time.sleep(0.25)
        return False, f"Chrome se inició, pero CDP no respondió en {CDP_START_TIMEOUT_SEGUNDOS}s."

    def _asegurar_chrome_cdp(self):
        cdp_url = self._normalizar_cdp_url(self.cdp_url_var.get())
        self.cdp_url_var.set(cdp_url)
        if self._cdp_disponible(cdp_url):
            self.cdp_iniciado_automaticamente = False
            return True

        self._append_log("ℹ️ CDP no disponible; iniciando Chrome automáticamente...")
        ok, mensaje = self._iniciar_chrome_cdp(cdp_url)
        self.cdp_iniciado_automaticamente = bool(ok)
        self._append_log(("✅ " if ok else "❌ ") + mensaje)
        return ok

    def _iniciar_chrome_cdp_manual(self):
        cdp_url = self._normalizar_cdp_url(self.cdp_url_var.get())
        self.cdp_url_var.set(cdp_url)
        if self._cdp_disponible(cdp_url):
            self.cdp_iniciado_automaticamente = False
            self._append_log(f"✅ CDP activo en {cdp_url}")
            self.status_var.set("CDP activo")
            return

        ok, mensaje = self._iniciar_chrome_cdp(cdp_url)
        self.cdp_iniciado_automaticamente = bool(ok)
        self._append_log(("✅ " if ok else "❌ ") + mensaje)
        self.status_var.set("CDP activo" if ok else "Error iniciando CDP")
        if not ok:
            messagebox.showerror("CDP", mensaje)

    def _construir_comando(self):
        numeros = self._validar_numeros()
        market_code = self._market_code_from_label(self.market_var.get())
        tipo_viaje_code = self._trip_code_from_label(self.tipo_viaje_var.get())
        checkpoint_code = self._checkpoint_code_from_label(self.checkpoint_var.get())

        cmd = [PYTHON_EXEC, "-u", str(PROJECT_ROOT / "test_sky.py")]
        cmd.extend(["--market", market_code])
        cmd.extend(["--tipo-viaje", tipo_viaje_code])
        origen = self.origen_var.get().strip()
        destino = self.destino_var.get().strip()
        if origen:
            cmd.extend(["--origen", origen])
        if destino:
            cmd.extend(["--destino", destino])
        cmd.extend(["--dias", str(numeros["dias"])])
        cmd.extend(["--dias-retorno", str(numeros["dias_retorno"])])
        cmd.extend(["--adultos", str(numeros["adultos"])])
        cmd.extend(["--ninos", str(numeros["ninos"])])
        cmd.extend(["--infantes", str(numeros["infantes"])])
        cmd.extend(["--pausa", str(numeros["pausa"])])
        cmd.extend(["--slow-mo", str(numeros["slow_mo"])])
        cmd.extend(["--espera-final-segundos", str(numeros["espera_final"])])

        if checkpoint_code and checkpoint_code != NO_CHECKPOINT:
            cmd.extend(["--checkpoint", checkpoint_code])
        if self.headless_var.get():
            cmd.append("--headless")
        if self.usar_chrome_existente_var.get():
            cmd.append("--usar-chrome-existente")
            cdp_url = self._normalizar_cdp_url(self.cdp_url_var.get())
            self.cdp_url_var.set(cdp_url)
            if cdp_url:
                cmd.extend(["--cdp-url", cdp_url])
            if self.cdp_iniciado_automaticamente:
                cmd.append("--cdp-reutilizar-primera-pestana")
        if self.modo_exploracion_var.get():
            cmd.append("--modo-exploracion")
        if self.solo_exploracion_var.get():
            cmd.append("--solo-exploracion")

        overrides_texto = [
            ("--nombre", self.nombre_override_var.get()),
            ("--apellido", self.apellido_override_var.get()),
            ("--email", self.email_override_var.get()),
            ("--doc-tipo", self.doc_tipo_override_var.get()),
            ("--doc-numero", self.doc_numero_override_var.get()),
            ("--telefono", self.telefono_override_var.get()),
            ("--prefijo-pais", self.prefijo_pais_override_var.get()),
            ("--pais-emision", self.pais_emision_override_var.get()),
            ("--fecha-nac", self.fecha_nac_override_var.get()),
            ("--tarjeta-numero", self.tarjeta_numero_override_var.get()),
            ("--tarjeta-fecha", self.tarjeta_fecha_override_var.get()),
            ("--tarjeta-cvv", self.tarjeta_cvv_override_var.get()),
        ]
        for flag, valor in overrides_texto:
            texto = (valor or "").strip()
            if texto:
                cmd.extend([flag, texto])

        genero = (self.genero_override_var.get() or "").strip()
        if genero in {"Masculino", "Femenino"}:
            cmd.extend(["--genero", genero])

        return cmd

    def _iniciar_ejecucion(self):
        if self.process and self.process.poll() is None:
            messagebox.showwarning("Ejecución en curso", "Ya hay una ejecución activa.")
            return

        if self.usar_chrome_existente_var.get() and not self._asegurar_chrome_cdp():
            messagebox.showerror(
                "CDP",
                "No se pudo iniciar/conectar a Chrome CDP automáticamente. Revisa la CDP URL o inicia Chrome manualmente.",
            )
            return

        try:
            cmd = self._construir_comando()
        except ValueError as error:
            messagebox.showerror("Validación", str(error))
            return

        log_limpio = bool(self.log_limpio_var.get())
        self._guardar_settings()
        if log_limpio:
            self._append_log("▶️ Iniciando ejecución del flujo...")
        else:
            self._append_log(f"$ {' '.join(cmd)}")
        self.status_var.set("Iniciando ejecución...")
        self.run_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)

        worker = threading.Thread(target=self._ejecutar_proceso, args=(cmd, log_limpio), daemon=True)
        worker.start()

    def _filtrar_linea_log(self, text, log_limpio):
        if text is None:
            return None
        linea_raw = str(text).rstrip()
        if not linea_raw.strip():
            return None if log_limpio else ""
        if not log_limpio:
            return linea_raw

        lower = linea_raw.lower()
        if "deprecationwarning" in lower:
            return None
        if linea_raw.startswith("(node:") or linea_raw.startswith("(Use `node --trace-deprecation"):
            return None

        prefijos_relevantes = (
            "---",
            "✅",
            "❌",
            "⚠️",
            "ℹ️",
            "🔌",
            "🧭",
            "🧪",
            "🧾",
            "📸",
            "🖱️",
            "⏸️",
            "⏹️",
            "👋",
            "🧹",
            "💳",
            "▶️",
        )
        if linea_raw.startswith(prefijos_relevantes):
            return linea_raw

        if any(token in lower for token in ("error", "traceback", "exception")):
            return linea_raw

        if linea_raw.startswith("    ") and any(
            token in linea_raw for token in ("Medio de pago", "Tipo viaje", "Modo exploración")
        ):
            return linea_raw

        return None

    def _ejecutar_proceso(self, cmd, log_limpio):
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in self.process.stdout:
                filtrada = self._filtrar_linea_log(line.rstrip("\n"), log_limpio)
                if filtrada is not None:
                    self.queue.put(("log", filtrada))
            return_code = self.process.wait()
            self.queue.put(("status", f"Finalizado con código {return_code}"))
        except Exception as error:
            self.queue.put(("log", f"❌ Error ejecutando proceso: {error}"))
            self.queue.put(("status", "Error de ejecución"))
        finally:
            self.queue.put(("done", None))

    def _detener_ejecucion(self):
        if not self.process or self.process.poll() is not None:
            self.status_var.set("No hay ejecución activa")
            return
        self._append_log("⏹️ Solicitando detener proceso...")
        self.process.terminate()
        self.status_var.set("Deteniendo...")
        self.root.after(3000, self._forzar_stop_si_sigue)

    def _forzar_stop_si_sigue(self):
        if self.process and self.process.poll() is None:
            self._append_log("⚠️ Forzando cierre del proceso...")
            self.process.kill()

    def _procesar_cola(self):
        while True:
            try:
                kind, payload = self.queue.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self._append_log(payload)
            elif kind == "status":
                self.status_var.set(payload)
            elif kind == "done":
                self.run_button.configure(state=tk.NORMAL)
                self.stop_button.configure(state=tk.DISABLED)
                self.process = None
        self.root.after(120, self._procesar_cola)

    def _append_log(self, text):
        self.log_text.insert(tk.END, f"{text}\n")
        self.log_text.see(tk.END)

    def _limpiar_log(self):
        self.log_text.delete("1.0", tk.END)

    def _al_cerrar_ventana(self):
        self._guardar_settings()
        if self.process and self.process.poll() is None:
            cerrar = messagebox.askyesno("Cerrar", "Hay una ejecución activa. ¿Deseas detenerla y salir?")
            if not cerrar:
                return
            self._detener_ejecucion()
            self.root.after(300, self.root.destroy)
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    if sys.platform == "darwin":
        root.tk.call("tk", "scaling", 1.1)
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    elif sys.platform == "darwin" and "aqua" in style.theme_names():
        style.theme_use("aqua")

    colors = {
        "bg": "#f5f7fa",
        "panel": "#ffffff",
        "fg": "#14213d",
        "muted": "#4a5568",
        "border": "#d6dde8",
        "button": "#e7ecf5",
        "button_active": "#d9e2f0",
        "primary_button": "#2563eb",
        "primary_button_active": "#1d4ed8",
        "primary_button_fg": "#ffffff",
        "section": "#eaf0f9",
        "section_active": "#dde7f5",
        "field": "#ffffff",
    }
    root.configure(bg=colors["bg"])

    style.configure(".", background=colors["bg"], foreground=colors["fg"], font=("SF Pro Text", 12))
    style.configure("TFrame", background=colors["bg"])
    style.configure("TLabel", background=colors["bg"], foreground=colors["fg"], padding=(0, 1))
    style.configure("HintIcon.TLabel", background=colors["bg"], foreground="#3b82f6", font=("SF Pro Text", 12, "bold"))
    style.configure("TLabelframe", background=colors["panel"], borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label", background=colors["bg"], foreground=colors["fg"], font=("SF Pro Text", 12, "bold"))
    style.configure("TCheckbutton", background=colors["panel"], foreground=colors["fg"])
    style.map("TCheckbutton", foreground=[("disabled", colors["muted"])])
    style.configure("TButton", padding=(12, 6), background=colors["button"], foreground=colors["fg"], relief="flat")
    style.map(
        "TButton",
        background=[("active", colors["button_active"]), ("pressed", colors["button_active"])],
        foreground=[("disabled", colors["muted"])],
    )
    style.configure(
        "Primary.TButton",
        padding=(14, 6),
        background=colors["primary_button"],
        foreground=colors["primary_button_fg"],
        relief="flat",
        font=("SF Pro Text", 12, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[("active", colors["primary_button_active"]), ("pressed", colors["primary_button_active"])],
        foreground=[("disabled", colors["muted"])],
    )
    style.configure(
        "Section.TButton",
        anchor="w",
        padding=(10, 6),
        background=colors["section"],
        foreground=colors["fg"],
        relief="flat",
        font=("SF Pro Text", 12, "bold"),
    )
    style.map("Section.TButton", background=[("active", colors["section_active"]), ("pressed", colors["section_active"])])
    style.configure("TEntry", fieldbackground=colors["field"], foreground=colors["fg"])
    style.configure("TSpinbox", fieldbackground=colors["field"], foreground=colors["fg"], arrowsize=12)
    style.configure("TCombobox", fieldbackground=colors["field"], background=colors["field"], foreground=colors["fg"], arrowsize=14)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", colors["field"])],
        foreground=[("readonly", colors["fg"])],
    )
    SkyBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
