"""Pruebas del modelo (no requieren interfaz gráfica).

Ejecutar desde la raíz del proyecto:
    python -m unittest discover -s tests -t . -v
"""
import itertools
import random
import unittest

from pickflow.modelo.almacen import Almacen, Pedido
from pickflow.modelo.distancias import MetricaEuclidiana, MetricaPorPasillos
from pickflow.modelo.planificador import PlanificadorRutas
from pickflow.modelo.tsp import (
    AlgoritmoGenetico,
    ConfigAG,
    VecinoMasCercano,
    construir_matriz_distancias,
    cruce_ox,
    distancia_euclidiana,
    eficiencia_porcentual,
    longitud_ruta,
    mutar_inversion,
)


def etiquetas(n):
    return ["INICIO"] + [f"X{i}" for i in range(1, n + 1)]


class MatematicaTests(unittest.TestCase):
    def test_distancia_pitagorica(self):
        self.assertAlmostEqual(distancia_euclidiana((0, 0), (3, 4)), 5.0)
        self.assertAlmostEqual(distancia_euclidiana((2, 2), (2, 2)), 0.0)

    def test_matriz_simetrica_con_diagonal_cero(self):
        puntos = [(0, 0), (3, 4), (6, 8), (1, 7)]
        m = construir_matriz_distancias(puntos)
        for i in range(4):
            self.assertEqual(m[i][i], 0.0)
            for j in range(4):
                self.assertAlmostEqual(m[i][j], m[j][i])
        self.assertAlmostEqual(m[0][1], 5.0)
        self.assertAlmostEqual(m[0][2], 10.0)

    def test_longitud_ruta_en_linea_recta(self):
        # INICIO(0,0), A(10,0), B(3,0), C(6,0)
        m = construir_matriz_distancias([(0, 0), (10, 0), (3, 0), (6, 0)])
        self.assertAlmostEqual(longitud_ruta([1, 2, 3], m), 10 + 7 + 3 + 6)  # A,B,C
        self.assertAlmostEqual(longitud_ruta([2, 3, 1], m), 3 + 3 + 4 + 10)  # B,C,A
        self.assertEqual(longitud_ruta([], m), 0.0)

    def test_eficiencia_porcentual(self):
        self.assertAlmostEqual(eficiencia_porcentual(200, 150), 25.0)
        self.assertAlmostEqual(eficiencia_porcentual(100, 100), 0.0)
        self.assertAlmostEqual(eficiencia_porcentual(100, 120), -20.0)
        self.assertEqual(eficiencia_porcentual(0, 0), 0.0)


class VecinoMasCercanoTests(unittest.TestCase):
    def test_orden_en_linea_recta(self):
        m = construir_matriz_distancias([(0, 0), (10, 0), (3, 0), (6, 0)])
        sol = VecinoMasCercano().resolver(m, etiquetas(3))
        self.assertEqual(sol.ruta, [2, 3, 1])  # B(3) -> C(6) -> A(10)
        self.assertAlmostEqual(sol.distancia, 20.0)

    def test_visita_cada_producto_una_vez(self):
        rng = random.Random(1)
        puntos = [(0, 0)] + [(rng.uniform(0, 70), rng.uniform(0, 60)) for _ in range(25)]
        sol = VecinoMasCercano().resolver(construir_matriz_distancias(puntos), etiquetas(25))
        self.assertEqual(sorted(sol.ruta), list(range(1, 26)))

    def test_un_solo_producto(self):
        m = construir_matriz_distancias([(0, 0), (3, 4)])
        sol = VecinoMasCercano().resolver(m, etiquetas(1))
        self.assertEqual(sol.ruta, [1])
        self.assertAlmostEqual(sol.distancia, 10.0)


class OperadoresGeneticosTests(unittest.TestCase):
    def test_cruce_ox_conserva_permutacion(self):
        rng = random.Random(3)
        for _ in range(200):
            n = rng.randint(4, 30)
            p1 = list(range(1, n + 1)); rng.shuffle(p1)
            p2 = list(range(1, n + 1)); rng.shuffle(p2)
            hijo = cruce_ox(p1, p2, rng)
            self.assertEqual(sorted(hijo), list(range(1, n + 1)))

    def test_cruce_ox_ejemplo_documentado(self):
        class Fijo(random.Random):
            def sample(self, poblacion, k):
                return [2, 4]  # cortes en las posiciones 2 y 4

        hijo = cruce_ox([1, 2, 3, 4, 5, 6], [6, 4, 2, 1, 5, 3], Fijo())
        self.assertEqual(hijo, [6, 2, 3, 4, 5, 1])

    def test_mutacion_conserva_permutacion_y_no_modifica_el_original(self):
        rng = random.Random(4)
        original = list(range(1, 15))
        for _ in range(100):
            mutado = mutar_inversion(original, rng)
            self.assertEqual(sorted(mutado), original)
        self.assertEqual(original, list(range(1, 15)))

    def test_config_invalida(self):
        for kwargs in ({"tamano_poblacion": 2}, {"generaciones": 0}, {"prob_cruce": 1.5},
                       {"tamano_torneo": 0}, {"elitismo": 100}):
            with self.assertRaises(ValueError):
                ConfigAG(**kwargs)


class AlgoritmoGeneticoTests(unittest.TestCase):
    def _puntos(self, n, semilla):
        rng = random.Random(semilla)
        return [(4, 4)] + [(rng.uniform(0, 70), rng.uniform(5, 55)) for _ in range(n)]

    def test_resultado_es_permutacion_valida(self):
        m = construir_matriz_distancias(self._puntos(20, 1))
        sol = AlgoritmoGenetico(semilla=1).resolver(m, etiquetas(20))
        self.assertEqual(sorted(sol.ruta), list(range(1, 21)))
        self.assertAlmostEqual(sol.distancia, longitud_ruta(sol.ruta, m))

    def test_nunca_es_peor_que_vecino_cercano_ni_que_el_orden_original(self):
        for semilla in range(8):
            m = construir_matriz_distancias(self._puntos(25, semilla))
            vmc = VecinoMasCercano().resolver(m, etiquetas(25)).distancia
            original = longitud_ruta(list(range(1, 26)), m)
            ag = AlgoritmoGenetico(semilla=semilla).resolver(m, etiquetas(25)).distancia
            self.assertLessEqual(ag, vmc + 1e-9)
            self.assertLessEqual(ag, original + 1e-9)

    def test_encuentra_el_optimo_en_problemas_pequenos(self):
        for semilla in range(5):
            m = construir_matriz_distancias(self._puntos(7, semilla))
            optimo = min(longitud_ruta(p, m) for p in itertools.permutations(range(1, 8)))
            ag = AlgoritmoGenetico(semilla=semilla).resolver(m, etiquetas(7)).distancia
            self.assertAlmostEqual(ag, optimo, places=6)

    def test_sin_siembra_tambien_mejora_mucho_el_azar(self):
        m = construir_matriz_distancias(self._puntos(20, 2))
        aleatoria = longitud_ruta(list(range(1, 21)), m)
        ag = AlgoritmoGenetico(ConfigAG(sembrar_soluciones_iniciales=False), semilla=2)
        self.assertLess(ag.resolver(m, etiquetas(20)).distancia, aleatoria * 0.6)

    def test_reproducible_con_semilla(self):
        m = construir_matriz_distancias(self._puntos(15, 5))
        a = AlgoritmoGenetico(semilla=9).resolver(m, etiquetas(15)).ruta
        b = AlgoritmoGenetico(semilla=9).resolver(m, etiquetas(15)).ruta
        self.assertEqual(a, b)

    def test_pocos_productos(self):
        for n in (1, 2, 3):
            m = construir_matriz_distancias(self._puntos(n, 0))
            sol = AlgoritmoGenetico(semilla=0).resolver(m, etiquetas(n))
            self.assertEqual(sorted(sol.ruta), list(range(1, n + 1)))


class AlmacenYPlanificadorTests(unittest.TestCase):
    def setUp(self):
        self.almacen = Almacen()

    def test_mapa_fijo_de_cinco_pasillos(self):
        self.assertEqual(len(self.almacen.productos), 5 * 2 * 8)
        self.assertEqual({p.pasillo for p in self.almacen.productos}, {1, 2, 3, 4, 5})
        self.assertEqual(len({p.codigo for p in self.almacen.productos}), 80)
        self.assertEqual(len(self.almacen.estanterias()), 10)
        # Determinista: dos almacenes tienen exactamente las mismas coordenadas.
        self.assertEqual(Almacen().productos, self.almacen.productos)

    def test_coordenadas_dentro_del_plano(self):
        for p in self.almacen.productos:
            self.assertTrue(0 < p.x < Almacen.ANCHO and 0 < p.y < Almacen.ALTO)

    def test_producto_mas_cercano(self):
        p = self.almacen.obtener("P3-D-05")
        self.assertEqual(self.almacen.producto_mas_cercano(p.x + 0.3, p.y - 0.3, 1.0), p)
        self.assertIsNone(self.almacen.producto_mas_cercano(0, 0, 1.0))

    def test_pedido_alternar(self):
        pedido, p = Pedido(), self.almacen.obtener("P1-I-01")
        self.assertTrue(pedido.alternar(p))
        self.assertTrue(pedido.contiene(p))
        self.assertFalse(pedido.alternar(p))
        self.assertEqual(len(pedido), 0)

    def test_pedido_aleatorio(self):
        pedido = self.almacen.generar_pedido_aleatorio(12, random.Random(1))
        self.assertEqual(len(pedido), 12)
        self.assertEqual(len(set(pedido.productos)), 12)
        with self.assertRaises(ValueError):
            self.almacen.generar_pedido_aleatorio(0)
        with self.assertRaises(ValueError):
            self.almacen.generar_pedido_aleatorio(81)

    def test_planificador_calcula_metricas_coherentes(self):
        planificador = PlanificadorRutas(
            self.almacen,
            [VecinoMasCercano(), AlgoritmoGenetico(semilla=1)],
            [MetricaEuclidiana(), MetricaPorPasillos(self.almacen)],
        )
        pedido = self.almacen.generar_pedido_aleatorio(20, random.Random(2))
        combinaciones = [(a, m) for a in planificador.nombres_algoritmos for m in planificador.nombres_metricas]
        self.assertEqual(len(combinaciones), 4)
        for nombre, metrica in combinaciones:
            r = planificador.planificar(pedido, nombre, metrica)
            self.assertEqual(set(r.productos_optimizados), set(pedido.productos))
            self.assertLessEqual(r.distancia_optimizada, r.distancia_original)
            self.assertAlmostEqual(
                r.eficiencia_pct, 100 * (r.distancia_original - r.distancia_optimizada) / r.distancia_original
            )
            self.assertEqual(r.ruta_puntos[0], Almacen.DEPOSITO)
            self.assertEqual(r.ruta_puntos[-1], Almacen.DEPOSITO)
            if r.sigue_pasillos:
                # Además de INICIO y los 20 productos, el camino incluye las esquinas
                # donde el operario gira entre el pasillo y el transversal.
                self.assertGreater(len(r.ruta_puntos), 22)
            else:
                self.assertEqual(len(r.ruta_puntos), 22)  # INICIO + 20 productos + INICIO
            self.assertTrue(r.pasos)

    def test_planificador_errores(self):
        planificador = PlanificadorRutas(self.almacen, [VecinoMasCercano()], [MetricaEuclidiana()])
        with self.assertRaises(ValueError):
            planificador.planificar(Pedido(), "Vecino más cercano", "Euclidiana (línea recta)")
        pedido = self.almacen.generar_pedido_aleatorio(3)
        with self.assertRaises(ValueError):
            planificador.planificar(pedido, "No existe", "Euclidiana (línea recta)")
        with self.assertRaises(ValueError):
            planificador.planificar(pedido, "Vecino más cercano", "No existe")
        with self.assertRaises(ValueError):
            PlanificadorRutas(self.almacen, [], [MetricaEuclidiana()])
        with self.assertRaises(ValueError):
            PlanificadorRutas(self.almacen, [VecinoMasCercano()], [])


if __name__ == "__main__":
    unittest.main()
