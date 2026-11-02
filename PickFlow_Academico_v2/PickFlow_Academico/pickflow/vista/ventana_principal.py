"""Ventana principal de PickFlow Académico (CustomTkinter, con modo oscuro).

Distribución:

    +----------------+----------------------------------+------------------+
    | CONTROLES      |  Plano del almacén (Canvas)      | Orden de         |
    |  - Pedido      |  con productos y ruta            | recolección      |
    |  - Algoritmo   |                                  |                  |
    | MÉTRICAS       |                                  +------------------+
    |  - Original    +----------------------------------+ Traza del        |
    |  - Optimizada  | Barra de estado                  | algoritmo        |
    |  - Eficiencia  |                                  |                  |
    +----------------+----------------------------------+------------------+

La Vista NO contiene lógica del TSP. Cada acción del usuario se delega en el
controlador, y todo lo que se muestra se lo entrega el controlador.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import customtkinter as ctk

from .lienzo_almacen import LienzoAlmacen

if TYPE_CHECKING:  # solo para anotaciones de tipo
    from ..controlador.controlador import ControladorPickFlow
    from ..modelo.almacen import Almacen, Producto, Punto

_MODOS_APARIENCIA = {"Oscuro": "dark", "Claro": "light", "Sistema": "system"}
_SIN_DATO = "—"
_GRIS = ("gray35", "gray65")


class VentanaPrincipal(ctk.CTk):
    """Ventana con controles, plano del almacén, métricas y explicación del algoritmo."""

    ANCHO_PANEL_IZQUIERDO = 310
    ANCHO_PANEL_DERECHO = 360

    def __init__(self) -> None:
        super().__init__()
        self.title("PickFlow Académico · Optimización de rutas de picking (TSP)")
        self.geometry("1480x820")
        self.minsize(1200, 700)

        self._controlador: ControladorPickFlow | None = None
        self._etiquetas_metricas: dict[str, ctk.CTkLabel] = {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construir_panel_izquierdo()
        self._construir_centro()
        self._construir_panel_derecho()

    # ------------------------------------------------------------------ #
    # Construcción de la interfaz
    # ------------------------------------------------------------------ #
    def _construir_panel_izquierdo(self) -> None:
        # Panel desplazable: así nada queda cortado en pantallas de poca altura.
        panel = ctk.CTkScrollableFrame(self, width=self.ANCHO_PANEL_IZQUIERDO - 30, corner_radius=0)
        panel.grid(row=0, column=0, sticky="nsew")
        margen = {"padx": 12}

        ctk.CTkLabel(panel, text="PickFlow", font=ctk.CTkFont(size=28, weight="bold")).pack(
            anchor="w", pady=(18, 0), **margen
        )
        ctk.CTkLabel(
            panel, text="Ruta de picking más corta (TSP)",
            font=ctk.CTkFont(size=12), text_color=_GRIS,
        ).pack(anchor="w", pady=(0, 12), **margen)

        # --- Pedido ---
        self._titulo_seccion(panel, "PEDIDO")
        self._etiqueta_cantidad = ctk.CTkLabel(panel, text="Productos del pedido: 12", anchor="w")
        self._etiqueta_cantidad.pack(fill="x", pady=(4, 0), **margen)
        self._control_cantidad = ctk.CTkSlider(
            panel, from_=3, to=40, number_of_steps=37, command=self._al_mover_cantidad
        )
        self._control_cantidad.set(12)
        self._control_cantidad.pack(fill="x", pady=(4, 8), **margen)
        ctk.CTkButton(
            panel, text="Generar pedido aleatorio", command=self._al_pulsar_generar
        ).pack(fill="x", pady=(0, 6), **margen)
        ctk.CTkButton(
            panel, text="Limpiar pedido",
            fg_color=("gray70", "gray30"), hover_color=("gray60", "gray40"),
            text_color=("gray10", "gray90"), command=self._al_pulsar_limpiar,
        ).pack(fill="x", pady=(0, 12), **margen)

        # --- Algoritmo ---
        self._titulo_seccion(panel, "ALGORITMO Y DISTANCIA")
        self._menu_algoritmo = ctk.CTkOptionMenu(panel, values=[_SIN_DATO], dynamic_resizing=False)
        self._menu_algoritmo.pack(fill="x", pady=(4, 6), **margen)
        self._menu_metrica = ctk.CTkOptionMenu(panel, values=[_SIN_DATO], dynamic_resizing=False)
        self._menu_metrica.pack(fill="x", pady=(0, 8), **margen)
        self._boton_optimizar = ctk.CTkButton(
            panel, text="Optimizar ruta", height=42, font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=("#2EA043", "#238636"), hover_color=("#2C974B", "#2EA043"),
            command=self._al_pulsar_optimizar,
        )
        self._boton_optimizar.pack(fill="x", pady=(0, 8), **margen)
        self._interruptor_original = ctk.CTkSwitch(
            panel, text="Mostrar ruta original", command=self._al_cambiar_ruta_original
        )
        self._interruptor_original.pack(anchor="w", pady=(0, 12), **margen)

        # --- Métricas (panel para la exposición) ---
        self._titulo_seccion(panel, "MÉTRICAS")
        self._crear_tarjeta(panel, "original", "Distancia original recorrida", margen)
        self._crear_tarjeta(panel, "optimizada", "Distancia optimizada por la IA", margen)
        self._crear_tarjeta(panel, "eficiencia", "% de eficiencia ganado", margen, destacada=True)
        self._etiqueta_detalle = ctk.CTkLabel(
            panel, text="", anchor="w", justify="left", text_color=_GRIS,
            font=ctk.CTkFont(size=11), wraplength=250
        )
        self._etiqueta_detalle.pack(fill="x", pady=(2, 0), **margen)

        # --- Apariencia (al fondo) ---
        inferior = ctk.CTkFrame(panel, fg_color="transparent")
        inferior.pack(fill="x", pady=(16, 14), **margen)
        ctk.CTkLabel(inferior, text="Apariencia", anchor="w").pack(side="left")
        self._menu_apariencia = ctk.CTkOptionMenu(
            inferior, values=list(_MODOS_APARIENCIA), width=120, command=self._al_cambiar_apariencia
        )
        self._menu_apariencia.set("Oscuro")
        self._menu_apariencia.pack(side="right")

    def _crear_tarjeta(self, padre, clave: str, titulo: str, margen: dict, destacada: bool = False) -> None:
        """Tarjeta de métrica: título pequeño y valor grande."""
        tarjeta = ctk.CTkFrame(padre, corner_radius=8, fg_color=("gray85", "gray20"))
        tarjeta.pack(fill="x", pady=(4, 2), **margen)
        ctk.CTkLabel(tarjeta, text=titulo, anchor="w", font=ctk.CTkFont(size=11), text_color=_GRIS).pack(
            fill="x", padx=12, pady=(6, 0)
        )
        valor = ctk.CTkLabel(
            tarjeta, text=_SIN_DATO, anchor="w",
            font=ctk.CTkFont(size=26 if destacada else 22, weight="bold"),
            text_color=("#1A7F37", "#3FB950") if destacada else ("gray10", "gray95"),
        )
        valor.pack(fill="x", padx=12, pady=(0, 6))
        self._etiquetas_metricas[clave] = valor

    def _construir_centro(self) -> None:
        centro = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        centro.grid(row=0, column=1, sticky="nsew")
        centro.grid_rowconfigure(0, weight=1)
        centro.grid_columnconfigure(0, weight=1)

        self._lienzo = LienzoAlmacen(centro, al_hacer_clic=self._al_hacer_clic_en_producto)
        self._lienzo.grid(row=0, column=0, sticky="nsew")

        self._etiqueta_estado = ctk.CTkLabel(centro, text="", anchor="w", height=30)
        self._etiqueta_estado.grid(row=1, column=0, sticky="ew", padx=14)

    def _construir_panel_derecho(self) -> None:
        panel = ctk.CTkFrame(self, width=self.ANCHO_PANEL_DERECHO, corner_radius=0)
        panel.grid(row=0, column=2, sticky="nsew")
        panel.pack_propagate(False)
        fuente_codigo = ctk.CTkFont(family="Courier", size=12)

        self._titulo_lista = ctk.CTkLabel(
            panel, text="Orden de recolección", font=ctk.CTkFont(size=15, weight="bold"), anchor="w"
        )
        self._titulo_lista.pack(fill="x", padx=16, pady=(16, 4))
        self._caja_lista = ctk.CTkTextbox(panel, font=fuente_codigo, wrap="none", height=300)
        self._caja_lista.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        ctk.CTkLabel(
            panel, text="Traza del algoritmo (paso a paso)",
            font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 4))
        self._caja_traza = ctk.CTkTextbox(panel, font=fuente_codigo, wrap="none", height=300)
        self._caja_traza.pack(fill="both", expand=True, padx=12, pady=(0, 14))

        self._escribir(self._caja_lista, "")
        self._escribir(self._caja_traza, "Pulsa «Optimizar ruta» para ver cómo\npiensa el algoritmo.")

    @staticmethod
    def _titulo_seccion(padre, texto: str) -> None:
        ctk.CTkLabel(
            padre, text=texto, font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray40", "gray60"), anchor="w",
        ).pack(fill="x", padx=12, pady=(0, 2))

    @staticmethod
    def _escribir(caja: ctk.CTkTextbox, texto: str) -> None:
        """Reemplaza el contenido de una caja de texto de solo lectura."""
        caja.configure(state="normal")
        caja.delete("1.0", "end")
        caja.insert("end", texto)
        caja.configure(state="disabled")

    # ------------------------------------------------------------------ #
    # Eventos de la interfaz -> controlador
    # ------------------------------------------------------------------ #
    def conectar_controlador(self, controlador: "ControladorPickFlow") -> None:
        """Registra el controlador que atenderá los eventos."""
        self._controlador = controlador

    def _al_mover_cantidad(self, valor: float) -> None:
        self._etiqueta_cantidad.configure(text=f"Productos del pedido: {int(round(valor))}")

    def _al_pulsar_generar(self) -> None:
        if self._controlador:
            self._controlador.al_generar_pedido(self.cantidad_solicitada())

    def _al_pulsar_limpiar(self) -> None:
        if self._controlador:
            self._controlador.al_limpiar_pedido()

    def _al_pulsar_optimizar(self) -> None:
        if self._controlador:
            self._controlador.al_optimizar(self.algoritmo_seleccionado(), self.metrica_seleccionada())

    def _al_hacer_clic_en_producto(self, producto: "Producto") -> None:
        if self._controlador:
            self._controlador.al_hacer_clic_en_producto(producto)

    def _al_cambiar_ruta_original(self) -> None:
        self._lienzo.mostrar_ruta_original(bool(self._interruptor_original.get()))

    def _al_cambiar_apariencia(self, etiqueta: str) -> None:
        ctk.set_appearance_mode(_MODOS_APARIENCIA[etiqueta])
        # El Canvas de Tk no se tematiza solo: se redibuja tras el cambio.
        self.after(80, self._lienzo.redibujar)

    # ------------------------------------------------------------------ #
    # API que usa el controlador para actualizar la pantalla
    # ------------------------------------------------------------------ #
    def definir_algoritmos(self, nombres: Sequence[str]) -> None:
        """Carga las opciones del selector de algoritmo y elige la primera."""
        self._menu_algoritmo.configure(values=list(nombres))
        self._menu_algoritmo.set(nombres[0])

    def definir_metricas(self, nombres: Sequence[str]) -> None:
        """Carga las opciones del selector de distancia y elige la primera."""
        self._menu_metrica.configure(values=list(nombres))
        self._menu_metrica.set(nombres[0])

    def metrica_seleccionada(self) -> str:
        """Nombre de la métrica de distancia elegida en el menú."""
        return self._menu_metrica.get()

    def cantidad_solicitada(self) -> int:
        """Cantidad de productos elegida en el control deslizante."""
        return int(round(self._control_cantidad.get()))

    def algoritmo_seleccionado(self) -> str:
        """Nombre del algoritmo elegido en el menú."""
        return self._menu_algoritmo.get()

    def mostrar_almacen(self, almacen: "Almacen") -> None:
        """Dibuja el plano del almacén."""
        self._lienzo.definir_almacen(almacen)

    def mostrar_pedido(
        self,
        paradas: Sequence["Producto"],
        ruta: Sequence["Punto"] | None = None,
        ruta_original: Sequence["Punto"] | None = None,
        sigue_pasillos: bool = False,
    ) -> None:
        """Dibuja las paradas numeradas y, si existen, las rutas."""
        self._lienzo.definir_escena(paradas, ruta, ruta_original, sigue_pasillos)

    def mostrar_lista(self, titulo: str, encabezado: str, filas: Sequence[str]) -> None:
        """Muestra la lista de productos en el panel derecho."""
        self._titulo_lista.configure(text=titulo)
        if filas:
            texto = encabezado + "\n" + "-" * len(encabezado) + "\n" + "\n".join(filas)
        else:
            texto = "El pedido está vacío.\n\nGenera un pedido aleatorio o\nhaz clic en los productos del plano."
        self._escribir(self._caja_lista, texto)

    def mostrar_traza(self, lineas: Sequence[str]) -> None:
        """Muestra la explicación paso a paso del algoritmo."""
        texto = "\n".join(lineas) if lineas else "Pulsa «Optimizar ruta» para ver cómo\npiensa el algoritmo."
        self._escribir(self._caja_traza, texto)

    def mostrar_metricas(self, metricas: dict[str, str] | None) -> None:
        """Muestra las métricas de la optimización; ``None`` las limpia."""
        for clave, etiqueta in self._etiquetas_metricas.items():
            etiqueta.configure(text=metricas[clave] if metricas else _SIN_DATO)
        self._etiqueta_detalle.configure(text=metricas["detalle"] if metricas else "")

    def mostrar_estado(self, mensaje: str) -> None:
        """Escribe un mensaje en la barra de estado."""
        self._etiqueta_estado.configure(text=mensaje)

    def indicar_ocupado(self, ocupado: bool) -> None:
        """Deshabilita el botón mientras se calcula."""
        self._boton_optimizar.configure(
            state="disabled" if ocupado else "normal",
            text="Calculando..." if ocupado else "Optimizar ruta",
        )
        self.update_idletasks()  # fuerza a Tk a repintar el botón antes del cálculo
