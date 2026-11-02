"""Controlador de PickFlow Académico: puente entre la Vista y el Modelo.

Responsabilidades:
  * Recibir los eventos de la Vista (generar pedido, optimizar, clic en producto).
  * Modificar el estado del Modelo (el pedido actual).
  * Pedirle al Modelo que calcule la ruta y entregar a la Vista lo que debe mostrar.

La Vista nunca habla directamente con el Modelo ni al revés: todo pasa por aquí.

Nota didáctica: el cálculo se ejecuta de forma síncrona (la ventana queda
ocupada una fracción de segundo). Con pedidos de hasta 40 productos el algoritmo
genético tarda menos de 1 segundo, por lo que no se justifica la complejidad
adicional de hilos para este prototipo.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, Sequence

from ..modelo.almacen import Almacen, Pedido, Producto
from ..modelo.planificador import PlanificadorRutas, ResultadoOptimizacion

if TYPE_CHECKING:
    from ..vista.ventana_principal import VentanaPrincipal

_ENCABEZADO_LISTA = f"{'#':>3}  {'Código':<9} {'Producto':<13} {'X':>5} {'Y':>5}"


class ControladorPickFlow:
    """Coordina la interacción entre ``VentanaPrincipal`` y el modelo."""

    def __init__(
        self,
        almacen: Almacen,
        planificador: PlanificadorRutas,
        vista: "VentanaPrincipal",
        rng: random.Random | None = None,
    ) -> None:
        self._almacen = almacen
        self._planificador = planificador
        self._vista = vista
        self._rng = rng or random.Random()

        self._pedido = Pedido()
        self._resultado: ResultadoOptimizacion | None = None

    # ------------------------------------------------------------------ #
    # Arranque
    # ------------------------------------------------------------------ #
    def iniciar(self) -> None:
        """Conecta la vista, dibuja el almacén y carga un primer pedido de prueba."""
        self._vista.conectar_controlador(self)
        self._vista.definir_algoritmos(self._planificador.nombres_algoritmos)
        self._vista.definir_metricas(self._planificador.nombres_metricas)
        self._vista.mostrar_almacen(self._almacen)
        self.al_generar_pedido(self._vista.cantidad_solicitada())

    # ------------------------------------------------------------------ #
    # Eventos de la Vista
    # ------------------------------------------------------------------ #
    def al_generar_pedido(self, cantidad: int) -> None:
        """Reemplaza el pedido actual por uno aleatorio de ``cantidad`` productos."""
        cantidad = max(1, min(cantidad, len(self._almacen.productos)))
        self._pedido = self._almacen.generar_pedido_aleatorio(cantidad, self._rng)
        self._resultado = None
        self._refrescar()
        self._vista.mostrar_estado(
            f"Pedido {self._pedido.numero} con {cantidad} productos. "
            "Pulsa «Optimizar ruta» para calcular el recorrido."
        )

    def al_limpiar_pedido(self) -> None:
        """Vacía el pedido actual."""
        self._pedido = Pedido(numero="PED-MANUAL")
        self._resultado = None
        self._refrescar()
        self._vista.mostrar_estado("Pedido vacío. Haz clic en los productos del plano para agregarlos.")

    def al_hacer_clic_en_producto(self, producto: Producto) -> None:
        """Agrega o quita del pedido el producto sobre el que se hizo clic."""
        agregado = self._pedido.alternar(producto)
        self._resultado = None  # el pedido cambió: la ruta calculada ya no es válida
        self._refrescar()
        accion = "agregado al" if agregado else "quitado del"
        self._vista.mostrar_estado(f"{producto.nombre} ({producto.codigo}) {accion} pedido.")

    def al_optimizar(self, nombre_algoritmo: str, nombre_metrica: str) -> None:
        """Calcula la ruta óptima con el algoritmo y la distancia elegidos."""
        if len(self._pedido) == 0:
            self._vista.mostrar_estado("Agrega al menos un producto al pedido antes de optimizar.")
            return

        self._vista.indicar_ocupado(True)
        try:
            self._resultado = self._planificador.planificar(
                self._pedido, nombre_algoritmo, nombre_metrica
            )
        except ValueError as error:
            self._vista.mostrar_estado(f"No se pudo optimizar: {error}")
            return
        finally:
            self._vista.indicar_ocupado(False)

        self._refrescar()
        r = self._resultado
        self._vista.mostrar_estado(
            f"{r.algoritmo} ({r.metrica}): {r.distancia_original:.1f} m -> {r.distancia_optimizada:.1f} m "
            f"({r.eficiencia_pct:.1f} % de eficiencia ganado)."
        )

    # ------------------------------------------------------------------ #
    # Utilidades internas
    # ------------------------------------------------------------------ #
    def _refrescar(self) -> None:
        """Sincroniza plano, lista, traza y métricas con el estado actual."""
        r = self._resultado
        if r is None:
            productos = self._pedido.productos
            self._vista.mostrar_pedido(productos)
            self._vista.mostrar_lista(
                f"Pedido {self._pedido.numero} (orden original)",
                _ENCABEZADO_LISTA,
                self._filas(productos),
            )
            self._vista.mostrar_traza([])
            self._vista.mostrar_metricas(None)
            return

        self._vista.mostrar_pedido(
            r.productos_optimizados, r.ruta_puntos, r.ruta_original_puntos, r.sigue_pasillos
        )
        self._vista.mostrar_lista(
            f"Orden de recolección · {self._pedido.numero}",
            _ENCABEZADO_LISTA,
            self._filas(r.productos_optimizados),
        )
        self._vista.mostrar_traza(r.pasos)
        detalle = (
            f"Ahorro: {r.ahorro_metros:,.1f} m  ·  {len(r.productos_optimizados)} productos\n"
            f"{r.algoritmo}  ·  {r.tiempo * 1000:,.0f} ms\n"
            f"Distancia medida: {r.metrica}"
        )
        if not r.sigue_pasillos:
            # La línea recta no es lo que realmente se camina: se muestra la diferencia.
            detalle += (
                f"\nCaminando por pasillos: {r.distancia_real_original:,.1f} m -> "
                f"{r.distancia_real_optimizada:,.1f} m ({r.eficiencia_real_pct:.1f} %)"
            )
        self._vista.mostrar_metricas(
            {
                "original": f"{r.distancia_original:,.1f} m",
                "optimizada": f"{r.distancia_optimizada:,.1f} m",
                "eficiencia": f"{r.eficiencia_pct:.1f} %",
                "detalle": detalle,
            }
        )

    @staticmethod
    def _filas(productos: Sequence[Producto]) -> list[str]:
        """Filas de texto numeradas para la lista de recolección."""
        return [
            f"{numero:>3}  {p.codigo:<9} {p.nombre:<13} {p.x:>5.1f} {p.y:>5.1f}"
            for numero, p in enumerate(productos, start=1)
        ]
