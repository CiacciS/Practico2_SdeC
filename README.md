# Trabajo Práctico N°2

## Calculadora de brecha cambiaria

**Convenciones de llamada entre lenguajes de alto y bajo nivel en x86-64**

---

**Universidad Nacional de Córdoba**
Facultad de Ciencias Exactas, Físicas y Naturales
Cátedra de Sistemas de Computación

**Profesor:** Ing. Javier Jorge

**Integrantes:**

- Nicolás Borsotti Bosco
- Santiago Valentín Ciacci
- Ignacio Ariel Leguizamón

---

## De qué se trata

El trabajo consiste en construir una aplicación de **tres capas** que obtenga la
cotización del dólar blue y del oficial desde [dolarapi.com](https://dolarapi.com) y
calcule la brecha cambiaria entre ambos:

| Capa | Lenguaje | Responsabilidad |
|---|---|---|
| Superior | Python | Consultar la API REST de dolarapi.com y convertir los precios a centavos |
| Intermedia | C | Recibir esos datos, validarlos e invocar las rutinas de bajo nivel |
| Inferior | Ensamblador x86-64 | Calcular la brecha cambiaria y la conversión de pesos a dólares con aritmética entera |

La condición central del práctico es que el pasaje de parámetros y la devolución de
resultados entre la capa de C y la de ensamblador se realice **a través del stack**, es
decir, respetando las convenciones de llamada que utilizan los lenguajes de alto nivel
para comunicarse con los de bajo nivel. Entender ese mecanismo es lo que permite razonar
sobre la frontera entre software y hardware, y es conocimiento directamente aplicable a
sistemas críticos y a seguridad informática.

El desarrollo se organiza en dos iteraciones, tal como pide la consigna: en la primera
se resuelve el problema completo con Python y C, sin ensamblador; en la segunda se
incorporan las rutinas en ensamblador y se verifica su funcionamiento con el depurador
GDB, mostrando el estado del stack antes, durante y después de cada llamada.

## Organización del repositorio

```
practico-2/
├── README.md              este documento
├── CONSIGNA.md            qué pide el TP y en qué orden abordarlo
├── GUIA.md                la teoría: stack frames explicados desde cero
├── PROCEDIMIENTO.md       paso a paso de lo que fuimos haciendo, con capturas
└── capturas/              las imágenes referenciadas por PROCEDIMIENTO.md
```

| Documento | Para qué sirve |
|---|---|
| [`CONSIGNA.md`](CONSIGNA.md) | Los requisitos del trabajo desglosados y el plan de etapas |
| [`GUIA.md`](GUIA.md) | Material de estudio: la teoría de stack frames y los ejemplos del profesor reordenados en secuencia |
| [`PROCEDIMIENTO.md`](PROCEDIMIENTO.md) | El registro del trabajo realizado, parte por parte, con las capturas que verifican cada resultado |

El procedimiento se lleva en **un solo documento**, al que se le van agregando las partes
a medida que avanzamos. Las partes siguen la numeración de `GUIA.md`, y cada captura
lleva el prefijo de su parte (`P2-04-direccion-de-retorno.jpg`, `P4-05-frame-suma-por-pila.jpg`, etc.).

| Parte | Tema | Capturas | Estado |
|---|---|---|---|
| Parte 1 | Preparación del entorno: herramientas y gdb-dashboard | 1 | terminada |
| Parte 2 | Una función en ensamblador puro: prólogo, epílogo, variables locales y dirección de retorno | 10 | terminada |
| Parte 3 | C llamando a ensamblador con argumentos por registros (System V AMD64 ABI) | 5 | terminada |
| Parte 4 | Paso de argumentos por la pila cuando se superan los seis registros, emulación de cdecl con `__asm__` y experimento de clobbers | 13 | terminada |
| Parte 5 | Detalles de la ABI: alineación a 16 bytes, registros callee-saved y red zone | 7 | terminada |
| Iteración 1 | Calculadora de brecha cambiaria en Python + C, sin ensamblador | — | pendiente |
| Iteración 2 | Rutinas en ensamblador con pasaje por stack y depuración con GDB | — | pendiente |

Todas las sesiones de depuración se hicieron con **gdb-dashboard**, como pide la cátedra.

## Conclusiones

*Las conclusiones del trabajo práctico se completan al finalizar las dos iteraciones.*

Del estudio previo de los stack frames (Partes 1 a 5) quedaron establecidas las bases que
el TP necesita:

- Los primeros seis argumentos enteros viajan por registros y el resultado vuelve en `%rax`.
- Cuando hay más argumentos, el compilador empuja los excedentes a la pila de derecha a
  izquierda, y la función los lee en `16(%rbp)`, `24(%rbp)`, etc. La pila la limpia el llamador.
- Declarar la función en C con más de seis parámetros es la forma más segura de pasar
  argumentos por el stack: respeta la ABI y deja al compilador a cargo de la alineación,
  la limpieza y los registros preservados.
- Las reglas de la ABI que no se ven (alineación, callee-saved) rompen el programa cuando
  no se respetan, así que las rutinas en ensamblador del TP tienen que cumplirlas.
