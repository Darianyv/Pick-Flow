"""Problema del Viajante (TSP) aplicado al picking: algoritmos programados desde cero.

=====================================================================
IDEA GENERAL
=====================================================================
El operario parte del INICIO, debe pasar por cada producto del pedido exactamente
una vez y regresar al INICIO. Queremos el orden de visita que minimice la
distancia caminada. Eso es el TSP (Traveling Salesperson Problem).

Con n productos existen n! órdenes posibles (con 20 productos, más de 2.4 x 10^18),
así que probarlos todos es imposible. Por eso se usan HEURÍSTICAS: métodos que
encuentran soluciones muy buenas (no siempre la óptima) en muy poco tiempo.

Este módulo implementa dos, sin librerías externas:

  1. Vecino más cercano (heurística voraz).
  2. Algoritmo genético simple (metaheurística inspirada en la evolución).

=====================================================================
CONVENCIÓN DE ÍNDICES (importante para entender el código)
=====================================================================
Se construye una lista de puntos donde:

    índice 0       -> INICIO (muelle de despacho)
    índices 1..n   -> los n productos del pedido, en su orden original

``matriz[i][j]`` es la distancia entre el punto i y el punto j. Según la métrica
elegida (ver ``distancias.py``) puede ser en línea recta o caminando por pasillos;
los algoritmos de este módulo no lo saben ni lo necesitan.

Una RUTA es una lista con los índices 1..n en el orden en que se visitan.
El INICIO (índice 0) no se escribe en la ruta: se asume al principio y al final.
Ejemplo con 3 productos:   ruta = [2, 3, 1]   significa   0 -> 2 -> 3 -> 1 -> 0
"""
from __future__ import annotations

import itertools
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Sequence

Punto = tuple[float, float]
Matriz = list[list[float]]
FuncionDistancia = Callable[[Punto, Punto], float]


# ======================================================================
# 1. MATEMÁTICA BÁSICA
# ======================================================================
def distancia_euclidiana(a: Punto, b: Punto) -> float:
    """Distancia en línea recta entre dos puntos (teorema de Pitágoras).

        d(a, b) = raíz( (xa - xb)^2 + (ya - yb)^2 )

    Ejemplo: de (0, 0) a (3, 4) la distancia es raíz(9 + 16) = 5.
    """
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return math.sqrt(dx * dx + dy * dy)


def construir_matriz_distancias(
    puntos: Sequence[Punto],
    funcion_distancia: FuncionDistancia = distancia_euclidiana,
) -> Matriz:
    """Calcula la distancia entre TODOS los pares de puntos.

    El resultado es una tabla cuadrada: ``matriz[i][j]`` = distancia de i a j.
    Es simétrica (ir de i a j cuesta lo mismo que de j a i) y su diagonal vale 0.
    Se calcula una sola vez; así los algoritmos solo consultan la tabla en lugar
    de repetir cálculos miles de veces.

    ``funcion_distancia`` decide QUÉ significa "distancia":
        * ``distancia_euclidiana`` (por defecto): línea recta entre los puntos.
        * Una distancia por pasillos (ver ``distancias.py``): camino real que
          camina el operario, sin atravesar las estanterías.

    Este es el único punto del programa donde se decide cómo se mide la
    distancia. Los algoritmos (vecino más cercano, genético) solo leen la
    matriz, así que funcionan igual con cualquiera de las dos.
    """
    n = len(puntos)
    matriz = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):  # solo la mitad superior; la otra es espejo
            d = funcion_distancia(puntos[i], puntos[j])
            matriz[i][j] = d
            matriz[j][i] = d
    return matriz


def longitud_ruta(ruta: Sequence[int], matriz: Matriz) -> float:
    """Distancia total de una ruta: INICIO -> productos en orden -> INICIO.

    Es la FUNCIÓN OBJETIVO del problema: la cantidad que queremos minimizar.
    """
    if not ruta:
        return 0.0
    total = matriz[0][ruta[0]]                  # del INICIO al primer producto
    for i in range(len(ruta) - 1):
        total += matriz[ruta[i]][ruta[i + 1]]   # de cada producto al siguiente
    total += matriz[ruta[-1]][0]                # del último producto al INICIO
    return total


def eficiencia_porcentual(distancia_original: float, distancia_optimizada: float) -> float:
    """Porcentaje de distancia ahorrada respecto a la original.

        eficiencia = (original - optimizada) / original x 100

    Ejemplo: de 200 m a 150 m -> (200 - 150) / 200 x 100 = 25 %.
    """
    if distancia_original <= 0:
        return 0.0
    return (distancia_original - distancia_optimizada) / distancia_original * 100.0


# ======================================================================
# 2. INTERFAZ COMÚN DE LOS ALGORITMOS
# ======================================================================
@dataclass
class SolucionTSP:
    """Resultado de un algoritmo.

    Atributos:
        ruta: Orden de visita (índices 1..n, sin el INICIO).
        distancia: Longitud total de la ruta, incluyendo el regreso al INICIO.
        pasos: Explicación paso a paso que la interfaz muestra en pantalla.
    """

    ruta: list[int]
    distancia: float
    pasos: list[str] = field(default_factory=list)


class AlgoritmoTSP(ABC):
    """Contrato que cumple cualquier algoritmo (patrón Estrategia).

    Gracias a esto, el resto del programa no necesita saber CÓMO se resuelve el
    TSP: basta con llamar a ``resolver``. Agregar un algoritmo nuevo es crear una
    subclase, sin tocar la interfaz ni el controlador.
    """

    nombre: str = "Algoritmo"

    @abstractmethod
    def resolver(self, matriz: Matriz, etiquetas: Sequence[str]) -> SolucionTSP:
        """Calcula la ruta. ``etiquetas[i]`` es el nombre legible del punto i."""


# ======================================================================
# 3. ALGORITMO 1: VECINO MÁS CERCANO
# ======================================================================
class VecinoMasCercano(AlgoritmoTSP):
    """Heurística voraz: desde donde estés, ve siempre al producto más cercano.

    Pasos:
        1. Parte del INICIO.
        2. Entre los productos que faltan, elige el más cercano a la posición actual.
        3. Ve a él y márcalo como visitado.
        4. Repite desde el paso 2 hasta que no falte ninguno.
        5. Regresa al INICIO.

    Ventajas: muy simple, muy rápida (complejidad O(n^2)) y fácil de explicar.
    Desventaja: es "miope". Decide mirando solo el siguiente paso y puede dejar
    productos lejanos para el final, obligando a un regreso largo, por lo que no
    garantiza la ruta óptima. En las pruebas de este proyecto (pedidos de 9
    productos, comparados contra la solución exacta por fuerza bruta) quedó en
    promedio 6.7 % por encima del óptimo, y hasta 12.4 % en el peor caso.
    """

    nombre = "Vecino más cercano"

    def resolver(self, matriz: Matriz, etiquetas: Sequence[str]) -> SolucionTSP:
        n = len(matriz) - 1                       # cantidad de productos
        por_visitar = list(range(1, n + 1))       # productos que aún faltan
        ruta: list[int] = []
        actual = 0                                # empezamos en el INICIO
        pasos = [
            f"VECINO MÁS CERCANO con {n} producto(s).",
            "Regla: desde donde estoy, voy siempre al producto más cercano que falte.",
            "",
        ]

        numero_paso = 1
        while por_visitar:
            # Buscar, entre los pendientes, el más cercano al punto actual.
            mejor = por_visitar[0]
            for candidato in por_visitar:
                if matriz[actual][candidato] < matriz[actual][mejor]:
                    mejor = candidato

            pasos.append(
                f"Paso {numero_paso:>2}: {etiquetas[actual]} -> {etiquetas[mejor]}  "
                f"({matriz[actual][mejor]:.1f} m, el más cercano de {len(por_visitar)})"
            )
            ruta.append(mejor)
            por_visitar.remove(mejor)
            actual = mejor
            numero_paso += 1

        distancia = longitud_ruta(ruta, matriz)
        pasos.append(
            f"Regreso: {etiquetas[actual]} -> {etiquetas[0]}  ({matriz[actual][0]:.1f} m)"
        )
        pasos.append("")
        pasos.append(f"Distancia total de la ruta: {distancia:.1f} m")
        return SolucionTSP(ruta=ruta, distancia=distancia, pasos=pasos)


# ======================================================================
# 4. ALGORITMO 2: ALGORITMO GENÉTICO SIMPLE
# ======================================================================
@dataclass(frozen=True)
class ConfigAG:
    """Parámetros del algoritmo genético (se pueden ajustar para experimentar).

    Atributos:
        tamano_poblacion: Cuántas rutas candidatas existen en cada generación.
        generaciones: Cuántas veces se repite el ciclo de evolución.
        prob_cruce: Probabilidad de que dos padres se crucen (si no, el hijo
            es copia del primer padre).
        prob_mutacion: Probabilidad de que un hijo sufra una mutación.
        tamano_torneo: Cuántas rutas compiten en cada torneo de selección.
        elitismo: Cuántas de las mejores rutas pasan intactas a la siguiente
            generación (garantiza que la mejor solución nunca se pierde).
        sembrar_soluciones_iniciales: Si es True, la población inicial incluye
            la ruta del vecino más cercano y el orden original del pedido.
            Así el algoritmo genético nunca devuelve algo peor que ellas.
    """

    tamano_poblacion: int = 100
    generaciones: int = 300
    prob_cruce: float = 0.9
    prob_mutacion: float = 0.3
    tamano_torneo: int = 3
    elitismo: int = 2
    sembrar_soluciones_iniciales: bool = True

    def __post_init__(self) -> None:
        if self.tamano_poblacion < 4:
            raise ValueError("La población debe tener al menos 4 individuos.")
        if self.generaciones < 1:
            raise ValueError("Debe haber al menos 1 generación.")
        if not 0 <= self.prob_cruce <= 1 or not 0 <= self.prob_mutacion <= 1:
            raise ValueError("Las probabilidades deben estar entre 0 y 1.")
        if not 1 <= self.tamano_torneo <= self.tamano_poblacion:
            raise ValueError("El tamaño del torneo debe estar entre 1 y el tamaño de la población.")
        if not 0 <= self.elitismo < self.tamano_poblacion:
            raise ValueError("El elitismo debe ser menor que el tamaño de la población.")


def cruce_ox(padre1: Sequence[int], padre2: Sequence[int], rng: random.Random) -> list[int]:
    """Cruce por orden (Order Crossover, OX).

    En el TSP cada producto debe aparecer UNA sola vez, así que un cruce simple
    (mitad de un padre + mitad del otro) generaría rutas con productos repetidos
    o faltantes. OX evita ese problema:

        1. Se eligen dos puntos de corte al azar.
        2. El hijo hereda del padre 1 el tramo entre los cortes, en su misma posición.
        3. Los huecos restantes se llenan con los productos que faltan, en el
           orden en que aparecen en el padre 2.

    Ejemplo con cortes en las posiciones 2 y 4:
        padre1 = [1 2 3 4 5 6]   tramo heredado = [3 4 5]
        padre2 = [6 4 2 1 5 3]   restantes en orden del padre 2 = [6 2 1]
        hijo   = [6 2 | 3 4 5 | 1]   (siempre una permutación válida)
    """
    n = len(padre1)
    corte_a, corte_b = sorted(rng.sample(range(n), 2))
    hijo: list[int | None] = [None] * n
    hijo[corte_a : corte_b + 1] = padre1[corte_a : corte_b + 1]

    heredados = set(padre1[corte_a : corte_b + 1])
    restantes = [gen for gen in padre2 if gen not in heredados]

    siguiente = 0
    for posicion in range(n):
        if hijo[posicion] is None:
            hijo[posicion] = restantes[siguiente]
            siguiente += 1
    return [gen for gen in hijo if gen is not None]


def mutar_inversion(individuo: Sequence[int], rng: random.Random) -> list[int]:
    """Mutación por inversión: se invierte un tramo al azar de la ruta.

    Ejemplo: [1 2 3 4 5 6] con tramo entre las posiciones 1 y 4 -> [1 5 4 3 2 6].

    La mutación introduce variedad que el cruce por sí solo no crea. Invertir un
    tramo equivale a "deshacer un cruce de caminos" (la idea del 2-opt), y suele
    acortar la ruta cuando el recorrido tenía un lazo innecesario.
    """
    mutado = list(individuo)
    a, b = sorted(rng.sample(range(len(mutado)), 2))
    mutado[a : b + 1] = reversed(mutado[a : b + 1])
    return mutado


def _resolver_exhaustivo(matriz: Matriz) -> list[int]:
    """Prueba todas las permutaciones. Solo se usa con 3 productos o menos."""
    n = len(matriz) - 1
    return list(min(itertools.permutations(range(1, n + 1)), key=lambda r: longitud_ruta(r, matriz)))


class AlgoritmoGenetico(AlgoritmoTSP):
    """Algoritmo genético: evoluciona una población de rutas candidatas.

    Analogía biológica:
        individuo  = una ruta posible (permutación de los productos)
        aptitud    = qué tan corta es la ruta (menor distancia = mejor)
        población  = conjunto de rutas candidatas
        generación = una iteración del algoritmo

    Ciclo (se repite ``generaciones`` veces):
        1. EVALUAR      calcular la distancia de cada ruta y ordenarlas.
        2. ELITISMO     las mejores pasan directo a la siguiente generación.
        3. SELECCIONAR  elegir padres por torneo (gana la ruta más corta de
                        un pequeño grupo al azar).
        4. CRUZAR       combinar dos padres para crear un hijo (cruce OX).
        5. MUTAR        con cierta probabilidad, alterar al hijo (inversión).
        6. REEMPLAZAR   la nueva población sustituye a la anterior.

    Es estocástico: usa azar, por lo que dos ejecuciones pueden diferir. Con una
    semilla fija el resultado es reproducible. No garantiza el óptimo, pero con
    pocos parámetros encuentra rutas muy cercanas a él.
    """

    nombre = "Algoritmo genético"

    def __init__(self, config: ConfigAG | None = None, semilla: int | None = None) -> None:
        self.config = config or ConfigAG()
        self.semilla = semilla

    def resolver(self, matriz: Matriz, etiquetas: Sequence[str]) -> SolucionTSP:
        n = len(matriz) - 1
        cfg = self.config

        # Con 3 productos o menos hay a lo sumo 6 rutas: se prueban todas.
        if n <= 3:
            ruta = _resolver_exhaustivo(matriz)
            distancia = longitud_ruta(ruta, matriz)
            return SolucionTSP(
                ruta,
                distancia,
                [
                    f"Solo hay {n} producto(s): se prueban todas las rutas posibles.",
                    f"Distancia total de la ruta: {distancia:.1f} m",
                ],
            )

        rng = random.Random(self.semilla)
        genes = list(range(1, n + 1))
        pasos = [
            f"ALGORITMO GENÉTICO con {n} producto(s).",
            f"Población: {cfg.tamano_poblacion} rutas | Generaciones: {cfg.generaciones}",
            f"Cruce OX (prob. {cfg.prob_cruce}) | Mutación por inversión (prob. {cfg.prob_mutacion})",
            f"Selección por torneo de {cfg.tamano_torneo} | Elitismo: {cfg.elitismo}",
            "",
        ]

        # --- 1. Población inicial ---------------------------------------
        poblacion: list[list[int]] = []
        if cfg.sembrar_soluciones_iniciales:
            ruta_vmc = VecinoMasCercano().resolver(matriz, etiquetas).ruta
            poblacion.append(ruta_vmc)
            poblacion.append(genes[:])  # orden original del pedido
            pasos.append(
                "Siembra: se incluyen el vecino más cercano "
                f"({longitud_ruta(ruta_vmc, matriz):.1f} m) y el orden original "
                f"({longitud_ruta(genes, matriz):.1f} m)."
            )
        while len(poblacion) < cfg.tamano_poblacion:
            individuo = genes[:]
            rng.shuffle(individuo)  # ruta completamente aleatoria
            poblacion.append(individuo)
        pasos.append(f"Población inicial: {len(poblacion)} rutas.")
        pasos.append("")

        # --- 2. Evolución ------------------------------------------------
        mejor_ruta = poblacion[0]
        mejor_distancia = float("inf")
        mejor_generacion = 0
        intervalo_registro = max(1, cfg.generaciones // 6)

        for generacion in range(cfg.generaciones + 1):
            # EVALUAR: distancia de cada ruta, de menor a mayor.
            evaluada = sorted(
                ((longitud_ruta(ind, matriz), ind) for ind in poblacion),
                key=lambda par: par[0],
            )
            if evaluada[0][0] < mejor_distancia - 1e-9:
                mejor_distancia, mejor_ruta = evaluada[0][0], evaluada[0][1][:]
                mejor_generacion = generacion

            if generacion % intervalo_registro == 0 or generacion == cfg.generaciones:
                pasos.append(f"Generación {generacion:>4}: mejor ruta = {mejor_distancia:.1f} m")
            if generacion == cfg.generaciones:
                break

            # ELITISMO: las mejores rutas se copian tal cual.
            siguiente = [ind[:] for _, ind in evaluada[: cfg.elitismo]]

            # Completar la nueva generación con hijos.
            while len(siguiente) < cfg.tamano_poblacion:
                padre1 = self._seleccion_torneo(evaluada, rng)
                padre2 = self._seleccion_torneo(evaluada, rng)
                if rng.random() < cfg.prob_cruce:
                    hijo = cruce_ox(padre1, padre2, rng)
                else:
                    hijo = padre1[:]
                if rng.random() < cfg.prob_mutacion:
                    hijo = mutar_inversion(hijo, rng)
                siguiente.append(hijo)

            poblacion = siguiente

        pasos.append("")
        pasos.append(f"La mejor ruta apareció en la generación {mejor_generacion}.")
        pasos.append(f"Distancia total de la ruta: {mejor_distancia:.1f} m")
        return SolucionTSP(ruta=mejor_ruta, distancia=mejor_distancia, pasos=pasos)

    def _seleccion_torneo(
        self, evaluada: Sequence[tuple[float, list[int]]], rng: random.Random
    ) -> list[int]:
        """Selección por torneo: se sortean k rutas y gana la más corta.

        Las rutas buenas tienen más probabilidad de ser padres, pero las malas
        también pueden serlo (con baja probabilidad), lo que mantiene la
        diversidad genética de la población.
        """
        competidores = rng.sample(list(evaluada), self.config.tamano_torneo)
        ganador = min(competidores, key=lambda par: par[0])
        return ganador[1]
