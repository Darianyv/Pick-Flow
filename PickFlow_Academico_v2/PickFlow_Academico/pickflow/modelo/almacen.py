"""Modelo del almacén: productos con coordenadas fijas repartidos en 5 pasillos.

Plano (vista desde arriba; X hacia la derecha, Y hacia el fondo, en metros):

     Y
     60 +-------------------------------------------------------+
        |                                                       |
     45 |   ##  ##     ##  ##     ##  ##     ##  ##     ##  ##   |  <- última fila
        |   ##  ##     ##  ##     ##  ##     ##  ##     ##  ##   |     de productos
        |   ##  ##     ##  ##     ##  ##     ##  ##     ##  ##   |
     10 |   ##  ##     ##  ##     ##  ##     ##  ##     ##  ##   |  <- primera fila
        |    P1         P2         P3         P4         P5       |
      4 | [INICIO]                                              |
      0 +-------------------------------------------------------+
        0       12        24        36        48        60     72  X

Cada pasillo tiene una estantería a cada lado (I = izquierda, D = derecha)
con 8 productos. En total: 5 pasillos x 2 lados x 8 productos = 80 productos.
Entre pasillos solo se puede pasar por dos pasillos transversales: el frontal
(y = 4, donde está el INICIO) y el trasero (y = 52). Las estanterías no se
atraviesan; ver ``distancias.py``.

Las coordenadas NO son aleatorias: se calculan con fórmulas fijas, así que el
mapa es siempre el mismo y los resultados se pueden reproducir en la exposición.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterator

Punto = tuple[float, float]


@dataclass(frozen=True)
class Producto:
    """Artículo almacenado en una posición fija del almacén.

    Atributos:
        codigo: Identificador legible, p. ej. ``P3-D-05`` (pasillo 3, lado
            derecho, posición 5).
        nombre: Nombre del producto (datos simulados).
        pasillo: Número de pasillo, de 1 a 5.
        lado: ``"I"`` (izquierda) o ``"D"`` (derecha).
        x, y: Coordenadas en metros. Son las que se usan para calcular las
            distancias euclidianas del TSP.
    """

    codigo: str
    nombre: str
    pasillo: int
    lado: str
    x: float
    y: float

    @property
    def posicion(self) -> Punto:
        """Coordenadas (x, y) del producto."""
        return (self.x, self.y)


class Pedido:
    """Lista ordenada de productos que el operario debe recolectar.

    El orden de la lista es el **orden original** del pedido (el orden en que
    llegaron las líneas). Es la referencia contra la que se mide la mejora del
    algoritmo.
    """

    def __init__(self, numero: str = "PED-0000") -> None:
        self.numero = numero
        self._productos: list[Producto] = []

    @property
    def productos(self) -> tuple[Producto, ...]:
        """Productos del pedido en su orden original."""
        return tuple(self._productos)

    def contiene(self, producto: Producto) -> bool:
        """Indica si el producto ya está en el pedido."""
        return producto in self._productos

    def alternar(self, producto: Producto) -> bool:
        """Agrega el producto si no está, o lo quita si ya está.

        Devuelve ``True`` si quedó agregado y ``False`` si fue quitado.
        """
        if producto in self._productos:
            self._productos.remove(producto)
            return False
        self._productos.append(producto)
        return True

    def limpiar(self) -> None:
        """Vacía el pedido."""
        self._productos.clear()

    def __len__(self) -> int:
        return len(self._productos)


class Almacen:
    """Almacén fijo de 5 pasillos con 80 productos y un punto de inicio."""

    NUM_PASILLOS = 5
    PRODUCTOS_POR_LADO = 8

    # Dimensiones del plano (metros).
    ANCHO = 72.0
    ALTO = 60.0

    # Geometría de los pasillos y estanterías (metros).
    X_PRIMER_PASILLO = 12.0       # eje del pasillo 1
    SEPARACION_PASILLOS = 12.0    # distancia entre ejes de pasillos contiguos
    Y_PRIMER_PRODUCTO = 10.0      # fila del primer producto
    SEPARACION_PRODUCTOS = 5.0    # distancia entre productos de un mismo lado
    DESPLAZAMIENTO_LATERAL = 3.5  # distancia del producto al eje del pasillo
    PROFUNDIDAD_ESTANTE = 3.0     # ancho dibujado de cada estantería

    # Pasillos transversales: son los únicos lugares donde el operario puede
    # cambiar de un pasillo a otro (las estanterías no se atraviesan).
    Y_PASILLO_FRONTAL = 4.0   # frente del almacén, donde está el INICIO
    Y_PASILLO_TRASERO = 52.0  # fondo del almacén

    # Punto donde el operario inicia y termina la ruta (muelle de despacho).
    # Está sobre el pasillo transversal frontal.
    DEPOSITO: Punto = (4.0, Y_PASILLO_FRONTAL)

    def __init__(self) -> None:
        self.productos: tuple[Producto, ...] = tuple(self._crear_productos())
        self._por_codigo = {p.codigo: p for p in self.productos}

    # ------------------------------------------------------------------ #
    # Construcción del mapa
    # ------------------------------------------------------------------ #
    def _crear_productos(self) -> Iterator[Producto]:
        """Genera los 80 productos con coordenadas calculadas por fórmula."""
        numero = 1
        for pasillo in range(1, self.NUM_PASILLOS + 1):
            x_eje = self.x_eje_pasillo(pasillo)
            for lado, signo in (("I", -1), ("D", 1)):
                for posicion in range(self.PRODUCTOS_POR_LADO):
                    yield Producto(
                        codigo=f"P{pasillo}-{lado}-{posicion + 1:02d}",
                        nombre=f"Producto {numero:03d}",
                        pasillo=pasillo,
                        lado=lado,
                        x=x_eje + signo * self.DESPLAZAMIENTO_LATERAL,
                        y=self.Y_PRIMER_PRODUCTO + posicion * self.SEPARACION_PRODUCTOS,
                    )
                    numero += 1

    def x_eje_pasillo(self, pasillo: int) -> float:
        """Coordenada X del eje del pasillo ``pasillo`` (1 a 5)."""
        return self.X_PRIMER_PASILLO + (pasillo - 1) * self.SEPARACION_PASILLOS

    def estanterias(self) -> list[tuple[float, float, float, float]]:
        """Rectángulos (x0, y0, x1, y1) de las 10 estanterías, para dibujarlas."""
        y0 = self.Y_PRIMER_PRODUCTO - self.SEPARACION_PRODUCTOS / 2
        y1 = (
            self.Y_PRIMER_PRODUCTO
            + (self.PRODUCTOS_POR_LADO - 1) * self.SEPARACION_PRODUCTOS
            + self.SEPARACION_PRODUCTOS / 2
        )
        mitad_pasillo = self.DESPLAZAMIENTO_LATERAL - self.PROFUNDIDAD_ESTANTE / 2
        rectangulos = []
        for pasillo in range(1, self.NUM_PASILLOS + 1):
            x = self.x_eje_pasillo(pasillo)
            rectangulos.append((x - mitad_pasillo - self.PROFUNDIDAD_ESTANTE, y0, x - mitad_pasillo, y1))
            rectangulos.append((x + mitad_pasillo, y0, x + mitad_pasillo + self.PROFUNDIDAD_ESTANTE, y1))
        return rectangulos

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    def obtener(self, codigo: str) -> Producto:
        """Producto por código (``KeyError`` si no existe)."""
        return self._por_codigo[codigo]

    def producto_mas_cercano(self, x: float, y: float, radio: float) -> Producto | None:
        """Producto más cercano al punto (x, y) dentro de ``radio`` metros, o ``None``."""
        mejor: Producto | None = None
        mejor_d2 = radio * radio
        for producto in self.productos:
            d2 = (producto.x - x) ** 2 + (producto.y - y) ** 2
            if d2 <= mejor_d2:
                mejor, mejor_d2 = producto, d2
        return mejor

    def generar_pedido_aleatorio(self, cantidad: int, rng: random.Random | None = None) -> Pedido:
        """Pedido con ``cantidad`` productos distintos elegidos al azar.

        El orden en que salen sorteados es el orden original del pedido.
        """
        if not 1 <= cantidad <= len(self.productos):
            raise ValueError(f"La cantidad debe estar entre 1 y {len(self.productos)}.")
        rng = rng or random.Random()
        pedido = Pedido(numero=f"PED-{rng.randint(0, 9999):04d}")
        for producto in rng.sample(self.productos, cantidad):
            pedido.alternar(producto)
        return pedido
