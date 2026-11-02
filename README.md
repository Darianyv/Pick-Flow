# PickFlow Académico

Prototipo académico que reduce la distancia que camina un operario de bodega al
recolectar un pedido, resolviendo el Problema del Viajante (TSP) con dos
algoritmos programados desde cero: **vecino más cercano** y **algoritmo genético**.
La distancia se puede medir en **línea recta** (euclidiana) o **por pasillos**
(lo que el operario realmente camina).
Python 3.10+ · CustomTkinter · patrón MVC · POO.

## Instalación y ejecución (Windows)

Descomprime el zip, abre una terminal dentro de la carpeta `PickFlow_Academico`
(la que contiene `main.py`) y ejecuta:

```bat
python -m pip install -r requirements.txt
python main.py
```

Atención: es `-r` con **un solo guion**. Si pip da error, instala directo con
`python -m pip install customtkinter`.

Para resultados reproducibles en la exposición: `python main.py --semilla 42`

En Linux puede hacer falta `sudo apt install python3-tk`.

## Cómo se usa

1. Al abrir ya hay un pedido aleatorio. Cambia el tamaño con el deslizador y
   pulsa **Generar pedido aleatorio**, o haz clic en los productos del plano
   (puntos grises) para armarlo a mano.
2. Elige el **algoritmo** (vecino más cercano o genético) y el **tipo de
   distancia** (euclidiana o por pasillos), y pulsa **Optimizar ruta**.
3. El plano traza la ruta con un degradado azul → verde → rojo (inicio → fin) y
   numera los productos en el orden de recolección. Con la distancia por
   pasillos se dibuja además la red por la que se puede caminar y la ruta
   nunca atraviesa una estantería.
4. El panel **Métricas** muestra: distancia original recorrida, distancia
   optimizada y % de eficiencia ganado.
5. El panel derecho muestra la **traza paso a paso** del algoritmo.
6. **Mostrar ruta original** dibuja punteada la ruta sin optimizar para comparar.
7. Con distancia euclidiana, el panel de métricas muestra además cuántos metros
   se caminarían **de verdad** por pasillos con esa misma ruta. Compara las dos
   distancias sobre el mismo pedido: es la demostración más clara de por qué la
   línea recta engaña.

Al abrir, la distancia seleccionada es la euclidiana (requisito del enunciado).
Para que arranque con la de pasillos, invierte el orden de la lista `metricas`
en `main.py`.

## Estructura

```
PickFlow_Academico/
├── main.py                          # ensambla Modelo, Vista y Controlador
├── requirements.txt
├── pickflow/
│   ├── modelo/
│   │   ├── almacen.py               # mapa fijo de 5 pasillos, Producto, Pedido
│   │   ├── tsp.py                   # matriz de distancias y algoritmos TSP
│   │   ├── distancias.py            # métricas: euclidiana y por pasillos
│   │   └── planificador.py          # une almacén + algoritmo + métrica
│   ├── vista/
│   │   ├── ventana_principal.py     # ventana CustomTkinter
│   │   └── lienzo_almacen.py        # Canvas: plano, productos y ruta
│   └── controlador/
│       └── controlador.py           # eventos, orquestación, refresco de la vista
├── tests/
│   ├── test_modelo.py               # almacén, algoritmos, planificador
│   └── test_distancias.py           # métricas de distancia e integración
└── docs/
    ├── diagramas.puml               # UML: clases (MVC) y secuencia
    └── guia_sustentacion.md         # explicación, resultados medidos y preguntas
```

## Para estudiar el código

Empieza por `pickflow/modelo/tsp.py`: está comentado de forma didáctica, con
ejemplos numéricos en los comentarios de cada función. Luego lee
`planificador.py` y por último la Vista y el Controlador.

## Pruebas

```bat
python -m unittest discover -s tests -t . -v
```

Son 40 pruebas en total. Las de `test_distancias.py` verifican, entre otras
cosas, que el camino dibujado mide exactamente lo que dice la distancia, que
nunca atraviesa una estantería y que la métrica es simétrica y cumple la
desigualdad triangular.

## Limitaciones

* El operario recolecta desde el eje del pasillo (no se cuenta el ancho del
  pasillo) y solo hay dos pasillos transversales, el frontal y el trasero.
* Datos simulados, un solo operario, mapa fijo de 5 pasillos y 80 productos.
* Más detalle y resultados medidos en `docs/guia_sustentacion.md`.
