"""Formas de medir la distancia entre dos puntos del almacén (patrón Estrategia).

=====================================================================
EL PROBLEMA DE LA LÍNEA RECTA
=====================================================================
La distancia euclidiana mide "como vuela el pájaro": en línea recta. Pero un
operario no puede atravesar una estantería. Solo puede caminar por:

  * el EJE de cada pasillo (líneas verticales), y
  * los dos PASILLOS TRANSVERSALES, el frontal y el trasero (líneas horizontales).

    Y
    52 ======+=========+=========+=========+=========+======   pasillo transversal trasero
              |         |         |         |         |
              |  ##  ## |  ##  ## |  ##  ## |  ##  ## |  ##  ##    cada pasillo se recorre
              |  ##  ## |  ##  ## |  ##  ## |  ##  ## |  ##  ##    por su eje (x = 12, 24, ...)
              |         |         |         |         |
     4 [INICIO]=========+=========+=========+=========+======   pasillo transversal frontal
        4      12        24        36        48        60     X

Para ir de un producto a otro hay dos casos:

  1. MISMO PASILLO: se camina por el eje, distancia = |diferencia de Y|.
  2. DISTINTO PASILLO: hay que salir del pasillo hasta un transversal, cruzar
     lateralmente y volver a entrar. Hay dos caminos posibles (por el frente o
     por el fondo) y se elige el más corto:

        por el frente = (Ya - Yfrente) + |Xa - Xb| + (Yb - Yfrente)
        por el fondo  = (Yfondo - Ya) + |Xa - Xb| + (Yfondo - Yb)

Esta distancia sigue siendo simétrica y cumple la desigualdad triangular (es el
camino más corto sobre una red), así que el TSP funciona igual: los algoritmos
no cambian, solo cambia la matriz que reciben.

Supuesto: el operario recolecta parado sobre el eje del pasillo, así que se
ignora el ancho del pasillo (los 3,5 m entre el eje y el producto).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from .almacen import Almacen, Punto
from .tsp import distancia_euclidiana


class MetricaDistancia(ABC):
    """Contrato de una forma de medir distancias (patrón Estrategia).

    Cada métrica sabe dos cosas:
        * ``distancia(a, b)``: cuántos metros hay entre dos puntos.
        * ``camino(a, b)``: por dónde se camina (para dibujarlo en el plano).
    Las dos deben ser coherentes: la longitud del camino es la distancia.
    """

    nombre: str = "Métrica"
    #: Indica si el camino sigue la red de pasillos (la vista dibuja la red).
    sigue_pasillos: bool = False

    @abstractmethod
    def distancia(self, a: Punto, b: Punto) -> float:
        """Distancia en metros entre los puntos ``a`` y ``b``."""

    @abstractmethod
    def camino(self, a: Punto, b: Punto) -> list[Punto]:
        """Puntos por los que se pasa al ir de ``a`` a ``b`` (incluye ambos)."""

    def camino_completo(self, puntos: Sequence[Punto]) -> list[Punto]:
        """Camino que une todos los puntos, en orden, sin repetir vértices."""
        resultado: list[Punto] = []
        for a, b in zip(puntos, puntos[1:]):
            for punto in self.camino(a, b):
                if not resultado or resultado[-1] != punto:
                    resultado.append(punto)
        return resultado


class MetricaEuclidiana(MetricaDistancia):
    """Línea recta entre los puntos (la que pide el enunciado original)."""

    nombre = "Euclidiana (línea recta)"
    sigue_pasillos = False

    def distancia(self, a: Punto, b: Punto) -> float:
        return distancia_euclidiana(a, b)

    def camino(self, a: Punto, b: Punto) -> list[Punto]:
        return [a, b]


class MetricaPorPasillos(MetricaDistancia):
    """Distancia caminando por los pasillos, sin atravesar estanterías."""

    nombre = "Por pasillos (realista)"
    sigue_pasillos = True

    def __init__(self, almacen: Almacen) -> None:
        self._almacen = almacen

    # ------------------------------------------------------------------ #
    # Paso 1: ajustar cada punto a la red de pasillos
    # ------------------------------------------------------------------ #
    def _ajustar(self, punto: Punto) -> tuple[int | None, Punto]:
        """Ubica un punto sobre la red de caminata.

        Devuelve ``(pasillo, punto_en_la_red)``:
          * Si el punto está en la franja de un pasillo (un producto), se
            "proyecta" sobre el eje del pasillo: (x_eje, y).
          * Si no está en ningún pasillo (el INICIO), se considera sobre el
            pasillo transversal frontal y el pasillo es ``None``.
        """
        x, y = punto
        for pasillo in range(1, Almacen.NUM_PASILLOS + 1):
            x_eje = self._almacen.x_eje_pasillo(pasillo)
            if abs(x - x_eje) <= Almacen.DESPLAZAMIENTO_LATERAL + 1e-6:
                return pasillo, (x_eje, y)
        return None, (x, Almacen.Y_PASILLO_FRONTAL)

    # ------------------------------------------------------------------ #
    # Paso 2: distancia y camino sobre la red
    # ------------------------------------------------------------------ #
    def _largos_por_transversal(self, qa: Punto, qb: Punto) -> tuple[float, float]:
        """Largo del camino por el pasillo frontal y por el trasero."""
        lateral = abs(qa[0] - qb[0])
        por_el_frente = (qa[1] - Almacen.Y_PASILLO_FRONTAL) + (qb[1] - Almacen.Y_PASILLO_FRONTAL) + lateral
        por_el_fondo = (Almacen.Y_PASILLO_TRASERO - qa[1]) + (Almacen.Y_PASILLO_TRASERO - qb[1]) + lateral
        return por_el_frente, por_el_fondo

    def distancia(self, a: Punto, b: Punto) -> float:
        pasillo_a, qa = self._ajustar(a)
        pasillo_b, qb = self._ajustar(b)
        if pasillo_a is not None and pasillo_a == pasillo_b:
            return abs(qa[1] - qb[1])  # mismo pasillo: se camina por el eje
        return min(self._largos_por_transversal(qa, qb))

    def camino(self, a: Punto, b: Punto) -> list[Punto]:
        pasillo_a, qa = self._ajustar(a)
        pasillo_b, qb = self._ajustar(b)
        if pasillo_a is not None and pasillo_a == pasillo_b:
            return [qa, qb]
        por_el_frente, por_el_fondo = self._largos_por_transversal(qa, qb)
        y_cruce = Almacen.Y_PASILLO_FRONTAL if por_el_frente <= por_el_fondo else Almacen.Y_PASILLO_TRASERO
        # salir del pasillo -> cruzar por el transversal -> entrar al otro pasillo
        return [qa, (qa[0], y_cruce), (qb[0], y_cruce), qb]
