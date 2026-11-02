# Guía de estudio para la sustentación

## 1. Cómo se explica el proyecto en 30 segundos

El operario sale del INICIO, debe recoger todos los productos de un pedido y
volver. Si los recoge en el orden en que llegaron, camina de más. Buscamos el
**orden de visita que minimice la distancia**: es el Problema del Viajante
(TSP). Con 20 productos hay más de 2,4 × 10¹⁸ órdenes posibles, así que no se
prueban todos: se usan **heurísticas** que encuentran rutas muy buenas en
fracciones de segundo.

La distancia se puede medir de dos formas, que el usuario elige en la interfaz:
**línea recta** (euclidiana, lo que pide el enunciado) o **por pasillos** (lo que
el operario realmente camina). Mostrar las dos y comparar su efecto es la parte
más interesante de la exposición.

## 2. Flujo del programa (sigue el diagrama de secuencia)

1. El usuario genera un pedido (o hace clic en productos del plano).
2. Elige algoritmo y tipo de distancia, y pulsa "Optimizar ruta".
3. La Vista avisa al Controlador, que le pide la ruta al `PlanificadorRutas`.
4. El Planificador arma la lista de puntos `[INICIO] + productos` y calcula la
   **matriz de distancias** usando la métrica elegida (`construir_matriz_distancias`).
5. El algoritmo recibe SOLO la matriz y devuelve el orden de visita.
6. El Planificador calcula la distancia del orden original y del optimizado, y
   el camino a dibujar (`metrica.camino_completo`).
7. La Vista dibuja la ruta y muestra las métricas: distancia original, distancia
   optimizada y % de eficiencia.

**Idea clave para defender el diseño:** los algoritmos solo conocen una matriz de
números. No saben nada de pasillos, de la interfaz ni de Tkinter. Por eso se
pueden probar solos y se pueden reemplazar sin tocar el resto. Cambiar de línea
recta a pasillos **no modificó ni una línea** de `VecinoMasCercano` ni de
`AlgoritmoGenetico`.

## 3. Vecino más cercano (`VecinoMasCercano`)

Regla: *"desde donde estoy, voy al producto pendiente más cercano"*.

Ejemplo numérico (el mismo de `tests/test_modelo.py`). INICIO en (0, 0) y tres
productos en línea recta: A en x=10, B en x=3, C en x=6. El pedido llega en el
orden A, B, C.

| Ruta | Cálculo | Total |
|---|---|---|
| Orden original (A, B, C) | 10 + 7 + 3 + 6 | **26 m** |
| Vecino más cercano (B, C, A) | 3 + 3 + 4 + 10 | **20 m** |

Eficiencia = (26 − 20) / 26 × 100 = **23,1 %**.

* Complejidad: O(n²). Es muy rápido.
* Debilidad: es **voraz y miope**; no mira hacia adelante. Puede dejar un
  producto lejano para el final y obligar a un regreso largo.

## 4. Algoritmo genético (`AlgoritmoGenetico`)

| Concepto biológico | En este proyecto |
|---|---|
| Individuo | una ruta (permutación de los productos) |
| Aptitud | qué tan corta es la ruta |
| Población | 100 rutas candidatas |
| Generación | una vuelta del ciclo (300 en total) |

Ciclo: **evaluar → elitismo → selección por torneo → cruce OX → mutación por
inversión → reemplazar**.

* **Cruce OX:** el hijo hereda un tramo del padre 1 y completa los huecos con
  el orden del padre 2. Así nunca hay productos repetidos ni faltantes.
  Ejemplo: padre1 `[1 2 3 4 5 6]`, padre2 `[6 4 2 1 5 3]`, tramo heredado
  `[3 4 5]` → hijo `[6 2 3 4 5 1]`.
* **Mutación por inversión:** se invierte un tramo al azar. Deshace cruces de
  caminos innecesarios.
* **Elitismo:** las 2 mejores rutas pasan intactas; la mejor solución nunca se
  pierde.
* **Siembra:** la población inicial incluye la ruta del vecino más cercano y el
  orden original. Por eso el genético **nunca da un resultado peor que
  ninguno de los dos**. Se puede desactivar con
  `ConfigAG(sembrar_soluciones_iniciales=False)`.
* Es estocástico: con `--semilla` los resultados son reproducibles.

## 5. Línea recta contra pasillos

### Por qué la línea recta engaña

La distancia euclidiana mide "como vuela un pájaro". Pero el operario no puede
atravesar una estantería: solo camina por el **eje de cada pasillo** y por los
dos **pasillos transversales** (frontal y trasero). Dos productos en pasillos
vecinos pueden estar a 5 m en línea recta y a 24 m caminando:

| Par de productos | Línea recta | Por pasillos | Cómo se camina |
|---|---|---|---|
| P1-D-01 → P2-I-01 | 5,0 m | **24,0 m** | bajar 6 m, cruzar 12 m por el frente, subir 6 m |
| P1-D-08 → P5-I-08 | 41,0 m | **62,0 m** | subir 7 m, cruzar 48 m por el fondo, bajar 7 m |
| P1-I-01 → P1-D-08 (mismo pasillo) | 35,7 m | **35,0 m** | recto por el eje, |10 − 45| |

### Cómo se calcula (`pickflow/modelo/distancias.py`)

1. **Ajustar** cada punto a la red de caminata: un producto se proyecta sobre el
   eje de su pasillo; el INICIO queda sobre el transversal frontal.
2. **Mismo pasillo:** distancia = |diferencia de Y|.
3. **Distinto pasillo:** se elige el camino más corto entre el frente y el fondo:

```
por el frente = (Ya - Yfrente) + |Xa - Xb| + (Yb - Yfrente)
por el fondo  = (Yfondo - Ya) + |Xa - Xb| + (Yfondo - Yb)
```

Es el camino más corto sobre una red, así que sigue siendo simétrica y cumple la
desigualdad triangular (verificado en las pruebas), y por eso el TSP funciona
igual.

### Qué se cambió en el código

* `tsp.py`: `construir_matriz_distancias(puntos, funcion_distancia)` ahora recibe
  la función de distancia (por defecto, la euclidiana). **Es el único punto
  donde se decide cómo se mide.**
* `distancias.py` (nuevo): `MetricaEuclidiana` y `MetricaPorPasillos`, con el
  mismo patrón Estrategia que los algoritmos. Cada una da la distancia y el
  camino a dibujar.
* `planificador.py`: usa la métrica elegida y además calcula siempre la
  distancia real por pasillos para poder compararla.
* Vista y controlador: un selector más y la red de pasillos dibujada.

### Cuánto importa: medido

15 pedidos aleatorios por tamaño. Todas las distancias de esta tabla son **lo que
realmente se camina** (por pasillos). Se compara la ruta optimizada en línea
recta contra la optimizada por pasillos.

| Productos | Orden original | Optimizado en línea recta (genético) | Optimizado por pasillos (genético) | Metros extra por usar línea recta |
|---|---|---|---|---|
| 8 | 469,2 m | 289,6 m | 268,7 m | +7,8 % |
| 15 | 839,6 m | 374,0 m | 321,5 m | +16,4 % |
| 25 | 1.310,4 m | 506,3 m | 351,1 m | +44,4 % |
| 40 | 2.061,9 m | 671,2 m | 371,2 m | +80,8 % |

Con el vecino más cercano la penalización llega a +100,4 % en pedidos de 40
productos (promedio) y el peor caso individual fue +131,1 %. La razón: en línea
recta, saltar a un pasillo vecino parece barato (5 m), así que el algoritmo
zigzaguea entre pasillos cuando en realidad cada salto cuesta 24 m o más.

## 6. Resultados de los algoritmos

15 pedidos aleatorios por tamaño. El "orden original" es el orden aleatorio en
que se sortearon los productos. Las columnas de porcentaje son la eficiencia
ganada frente a ese orden.

**Distancia por pasillos (realista)**

| Productos | Original (prom.) | Vecino más cercano | Algoritmo genético | Genético mejor que VMC | Tiempo máx. genético |
|---|---|---|---|---|---|
| 8 | 469,2 m | 39,0 % | 42,7 % | 9 de 15 | 0,29 s |
| 15 | 839,6 m | 60,2 % | 61,7 % | 7 de 15 | 0,32 s |
| 25 | 1.310,4 m | 72,3 % | 73,2 % | 8 de 15 | 0,34 s |
| 40 | 2.061,9 m | 81,4 % | 82,0 % | 14 de 15 | 0,41 s |

En los demás pedidos ambos empatan; el genético nunca fue peor.

**Distancia euclidiana (línea recta)**

| Productos | Original (prom.) | Vecino más cercano | Algoritmo genético | Genético mejor que VMC | Tiempo máx. genético |
|---|---|---|---|---|---|
| 8 | 267,2 m | 35,2 % | 40,2 % | 13 de 15 | 0,36 s |
| 15 | 457,8 m | 49,6 % | 56,8 % | 15 de 15 | 0,42 s |
| 25 | 742,7 m | 62,0 % | 68,2 % | 15 de 15 | 0,45 s |
| 40 | 1.156,4 m | 68,4 % | 73,6 % | 15 de 15 | 0,54 s |

Observación para comentar: con distancia por pasillos, el vecino más cercano
queda mucho más cerca del genético. La estructura de pasillos hace que la
decisión voraz sea más acertada que con línea recta.

**Qué tan cerca del óptimo están.** Con 9 productos se puede calcular el óptimo
exacto probando las 362.880 rutas. En 6 pedidos:

| Distancia | Vecino más cercano | Algoritmo genético |
|---|---|---|
| Euclidiana | 6,7 % sobre el óptimo (máx. 12,4 %) | 0,00 %: óptimo en los 6 |
| Por pasillos | 3,6 % sobre el óptimo (máx. 12,9 %) | 0,00 %: óptimo en los 6 |

Con 25 o 40 productos no se puede verificar el óptimo por fuerza bruta, así que
ahí solo se afirma que el genético mejora o iguala al vecino más cercano, no que
sea óptimo.

## 7. Limitaciones (conviene decirlas antes de que las pregunten)

1. **El operario recolecta desde el eje del pasillo.** No se cuentan los 3,5 m
   entre el eje y el producto. Por eso, en el mismo pasillo y entre lados
   opuestos, la distancia por pasillos puede ser hasta 0,7 m menor que la recta.
2. **Solo hay dos pasillos transversales** (frontal y trasero). Muchas bodegas
   reales tienen transversales intermedios, que acortarían las rutas. Tampoco se
   modelan pasillos de un solo sentido ni congestión.
3. **La mejora depende de la línea base.** Aquí el orden original es aleatorio,
   el peor caso. Si en la bodega los pedidos ya llegaran ordenados por zona, el
   ahorro sería menor. Los porcentajes no se deben presentar como mejora real
   en una bodega sin medirlo con sus datos.
4. **Datos simulados, un solo operario, una sola ruta.** Mapa fijo de 5
   pasillos y 80 productos. No hay peso, tiempos ni varios operarios.
5. **El genético no garantiza el óptimo.** Es una heurística; los parámetros
   (población, generaciones, probabilidades) se fijaron razonablemente pero no
   se hizo un estudio de sensibilidad.
6. **Si el pedido se arma a mano** en un orden ya muy bueno, el vecino más
   cercano podría dar una ruta peor que la original (la eficiencia saldría
   negativa). El genético no, porque se siembra con el orden original.

## 8. Preguntas probables

**¿Por qué no probar todas las rutas?** Crece factorialmente: 10 productos son
3,6 millones de rutas, 20 productos son 2,4 × 10¹⁸.

**¿Cuál es la función objetivo?** `longitud_ruta`: distancia INICIO → productos
en orden → INICIO.

**¿Por qué la matriz de distancias?** Se calcula una vez y los algoritmos solo la
consultan, en vez de repetir cálculos miles de veces.

**¿Por qué hay dos tipos de distancia?** El enunciado pide euclidiana, así que
se conserva. La de pasillos es la que refleja lo que camina el operario. Tener
las dos permite medir cuánto error introduce la simplificación.

**¿Cambia el algoritmo al cambiar la distancia?** No. El algoritmo solo recibe
una matriz de números. Cambia únicamente cómo se llena esa matriz.

**¿Cómo se calcula la distancia por pasillos?** Si los dos productos están en el
mismo pasillo, se camina por el eje. Si no, se sale hasta un pasillo transversal
(el que dé el camino más corto, frente o fondo), se cruza y se entra al otro.

**¿Por qué no usar un grafo y Dijkstra?** La red es lo bastante simple (solo dos
transversales) para resolverla con una fórmula directa. Con una bodega más
compleja (transversales intermedios, pasillos de un solo sentido) se modelaría
como grafo y se calcularía el camino más corto con Dijkstra; el resto del
programa no cambiaría, solo la métrica.

**¿Es válida la distancia por pasillos para el TSP?** Sí: es el camino más
corto sobre una red, por lo que es simétrica y cumple la desigualdad triangular.
Las pruebas lo verifican sobre 15.625 combinaciones de tres puntos.

**¿Por qué un cruce especial (OX) y no cortar por la mitad?** Porque cada
producto debe aparecer una sola vez; un cruce simple produciría repetidos.

**¿Para qué sirve la mutación?** Introduce variedad que el cruce no crea y evita
que toda la población se parezca demasiado.

**¿Qué pasa si se ejecuta dos veces?** El genético puede dar rutas distintas
porque usa azar. Con `--semilla N` el resultado se repite.

**¿Por qué el genético sale mejor que el vecino más cercano?** Porque evalúa
rutas completas y las mejora durante muchas generaciones, mientras que el
vecino más cercano decide paso a paso sin mirar el resto. La diferencia es
menor con distancia por pasillos (ver sección 6).

**¿Es "inteligencia artificial"?** El algoritmo genético es una metaheurística
inspirada en la evolución, una técnica clásica de computación evolutiva. No
aprende de datos como una red neuronal, y conviene decirlo así.

**¿Por qué MVC?** La Vista solo dibuja, el Modelo solo calcula, el Controlador
las conecta. Gracias a eso el modelo se prueba sin interfaz (40 pruebas).

**¿Cómo agregarían otro algoritmo u otra distancia?** Crear una subclase de
`AlgoritmoTSP` o de `MetricaDistancia` y registrarla en `main.py`. Aparece sola
en el menú correspondiente.
