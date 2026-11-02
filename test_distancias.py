"""Pruebas de las métricas de distancia (euclidiana y por pasillos).

Ejecutar desde la raíz del proyecto:
    python -m unittest discover -s tests -t . -v
"""
import itertools
import math
import random
import unittest

from pickflow.modelo.almacen import Almacen
from pickflow.modelo.distancias import MetricaEuclidiana, MetricaPorPasillos
from pickflow.modelo.planificador import PlanificadorRutas
from pickflow.modelo.tsp import (
    AlgoritmoGenetico,
    VecinoMasCercano,
    construir_matriz_distancias,
    distancia_euclidiana,
    longitud_ruta,
)


def largo_camino(camino):
    return sum(math.dist(a, b) for a, b in zip(camino, camino[1:]))


class MetricaPorPasillosTests(unittest.TestCase):
    def setUp(self):
        self.almacen = Almacen()
        self.metrica = MetricaPorPasillos(self.almacen)
        self.puntos = [Almacen.DEPOSITO] + [p.posicion for p in self.almacen.productos]

    def pos(self, codigo):
        return self.almacen.obtener(codigo).posicion

    def test_el_inicio_esta_sobre_el_pasillo_transversal_frontal(self):
        self.assertEqual(Almacen.DEPOSITO[1], Almacen.Y_PASILLO_FRONTAL)
        pasillo, punto = self.metrica._ajustar(Almacen.DEPOSITO)
        self.assertIsNone(pasillo)
        self.assertEqual(punto, Almacen.DEPOSITO)

    def test_mismo_pasillo_se_camina_por_el_eje(self):
        # Lados opuestos del pasillo 1, filas 1 y 8: |10 - 45| = 35 m.
        d = self.metrica.distancia(self.pos("P1-I-01"), self.pos("P1-D-08"))
        self.assertAlmostEqual(d, 35.0)

    def test_pasillos_vecinos_cruzan_por_el_frente(self):
        # Fila 1 (y=10): bajar 6 m al transversal frontal + 12 m + subir 6 m.
        d = self.metrica.distancia(self.pos("P1-D-01"), self.pos("P2-I-01"))
        self.assertAlmostEqual(d, 6 + 12 + 6)

    def test_extremos_en_fila_alta_cruzan_por_el_fondo(self):
        # Fila 8 (y=45): subir 7 m al transversal trasero + 48 m + bajar 7 m.
        d = self.metrica.distancia(self.pos("P1-D-08"), self.pos("P5-I-08"))
        self.assertAlmostEqual(d, 7 + 48 + 7)

    def test_desde_el_inicio(self):
        # INICIO (4, 4) -> P1-D-01 (x eje = 12, y = 10): 8 m por el transversal + 6 m.
        d = self.metrica.distancia(Almacen.DEPOSITO, self.pos("P1-D-01"))
        self.assertAlmostEqual(d, 8 + 6)

    def test_el_camino_mide_exactamente_la_distancia(self):
        for a in self.puntos:
            for b in self.puntos:
                self.assertAlmostEqual(largo_camino(self.metrica.camino(a, b)), self.metrica.distancia(a, b))

    def test_simetria_y_desigualdad_triangular(self):
        muestra = random.Random(1).sample(self.puntos, 25)
        for a, b in itertools.product(muestra, repeat=2):
            self.assertAlmostEqual(self.metrica.distancia(a, b), self.metrica.distancia(b, a))
        for a, b, c in itertools.product(muestra, repeat=3):
            self.assertLessEqual(
                self.metrica.distancia(a, c),
                self.metrica.distancia(a, b) + self.metrica.distancia(b, c) + 1e-9,
            )

    def test_en_pasillos_distintos_es_mayor_que_la_linea_recta(self):
        # Entre pasillos distintos hay que rodear las estanterías, nunca es menos.
        # (En el mismo pasillo puede diferir unos centímetros porque el operario
        # recolecta desde el eje y no se cuenta el ancho del pasillo.)
        for a in self.almacen.productos:
            for b in self.almacen.productos:
                if a.pasillo != b.pasillo:
                    self.assertGreaterEqual(
                        self.metrica.distancia(a.posicion, b.posicion),
                        distancia_euclidiana(a.posicion, b.posicion) - 1e-9,
                    )

    def test_el_camino_nunca_atraviesa_una_estanteria(self):
        # Todo tramo del camino debe ser horizontal sobre un transversal o
        # vertical sobre el eje de un pasillo.
        ejes = {self.almacen.x_eje_pasillo(k) for k in range(1, Almacen.NUM_PASILLOS + 1)}
        transversales = {Almacen.Y_PASILLO_FRONTAL, Almacen.Y_PASILLO_TRASERO}
        rng = random.Random(2)
        for _ in range(300):
            a, b = rng.choice(self.puntos), rng.choice(self.puntos)
            for (x0, y0), (x1, y1) in zip(*[self.metrica.camino(a, b)[i:] for i in (0, 1)]):
                horizontal = abs(y0 - y1) < 1e-9 and y0 in transversales
                vertical = abs(x0 - x1) < 1e-9 and any(abs(x0 - e) < 1e-9 for e in ejes)
                self.assertTrue(horizontal or vertical or (x0, y0) == (x1, y1), ((x0, y0), (x1, y1)))


class MetricaEuclidianaTests(unittest.TestCase):
    def test_coincide_con_la_formula(self):
        m = MetricaEuclidiana()
        self.assertAlmostEqual(m.distancia((0, 0), (3, 4)), 5.0)
        self.assertEqual(m.camino((0, 0), (3, 4)), [(0, 0), (3, 4)])
        self.assertFalse(m.sigue_pasillos)

    def test_camino_completo_une_los_puntos_sin_repetir(self):
        self.assertEqual(MetricaEuclidiana().camino_completo([(0, 0), (1, 1), (2, 2)]), [(0, 0), (1, 1), (2, 2)])


class MatrizConMetricaTests(unittest.TestCase):
    def test_la_matriz_usa_la_funcion_indicada(self):
        puntos = [(0, 0), (3, 4)]
        self.assertAlmostEqual(construir_matriz_distancias(puntos)[0][1], 5.0)  # por defecto: euclidiana
        manhattan = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
        self.assertAlmostEqual(construir_matriz_distancias(puntos, manhattan)[0][1], 7.0)


class IntegracionConAlgoritmosTests(unittest.TestCase):
    """Los algoritmos no cambian: solo leen la matriz que se les entregue."""

    def setUp(self):
        self.almacen = Almacen()
        self.planificador = PlanificadorRutas(
            self.almacen,
            [VecinoMasCercano(), AlgoritmoGenetico(semilla=3)],
            [MetricaEuclidiana(), MetricaPorPasillos(self.almacen)],
        )

    def test_la_ruta_dibujada_mide_lo_que_dice_la_metrica(self):
        pedido = self.almacen.generar_pedido_aleatorio(15, random.Random(4))
        for algoritmo in self.planificador.nombres_algoritmos:
            for metrica in self.planificador.nombres_metricas:
                r = self.planificador.planificar(pedido, algoritmo, metrica)
                self.assertAlmostEqual(largo_camino(r.ruta_puntos), r.distancia_optimizada, places=6)
                self.assertAlmostEqual(largo_camino(r.ruta_original_puntos), r.distancia_original, places=6)
                self.assertEqual(r.sigue_pasillos, metrica.startswith("Por pasillos"))

    def test_con_metrica_por_pasillos_la_distancia_real_coincide(self):
        pedido = self.almacen.generar_pedido_aleatorio(12, random.Random(5))
        r = self.planificador.planificar(pedido, "Vecino más cercano", "Por pasillos (realista)")
        self.assertAlmostEqual(r.distancia_real_optimizada, r.distancia_optimizada)
        self.assertAlmostEqual(r.distancia_real_original, r.distancia_original)

    def test_la_distancia_real_siempre_se_calcula_por_pasillos(self):
        pedido = self.almacen.generar_pedido_aleatorio(12, random.Random(5))
        r = self.planificador.planificar(pedido, "Vecino más cercano", "Euclidiana (línea recta)")
        self.assertGreater(r.distancia_real_optimizada, r.distancia_optimizada)

    def test_optimizar_con_la_metrica_real_nunca_camina_mas_que_con_la_euclidiana(self):
        # El genético con la métrica real parte sembrado con el vecino más cercano
        # y el orden original medidos en pasillos, así que no puede quedar peor
        # que ellos al medir lo que realmente se camina.
        for semilla in range(6):
            pedido = self.almacen.generar_pedido_aleatorio(20, random.Random(semilla))
            real = self.planificador.planificar(pedido, "Algoritmo genético", "Por pasillos (realista)")
            self.assertLessEqual(real.distancia_optimizada, real.distancia_original + 1e-9)
            vmc = self.planificador.planificar(pedido, "Vecino más cercano", "Por pasillos (realista)")
            self.assertLessEqual(real.distancia_optimizada, vmc.distancia_optimizada + 1e-9)


if __name__ == "__main__":
    unittest.main()
