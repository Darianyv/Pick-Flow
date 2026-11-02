"""Planificador de rutas: une el almacén, el pedido, los algoritmos y la métrica.

Es la "puerta de entrada" del modelo para el controlador. Recibe un pedido, el
nombre del algoritmo y el nombre de la métrica de distancia elegidos, y devuelve
un ``ResultadoOptimizacion`` con todo lo que la interfaz necesita mostrar: orden
de recolección, distancias, porcentaje de eficiencia, camino a dibujar y la
explicación paso a paso.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Sequence

from .almacen import Almacen, Pedido, Producto, Punto
from .distancias import MetricaDistancia, MetricaPorPasillos
from .tsp import (
    AlgoritmoTSP,
    construir_matriz_distancias,
    eficiencia_porcentual,
    longitud_ruta,
)


@dataclass(frozen=True)
class ResultadoOptimizacion:
    """Resultado completo de una optimización (objeto de solo lectura).

    Atributos:
        algoritmo: Nombre del algoritmo usado.
        metrica: Nombre de la métrica con la que se midieron las distancias.
        sigue_pasillos: True si el camino dibujado sigue la red de pasillos.
        productos_optimizados: Productos en el orden óptimo de recolección.
        productos_originales: Productos en el orden original del pedido.
        distancia_original: Metros del orden original, según la métrica elegida.
        distancia_optimizada: Metros del orden optimizado, según la métrica elegida.
        distancia_real_original: Metros que se caminarían de verdad (por pasillos)
            siguiendo el orden original.
        distancia_real_optimizada: Metros que se caminarían de verdad (por pasillos)
            siguiendo el orden optimizado.
        tiempo: Segundos que tardó el cálculo.
        pasos: Explicación paso a paso del algoritmo.
        ruta_puntos: Camino (x, y) de la ruta optimizada, de INICIO a INICIO.
        ruta_original_puntos: Camino (x, y) de la ruta original, de INICIO a INICIO.
    """

    algoritmo: str
    metrica: str
    sigue_pasillos: bool
    productos_optimizados: tuple[Producto, ...]
    productos_originales: tuple[Producto, ...]
    distancia_original: float
    distancia_optimizada: float
    distancia_real_original: float
    distancia_real_optimizada: float
    tiempo: float
    pasos: tuple[str, ...]
    ruta_puntos: tuple[Punto, ...]
    ruta_original_puntos: tuple[Punto, ...]

    @property
    def ahorro_metros(self) -> float:
        """Metros que se dejan de caminar respecto al orden original."""
        return self.distancia_original - self.distancia_optimizada

    @property
    def eficiencia_pct(self) -> float:
        """Porcentaje de distancia ahorrado respecto al orden original."""
        return eficiencia_porcentual(self.distancia_original, self.distancia_optimizada)

    @property
    def eficiencia_real_pct(self) -> float:
        """Porcentaje ahorrado midiendo con la distancia real por pasillos."""
        return eficiencia_porcentual(self.distancia_real_original, self.distancia_real_optimizada)


class PlanificadorRutas:
    """Calcula la ruta de recolección con el algoritmo y la métrica indicados."""

    def __init__(
        self,
        almacen: Almacen,
        algoritmos: Sequence[AlgoritmoTSP],
        metricas: Sequence[MetricaDistancia],
    ) -> None:
        if not algoritmos:
            raise ValueError("Se necesita al menos un algoritmo.")
        if not metricas:
            raise ValueError("Se necesita al menos una métrica de distancia.")
        self._almacen = almacen
        self._algoritmos = {algoritmo.nombre: algoritmo for algoritmo in algoritmos}
        self._metricas = {metrica.nombre: metrica for metrica in metricas}
        # Referencia para medir la distancia REAL que se caminaría, sin importar
        # con qué métrica se haya optimizado la ruta.
        self._metrica_real = MetricaPorPasillos(almacen)

    @property
    def nombres_algoritmos(self) -> list[str]:
        """Nombres de los algoritmos disponibles, en el orden en que se registraron."""
        return list(self._algoritmos)

    @property
    def nombres_metricas(self) -> list[str]:
        """Nombres de las métricas disponibles, en el orden en que se registraron."""
        return list(self._metricas)

    def planificar(
        self, pedido: Pedido, nombre_algoritmo: str, nombre_metrica: str
    ) -> ResultadoOptimizacion:
        """Optimiza el orden de recolección de ``pedido``.

        Lanza ``ValueError`` si el pedido está vacío o el algoritmo/métrica no existe.
        """
        if len(pedido) == 0:
            raise ValueError("El pedido está vacío: agrega productos antes de optimizar.")
        try:
            algoritmo = self._algoritmos[nombre_algoritmo]
        except KeyError:
            raise ValueError(f"Algoritmo desconocido: {nombre_algoritmo!r}.") from None
        try:
            metrica = self._metricas[nombre_metrica]
        except KeyError:
            raise ValueError(f"Métrica de distancia desconocida: {nombre_metrica!r}.") from None

        inicio = time.perf_counter()
        originales = pedido.productos

        # Puntos: índice 0 = INICIO, índices 1..n = productos en orden original.
        puntos = [Almacen.DEPOSITO] + [p.posicion for p in originales]
        etiquetas = ["INICIO"] + [p.codigo for p in originales]

        # La métrica elegida decide cómo se llena la matriz. Los algoritmos
        # solo ven esta tabla de números y no saben nada de pasillos.
        matriz = construir_matriz_distancias(puntos, metrica.distancia)
        solucion = algoritmo.resolver(matriz, etiquetas)

        orden_original = list(range(1, len(originales) + 1))
        optimizados = tuple(originales[i - 1] for i in solucion.ruta)

        # Distancia real (por pasillos) de ambos órdenes, para comparar con la realidad.
        matriz_real = construir_matriz_distancias(puntos, self._metrica_real.distancia)

        return ResultadoOptimizacion(
            algoritmo=algoritmo.nombre,
            metrica=metrica.nombre,
            sigue_pasillos=metrica.sigue_pasillos,
            productos_optimizados=optimizados,
            productos_originales=originales,
            distancia_original=longitud_ruta(orden_original, matriz),
            distancia_optimizada=solucion.distancia,
            distancia_real_original=longitud_ruta(orden_original, matriz_real),
            distancia_real_optimizada=longitud_ruta(solucion.ruta, matriz_real),
            tiempo=time.perf_counter() - inicio,
            pasos=tuple(solucion.pasos),
            ruta_puntos=tuple(metrica.camino_completo(self._puntos_de_ruta(optimizados))),
            ruta_original_puntos=tuple(metrica.camino_completo(self._puntos_de_ruta(originales))),
        )

    @staticmethod
    def _puntos_de_ruta(productos: Sequence[Producto]) -> list[Punto]:
        """Puntos (x, y) de la ruta completa: INICIO, productos y regreso a INICIO."""
        return [Almacen.DEPOSITO, *(p.posicion for p in productos), Almacen.DEPOSITO]
