"""PickFlow Académico: optimización de rutas de picking con TSP.

Uso:
    python main.py
    python main.py --semilla 42     (resultados reproducibles para la exposición)
"""
from __future__ import annotations

import argparse
import random

import customtkinter as ctk

from pickflow.controlador.controlador import ControladorPickFlow
from pickflow.modelo.almacen import Almacen
from pickflow.modelo.distancias import MetricaEuclidiana, MetricaPorPasillos
from pickflow.modelo.planificador import PlanificadorRutas
from pickflow.modelo.tsp import AlgoritmoGenetico, VecinoMasCercano
from pickflow.vista.ventana_principal import VentanaPrincipal


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PickFlow Académico: rutas de picking con TSP.")
    parser.add_argument(
        "--semilla", type=int, default=None,
        help="semilla del azar: mismos pedidos y mismos resultados en cada ejecución",
    )
    return parser.parse_args()


def main() -> None:
    argumentos = leer_argumentos()
    rng = random.Random(argumentos.semilla)

    # --- Modelo ---
    almacen = Almacen()
    planificador = PlanificadorRutas(
        almacen,
        algoritmos=[VecinoMasCercano(), AlgoritmoGenetico(semilla=argumentos.semilla)],
        # La primera métrica es la que aparece seleccionada al abrir. Se deja la
        # euclidiana (requisito del enunciado); para que el programa arranque con
        # la distancia realista basta con invertir el orden de esta lista.
        metricas=[MetricaEuclidiana(), MetricaPorPasillos(almacen)],
    )

    # --- Vista y Controlador ---
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    vista = VentanaPrincipal()
    controlador = ControladorPickFlow(almacen, planificador, vista, rng)
    controlador.iniciar()
    vista.mainloop()


if __name__ == "__main__":
    main()
