"""Lienzo (Canvas) que dibuja el almacén, los productos y la ruta del operario.

Es un componente "pasivo" de la Vista: no calcula nada del TSP. Recibe del
controlador qué dibujar y le avisa cuando el usuario hace clic sobre un producto.

La ruta se dibuja con un degradado de color a lo largo del recorrido:
    azul (inicio)  ->  verde (mitad)  ->  rojo (fin)
así se ve de un vistazo en qué orden camina el operario.
"""
from __future__ import annotations

import math
import tkinter as tk
from typing import Callable, Sequence

import customtkinter as ctk

from ..modelo.almacen import Almacen, Producto, Punto

# Paletas por modo de apariencia (el Canvas de Tk no se tematiza solo).
_PALETAS = {
    "Dark": {
        "fondo": "#1B1F24", "piso": "#242A31", "estante": "#3A434D", "borde": "#2D353E",
        "punto": "#5B6773", "red": "#56616D", "texto": "#E6EDF3", "tenue": "#8B98A5",
        "original": "#8B98A5", "parada": "#F2CC60", "texto_parada": "#1B1F24", "inicio": "#BC8CFF",
    },
    "Light": {
        "fondo": "#F4F6F8", "piso": "#FFFFFF", "estante": "#C9D1D9", "borde": "#AEB8C2",
        "punto": "#8B98A5", "red": "#9AA6B2", "texto": "#1F2933", "tenue": "#667085",
        "original": "#667085", "parada": "#F5B700", "texto_parada": "#1F2933", "inicio": "#8250DF",
    },
}

# Degradado de la ruta: (posición entre 0 y 1, color RGB).
_DEGRADADO = ((0.0, (59, 130, 246)), (0.5, (34, 197, 94)), (1.0, (239, 68, 68)))

_MARGEN_X = 24
_MARGEN_SUPERIOR = 30
_MARGEN_INFERIOR = 34
_RADIO_CLIC_M = 2.5  # radio (en metros) para detectar el producto pulsado


def color_degradado(t: float) -> str:
    """Color hexadecimal en la posición ``t`` (0 a 1) del degradado de la ruta."""
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(_DEGRADADO, _DEGRADADO[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            r, g, b = (round(a + (b_ - a) * f) for a, b_ in zip(c0, c1))
            return f"#{r:02x}{g:02x}{b:02x}"
    r, g, b = _DEGRADADO[-1][1]
    return f"#{r:02x}{g:02x}{b:02x}"


class LienzoAlmacen(tk.Canvas):
    """Plano 2D del almacén con los productos del pedido y la ruta calculada."""

    def __init__(
        self,
        master,
        al_hacer_clic: Callable[[Producto], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, highlightthickness=0, cursor="hand2", **kwargs)
        self._al_hacer_clic = al_hacer_clic
        self._almacen: Almacen | None = None
        self._paradas: Sequence[Producto] = ()
        self._ruta: Sequence[Punto] = ()
        self._ruta_original: Sequence[Punto] = ()
        self._mostrar_original = False
        self._sigue_pasillos = False
        # Transformación metros -> píxeles.
        self._escala = 1.0
        self._desfase_x = 0.0
        self._desfase_y = 0.0

        self.bind("<Configure>", lambda _evento: self.redibujar())
        self.bind("<Button-1>", self._manejar_clic)

    # ------------------------------------------------------------------ #
    # API pública (la usa la ventana principal)
    # ------------------------------------------------------------------ #
    def definir_almacen(self, almacen: Almacen) -> None:
        """Define el almacén a dibujar."""
        self._almacen = almacen
        self.redibujar()

    def definir_escena(
        self,
        paradas: Sequence[Producto],
        ruta: Sequence[Punto] | None = None,
        ruta_original: Sequence[Punto] | None = None,
        sigue_pasillos: bool = False,
    ) -> None:
        """Define las paradas (en el orden en que se numeran) y las rutas a trazar.

        Si ``sigue_pasillos`` es True, la ruta camina por la red de pasillos: se
        dibuja esa red y se une cada producto con el eje de su pasillo.
        """
        self._sigue_pasillos = sigue_pasillos
        self._paradas = tuple(paradas)
        self._ruta = tuple(ruta or ())
        self._ruta_original = tuple(ruta_original or ())
        self.redibujar()

    def mostrar_ruta_original(self, mostrar: bool) -> None:
        """Muestra u oculta la ruta original (línea punteada)."""
        self._mostrar_original = mostrar
        self.redibujar()

    # ------------------------------------------------------------------ #
    # Conversión de coordenadas
    # ------------------------------------------------------------------ #
    def _calcular_transformacion(self, ancho: int, alto: int) -> None:
        """Calcula escala y desfase para que el plano quepa centrado en el lienzo."""
        disponible_x = max(ancho - 2 * _MARGEN_X, 50)
        disponible_y = max(alto - _MARGEN_SUPERIOR - _MARGEN_INFERIOR, 50)
        self._escala = min(disponible_x / Almacen.ANCHO, disponible_y / Almacen.ALTO)
        self._desfase_x = _MARGEN_X + (disponible_x - Almacen.ANCHO * self._escala) / 2
        self._desfase_y = _MARGEN_SUPERIOR + (disponible_y - Almacen.ALTO * self._escala) / 2

    def _a_pixeles(self, x: float, y: float) -> tuple[float, float]:
        """Metros -> píxeles. El eje Y se invierte: el INICIO queda abajo."""
        return (
            self._desfase_x + x * self._escala,
            self._desfase_y + (Almacen.ALTO - y) * self._escala,
        )

    def _a_metros(self, px: float, py: float) -> tuple[float, float]:
        """Píxeles -> metros."""
        return (
            (px - self._desfase_x) / self._escala,
            Almacen.ALTO - (py - self._desfase_y) / self._escala,
        )

    # ------------------------------------------------------------------ #
    # Eventos
    # ------------------------------------------------------------------ #
    def _manejar_clic(self, evento) -> None:
        if self._almacen is None or self._al_hacer_clic is None:
            return
        x, y = self._a_metros(evento.x, evento.y)
        producto = self._almacen.producto_mas_cercano(x, y, _RADIO_CLIC_M)
        if producto is not None:
            self._al_hacer_clic(producto)

    # ------------------------------------------------------------------ #
    # Dibujo
    # ------------------------------------------------------------------ #
    def redibujar(self) -> None:
        """Redibuja todo según el tamaño del lienzo y el modo de apariencia."""
        paleta = _PALETAS.get(ctk.get_appearance_mode(), _PALETAS["Dark"])
        self.configure(bg=paleta["fondo"])
        self.delete("all")
        ancho, alto = self.winfo_width(), self.winfo_height()
        if self._almacen is None or ancho < 80 or alto < 80:
            return
        self._calcular_transformacion(ancho, alto)

        self._dibujar_plano(paleta)
        if self._sigue_pasillos:
            self._dibujar_red_pasillos(paleta)
        if self._mostrar_original and self._ruta_original:
            self._dibujar_ruta_original(paleta)
        if self._ruta:
            self._dibujar_ruta()
        self._dibujar_paradas(paleta)
        self._dibujar_inicio(paleta)
        self._dibujar_leyenda(ancho, alto, paleta)

    def _dibujar_plano(self, paleta: dict[str, str]) -> None:
        almacen = self._almacen
        assert almacen is not None
        x0, y0 = self._a_pixeles(0, Almacen.ALTO)
        x1, y1 = self._a_pixeles(Almacen.ANCHO, 0)
        self.create_rectangle(x0, y0, x1, y1, fill=paleta["piso"], outline=paleta["borde"])

        for ex0, ey0, ex1, ey1 in almacen.estanterias():
            px0, py0 = self._a_pixeles(ex0, ey1)
            px1, py1 = self._a_pixeles(ex1, ey0)
            self.create_rectangle(px0, py0, px1, py1, fill=paleta["estante"], outline=paleta["borde"])

        for pasillo in range(1, Almacen.NUM_PASILLOS + 1):
            px, _ = self._a_pixeles(almacen.x_eje_pasillo(pasillo), 0)
            self.create_text(
                px, self._desfase_y - 14, text=f"Pasillo {pasillo}",
                fill=paleta["tenue"], font=("Arial", 9, "bold"),
            )

        # Puntos pequeños: indican dónde está cada producto (se puede hacer clic).
        radio = max(1.5, self._escala * 0.18)
        for producto in almacen.productos:
            px, py = self._a_pixeles(producto.x, producto.y)
            self.create_oval(px - radio, py - radio, px + radio, py + radio, fill=paleta["punto"], outline="")

    def _dibujar_red_pasillos(self, paleta: dict[str, str]) -> None:
        """Dibuja punteada la red por la que SÍ se puede caminar."""
        almacen = self._almacen
        assert almacen is not None
        for pasillo in range(1, Almacen.NUM_PASILLOS + 1):
            x_eje = almacen.x_eje_pasillo(pasillo)
            ax, ay = self._a_pixeles(x_eje, Almacen.Y_PASILLO_FRONTAL)
            bx, by = self._a_pixeles(x_eje, Almacen.Y_PASILLO_TRASERO)
            self.create_line(ax, ay, bx, by, fill=paleta["red"], dash=(2, 4))
        for y in (Almacen.Y_PASILLO_FRONTAL, Almacen.Y_PASILLO_TRASERO):
            ax, ay = self._a_pixeles(Almacen.DEPOSITO[0], y)
            bx, by = self._a_pixeles(almacen.x_eje_pasillo(Almacen.NUM_PASILLOS), y)
            self.create_line(ax, ay, bx, by, fill=paleta["red"], dash=(2, 4))

    def _dibujar_ruta_original(self, paleta: dict[str, str]) -> None:
        pixeles = [self._a_pixeles(x, y) for x, y in self._ruta_original]
        plano = [coord for punto in pixeles for coord in punto]
        self.create_line(*plano, fill=paleta["original"], width=2, dash=(6, 5))

    def _dibujar_ruta(self) -> None:
        """Dibuja la ruta con un degradado según la distancia ya recorrida.

        El color de cada tramo depende de qué fracción del recorrido total lleva
        el operario al pasar por él: azul al salir, verde a la mitad, rojo al llegar.
        (Se usa la distancia y no el número de vértices porque, al caminar por
        pasillos, un mismo trayecto puede tener muchos o pocos vértices.)
        """
        pixeles = [self._a_pixeles(x, y) for x, y in self._ruta]
        largos = [math.hypot(bx - ax, by - ay) for (ax, ay), (bx, by) in zip(pixeles, pixeles[1:])]
        total = sum(largos) or 1.0
        recorrido = 0.0
        for ((ax, ay), (bx, by)), largo in zip(zip(pixeles, pixeles[1:]), largos):
            color = color_degradado((recorrido + largo / 2) / total)
            recorrido += largo
            self.create_line(ax, ay, bx, by, fill=color, width=3, capstyle=tk.ROUND)
            # Flecha de dirección en el punto medio de los tramos largos.
            if largo >= 30:
                ux, uy = (bx - ax) / largo, (by - ay) / largo
                mx, my = (ax + bx) / 2, (ay + by) / 2
                self.create_line(
                    mx - ux * 5, my - uy * 5, mx + ux * 5, my + uy * 5,
                    fill=color, width=3, arrow=tk.LAST, arrowshape=(10, 12, 5),
                )

    def _dibujar_paradas(self, paleta: dict[str, str]) -> None:
        radio = max(8.0, min(12.0, self._escala * 0.9))
        tamano_fuente = max(7, int(radio * 0.85))
        for numero, producto in enumerate(self._paradas, start=1):
            px, py = self._a_pixeles(producto.x, producto.y)
            if self._sigue_pasillos and self._almacen is not None:
                # El operario recolecta parado en el eje del pasillo.
                ex, ey = self._a_pixeles(self._almacen.x_eje_pasillo(producto.pasillo), producto.y)
                self.create_line(px, py, ex, ey, fill=paleta["parada"], width=2)
            self.create_oval(
                px - radio, py - radio, px + radio, py + radio,
                fill=paleta["parada"], outline=paleta["piso"], width=2,
            )
            self.create_text(
                px, py, text=str(numero),
                fill=paleta["texto_parada"], font=("Arial", tamano_fuente, "bold"),
            )

    def _dibujar_inicio(self, paleta: dict[str, str]) -> None:
        px, py = self._a_pixeles(*Almacen.DEPOSITO)
        mitad = 8
        self.create_rectangle(
            px - mitad, py - mitad, px + mitad, py + mitad,
            fill=paleta["inicio"], outline=paleta["piso"], width=2,
        )
        self.create_text(px + mitad + 6, py, text="INICIO / FIN", anchor="w",
                         fill=paleta["texto"], font=("Arial", 8, "bold"))

    def _dibujar_leyenda(self, ancho: int, alto: int, paleta: dict[str, str]) -> None:
        y = alto - 16
        x = _MARGEN_X
        # Barra de degradado = sentido del recorrido.
        pasos = 24
        for i in range(pasos):
            self.create_line(x + i * 2, y, x + i * 2 + 2, y, fill=color_degradado(i / (pasos - 1)), width=5)
        self.create_text(x + pasos * 2 + 8, y, text="Ruta optimizada (inicio -> fin)",
                         anchor="w", fill=paleta["texto"], font=("Arial", 9))
        if self._mostrar_original:
            x2 = x + pasos * 2 + 230
            self.create_line(x2, y, x2 + 28, y, fill=paleta["original"], width=2, dash=(6, 5))
            self.create_text(x2 + 36, y, text="Ruta original del pedido", anchor="w",
                             fill=paleta["texto"], font=("Arial", 9))
        self.create_text(ancho - _MARGEN_X, y, text="Clic en un producto para agregarlo o quitarlo",
                         anchor="e", fill=paleta["tenue"], font=("Arial", 9))
