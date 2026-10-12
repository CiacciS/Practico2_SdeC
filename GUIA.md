# Guía paso a paso — TP #2

Esta guía reordena el material del profesor (que viene todo junto y sin secuencia) y lo
explica desde cero. Está pensada para leerse en orden.

---

## Parte 0 — Qué estamos haciendo, en criollo

### El problema de fondo

Cuando escribís `suma(10, 25)` en C, el procesador no tiene ni idea de qué es una
"función". Lo único que sabe hacer es mover números entre registros y memoria, y saltar a
direcciones. Entonces: **¿cómo hace el C para pasarle dos números a otra porción de código,
y recibir una respuesta de vuelta?**

La respuesta es un **acuerdo**: una convención de llamadas. Es un contrato que dice "el
primer argumento te lo dejo en el registro `%rdi`, el segundo en `%rsi`, y vos me devolvés
el resultado en `%rax`". Si las dos partes respetan el contrato, se entienden. En Linux
x86-64 ese contrato se llama **System V AMD64 ABI**.

### Por qué existe el stack

Los registros son pocos (16) y los comparte todo el programa. Si `main` llama a `suma`, y
`suma` usa `%rax` para su cuenta, `main` pierde lo que tenía ahí. Además: ¿dónde guarda
`suma` sus variables locales? ¿Y cómo sabe a qué dirección volver cuando termina?

Para eso está **la pila (stack)**: una zona de memoria donde cada función se arma su
propio "escritorio" temporal — su **stack frame** — mete ahí lo que necesita, y al terminar
lo desarma y deja todo como estaba.

Dato clave: **la pila crece hacia direcciones más bajas.** Cada `push` le resta a `%rsp`,
cada `pop` le suma. Es al revés de lo intuitivo.

### Los dos registros que importan

| Registro | Qué es | Analogía |
|---|---|---|
| `%rsp` | *Stack pointer*. Siempre apunta al tope actual de la pila. | El borde de la pila de platos: se mueve todo el tiempo |
| `%rbp` | *Base pointer*. Apunta a un punto **fijo** dentro de tu frame. | La marca en la pared desde donde medís: no se mueve mientras estés en la función |

¿Por qué hacen falta los dos? Porque `%rsp` se mueve constantemente (cada `push`, cada
`call`). Si quisieras ubicar tus variables relativas a `%rsp`, el offset cambiaría a cada
instrucción. Con `%rbp` clavado al inicio de la función, `-8(%rbp)` significa lo mismo
siempre.

### Anatomía de un stack frame

```
          dirección ALTA
        ┌───────────────────────────┐
24(%rbp)│  8vo argumento (b)        │  ← lo empujó el que llama (caller)
16(%rbp)│  7mo argumento (a)        │  ← lo empujó el caller
 8(%rbp)│  dirección de retorno     │  ← la puso automáticamente 'call'
 0(%rbp)│  %rbp anterior            │  ← lo guardó tu 'pushq %rbp'
-8(%rbp)│  variable local 1         │  ← reservada con 'subq $16, %rsp'
-16(%rbp)│ variable local 2         │
        └───────────────────────────┘  ← %rsp apunta acá
          dirección BAJA
```

Leelo así: **positivos = cosas que me dio el que me llamó. Negativos = cosas mías.**
Y en el medio, en `8(%rbp)`, la dirección a la que tengo que volver.

### El prólogo y el epílogo

Toda función que use frame propio arranca y termina igual:

```asm
mi_funcion:
    pushq %rbp          # PRÓLOGO: guardo el %rbp del que me llamó
    movq  %rsp, %rbp    #          mi frame arranca acá
    subq  $16, %rsp     #          reservo 16 bytes para mis locales (si necesito)

    ...cuerpo...

    movq  %rbp, %rsp    # EPÍLOGO: tiro abajo mis locales
    popq  %rbp          #          devuelvo el %rbp original
    ret                 #          saco la dirección de retorno y salto ahí
```

`leave` es un atajo que hace exactamente `movq %rbp,%rsp ; popq %rbp`.

### Vocabulario que vas a necesitar (de la teoría del profe)

En x86, por razones históricas del 8086, los tamaños tienen nombres fijos:

| Nombre | Tamaño | Sufijo AT&T | Letra en GDB |
|---|---|---|---|
| Byte | 8 bits (1 byte) | `b` | `b` |
| Word | 16 bits (2 bytes) | `w` | `h` (*half word*) |
| Double word | 32 bits (4 bytes) | `l` | `w` |
| **Quadword** | **64 bits (8 bytes)** | `q` | `g` (*giant word*) |

> 📌 **Erratum del README del profe:** ahí dice *"Half Word (Media Palabra): 8 bits (1
> byte)"*. Eso es incorrecto y además se contradice con su propia sección de GDB más
> abajo, donde dice —correctamente— que `h` es *half-word de 2 bytes*. Media palabra de una
> word de 16 bits es **1 byte**, pero el nombre "half word" en la nomenclatura de GDB se
> usa para **2 bytes**. Quedate con la tabla de arriba.

Lo importante para nosotros: en x86-64 **cada ranura de la pila ocupa un quadword (8
bytes)**. Por eso los offsets van siempre de a 8: `-8`, `-16`, `16`, `24`. Y por eso
`subq $16, %rsp` reserva exactamente dos variables locales.

### El comando `x/1gx $rsp` desarmado

Lo vas a usar todo el tiempo en GDB:

- `x` → *examine*, "mostrame memoria"
- `/` → empiezan los parámetros de formato
- `1` → cuántos elementos mostrar
- `g` → *giant word*, de a 8 bytes (quadword)
- `x` → formato hexadecimal
- `$rsp` → desde qué dirección leer

O sea: *"mostrame 1 quadword en hexa, empezando en la cima de la pila"*. Si lo ejecutás
justo al entrar a una función (antes del prólogo), lo que ves es **la dirección de retorno**
que dejó el `call`.

---

## Parte 1 — Preparar el entorno

### 1.1 Instalar las herramientas

```bash
sudo apt update
sudo apt install build-essential gdb python3 python3-pip git
```

- `build-essential` trae `gcc` (compilador C), `as` (ensamblador) y `ld` (enlazador).
- `gdb` es el depurador.

Verificá:

```bash
gcc --version && as --version && ld --version && gdb --version
```

### 1.2 Traer el material del profe

Ya lo tenés clonado en `~/Escritorio/SdeComp/Gitlab/stackframe`. Si necesitaras clonarlo
de nuevo:

```bash
git clone https://gitlab.com/nicoborsottib/stackframe.git
cd stackframe
```

> **Sobre GitLab:** no necesitás cuenta ni entender nada de GitLab. Es igual que GitHub:
> un repo público que clonás con `git clone` y listo. La entrega del TP va en GitHub aparte.

### 1.3 Instalar gdb-dashboard

Esto es **opcional pero muy recomendado**: hace que GDB muestre registros, pila y
desensamblado todos juntos en pantalla en vez de tener que pedirlos de a uno.

```bash
cd ~/Escritorio/SdeComp/Gitlab/stackframe
./setup.sh
```

El `setup.sh` inicializa el submódulo y copia el `.gdbinit` a esa carpeta (o sea, funciona
solo cuando arrancás GDB **desde ahí**).

Si lo querés para todo el sistema:

```bash
wget -P ~ https://github.com/cyrus-and/gdb-dashboard/raw/master/.gdbinit
pip install pygments   # opcional, agrega colores
```

> El README del profe menciona este `wget` en el medio de la teoría, como al pasar. En
> realidad es parte de la preparación del entorno y va acá, **antes** de empezar a debuggear.

---

## Parte 2 — Ejemplo standalone: `asm hello world`

Este es el ejemplo más puro: **assembler solo, sin C**. Un programa que suma 10 + 20 y
devuelve 30 como código de salida.

### 2.1 Qué hace el código

`program.s` tiene dos partes:

- **`_start`** — el punto de entrada real del programa (el equivalente a `main`, pero sin
  la librería estándar de C de por medio). Carga 10 en `%rdi` y 20 en `%rsi`, llama a
  `calc_sum`, y termina el proceso con la syscall `exit` usando el resultado como código de
  salida.
- **`calc_sum`** — arma su stack frame, copia los dos argumentos de los registros a
  variables locales en la pila, las suma, y devuelve en `%rax`.

Fijate que `calc_sum` **no necesitaría** guardar los argumentos en la pila (podría sumar
`%rdi + %rsi` directo). Lo hace a propósito, para que vos puedas *ver* las variables
locales en memoria con GDB. Es un ejercicio didáctico.

### 2.2 Compilar y ejecutar — en este orden

```bash
cd ~/Escritorio/SdeComp/Gitlab/stackframe/"asm hello world"

# 1. Ensamblar, generando símbolos de depuración (-g --gdwarf-2 es lo que
#    después le permite a GDB mostrarte el código fuente mientras avanzás)
as -g --gdwarf-2 -o program.o program.s

# 2. Enlazar. Usamos 'ld' directo (no gcc) porque este programa no usa
#    la librería estándar de C: entra por _start, no por main.
ld -o program program.o

# 3. Ejecutar y ver el código de retorno
./program
echo $?          # tiene que imprimir 30
```

> Las comillas en `"asm hello world"` son necesarias: el nombre de la carpeta tiene
> espacios.

Si `echo $?` imprime 30, ya funcionó. El programa no imprime nada por pantalla — su única
salida es el *exit code*.

### 2.3 Sesión de GDB, ordenada

Acá es donde realmente se aprende: vas a ver la pila armarse y desarmarse en vivo.

**Arrancar:**

```bash
gdb ./program
```

**Dentro de GDB, en este orden:**

```gdb
# --- Preparar ---
break *calc_sum        # breakpoint en la PRIMERA instrucción de calc_sum
break _start           # breakpoint en el punto de entrada
run                    # arranca; se detiene en _start
```

> 💡 Usamos `break *calc_sum` (con asterisco) en vez de `break calc_sum`. Sin el asterisco,
> GDB a veces salta el prólogo automáticamente, y justo el prólogo es lo que queremos ver.

```gdb
# --- Estado inicial ---
info registers rsp rbp rip     # anotá estos valores, los vas a comparar después

# --- Cargar los argumentos ---
stepi                  # ejecuta: movq $10, %rdi
stepi                  # ejecuta: movq $20, %rsi
info registers rdi rsi # verificá: 0xa y 0x14

# --- Entrar a la función ---
stepi                  # ejecuta: call calc_sum
```

Ahora estás **dentro de `calc_sum`, antes del prólogo**. Este es el momento clave:

```gdb
x/1gx $rsp             # la cima de la pila = dirección de retorno
disassemble _start     # compará: tiene que ser la dirección de la instrucción
                       # siguiente al 'call'
```

Eso te demuestra físicamente que `call` empujó la dirección de retorno a la pila.

```gdb
# --- Ver armarse el frame ---
stepi                  # pushq %rbp       (guarda el base pointer del caller)
stepi                  # movq %rsp, %rbp  (establece el nuevo base pointer)
stepi                  # subq $16, %rsp   (reserva las dos variables locales)

x/4gx $rsp             # mirá los 4 quadwords desde la cima
```

El mapa de lo que estás viendo:

| Dirección | Equivale a | Qué contiene |
|---|---|---|
| `$rsp + 0` | `-16(%rbp)` | espacio de la variable `b` (todavía basura) |
| `$rsp + 8` | `-8(%rbp)` | espacio de la variable `a` (todavía basura) |
| `$rsp + 16` | `0(%rbp)` | el `%rbp` viejo que se salvó |
| `$rsp + 24` | `8(%rbp)` | la dirección de retorno |

```gdb
# --- Ver escribirse las variables locales ---
stepi                  # movq %rdi, -8(%rbp)    → copia 10 (0xa)
stepi                  # movq %rsi, -16(%rbp)   → copia 20 (0x14)

x/4gx $rsp             # ahora SÍ ves 0xa y 0x14 en los dos primeros slots
```

```gdb
# --- El cuerpo ---
stepi                  # movq -8(%rbp), %rax    → %rax = 10
stepi                  # addq -16(%rbp), %rax   → %rax = 30 (0x1e)
info registers rax     # confirmá: 0x1e

# --- Ver desarmarse el frame ---
stepi                  # movq %rbp, %rsp   (libera las locales)
stepi                  # popq %rbp         (restaura el base pointer del caller)
info registers rsp rbp # %rsp volvió a apuntar a la dirección de retorno,
                       # %rbp es el mismo valor que tenías al principio

stepi                  # ret  (saca la dirección de retorno y salta a _start)

quit
```

Cuando termines esta sesión y hayas *visto* cada paso, entendiste stack frames. Todo lo
demás del TP es aplicar esto.

---

## Parte 3 — Ejemplo 1: C llamando a ASM (argumentos por registros)

Archivos: `main.c` + `suma.s`

Esta es la forma **normal y correcta** según la ABI: los primeros 6 argumentos enteros
viajan por registros, en este orden estricto:

```
%rdi , %rsi , %rdx , %rcx , %r8 , %r9
```

y el retorno vuelve en `%rax`.

`suma.s` es mínimo — ni siquiera arma frame, porque no lo necesita:

```asm
suma:
    movq %rdi, %rax   # rax = a
    addq %rsi, %rax   # rax = a + b
    ret
```

En `main.c` alcanza con declarar `extern long suma(long a, long b);` y llamarla como
cualquier función de C. El compilador se encarga de poner `a` en `%rdi` y `b` en `%rsi`.

### Compilar

```bash
cd ~/Escritorio/SdeComp/Gitlab/stackframe

as --64 -o suma.o suma.s        # ensamblar el .s
gcc -c main.c -o main.o         # compilar el .c (sin enlazar)
gcc main.o suma.o -o programa   # enlazar los dos objetos
./programa
```

Salida esperada: `suma(10, 25) = 35`

> Acá enlazamos con `gcc` y no con `ld`, porque `main.c` usa `printf` y entra por `main`:
> necesitamos que se enganche la librería estándar de C.

---

## Parte 4 — Ejemplo 2: argumentos **por la pila** ← este es el que importa para el TP

Archivos: `main2.c` + `suma2.s` + `suma_por_pila.s`

Acá hay **dos técnicas distintas** mezcladas en el mismo `main2.c`. Conviene separarlas
mentalmente.

### 4.1 Técnica A — empujar los argumentos a mano (`suma_stack`)

Emula la vieja convención **cdecl** (la clásica de C en 32 bits). En `main2.c` se hace con
assembler en línea:

```c
__asm__ (
    "pushq %[b]\n\t"        // 1. empujo el 2do argumento
    "pushq %[a]\n\t"        // 2. empujo el 1er argumento
    "call suma_stack\n\t"   // 3. llamo
    "addq $16, %%rsp\n\t"   // 4. limpio la pila (2 args x 8 bytes)
    : "=a" (resultado)
    : [a] "r" (a), [b] "r" (b)
    : "memory"
);
```

Del lado del assembler, `suma2.s`:

```asm
suma_stack:
    pushq   %rbp
    movq    %rsp, %rbp
    movq    16(%rbp), %rax   # a
    addq    24(%rbp), %rax   # b
    popq    %rbp
    ret
```

**¿Por qué 16 y 24?** Seguí la cuenta desde `%rbp`:

```
0(%rbp)  → el %rbp viejo      (lo puso 'pushq %rbp')
8(%rbp)  → dirección retorno  (lo puso 'call')
16(%rbp) → 'a'                (fue el ÚLTIMO push, entonces quedó más abajo)
24(%rbp) → 'b'                (fue el PRIMER push, quedó más arriba)
```

Por eso se empuja **en orden inverso**: primero `b`, después `a`. El último que entra es el
primero que aparece.

Y el `addq $16, %rsp` después del `call` es obligatorio: en cdecl **el que llama es el
responsable de limpiar** los argumentos que empujó. Si te lo olvidás, la pila queda
desbalanceada y el programa revienta más adelante.

> ⚠️ Esta técnica con `__asm__` inline es frágil: le estás moviendo la pila por debajo al
> compilador, que no se entera. Sirve para aprender y para el TP está perfecta, pero en
> código real no se hace así.

### 4.2 Técnica B — dejar que la ABI use la pila sola (`suma_por_pila`)

Esta es más elegante y **es la que recomiendo para el TP**. La idea: la ABI dice que
los primeros 6 argumentos van por registros. ¿Y el séptimo? **A la pila.** Entonces si
declarás una función con 8 argumentos, el compilador empuja los dos últimos a la pila
*por vos*, respetando la ABI al pie de la letra.

```c
extern long suma_por_pila(long r1, long r2, long r3, long r4, long r5, long r6,
                          long a, long b);
long res = suma_por_pila(0, 0, 0, 0, 0, 0, 10, 25);
```

Los seis ceros van a `%rdi, %rsi, %rdx, %rcx, %r8, %r9` y se ignoran. Los que nos importan,
`a` y `b`, terminan en la pila — y el assembler los lee exactamente igual que antes:

```asm
suma_por_pila:
    pushq   %rbp
    movq    %rsp, %rbp
    movq    16(%rbp), %rax   # 7mo argumento = a
    addq    24(%rbp), %rax   # 8vo argumento = b
    popq    %rbp
    ret
```

Ventaja: no hay assembler inline, no hay que limpiar la pila a mano, y es ABI-correcto.
Cumple el requisito R5 de la consigna sin trucos.

### 4.3 Compilar

```bash
cd ~/Escritorio/SdeComp/Gitlab/stackframe

as --64 -o suma2.o suma2.s
as --64 -o suma_por_pila.o suma_por_pila.s
gcc -c main2.c -o main2.o
gcc main2.o suma2.o suma_por_pila.o -o programa2
./programa2
```

Salida esperada:

```
suma(10, 25) = 35
suma_por_pila(10, 25) = 35
```

### 4.4 Verlo en GDB

```bash
gdb ./programa2
```

```gdb
break *suma_por_pila
run
x/4gx $rsp          # antes del prólogo: [rsp]=ret addr, [rsp+8]=a, [rsp+16]=b
stepi               # pushq %rbp
stepi               # movq %rsp, %rbp
x/4gx $rbp          # ahora: [rbp]=rbp viejo, [rbp+8]=ret, [rbp+16]=a, [rbp+24]=b
p $rbp              # imprimir el valor de rbp
x/1gx $rbp+16       # tiene que dar 0xa  (10)
x/1gx $rbp+24       # tiene que dar 0x19 (25)
continue
quit
```

Esas dos últimas líneas son **la evidencia** de que los parámetros viajaron por la pila.
Sacale una captura: sirve para defender el TP.

---

## Parte 5 — Detalles de la ABI que te pueden morder

Tres cosas que no se ven en los ejemplos pero son parte del contrato:

**1. Alineación de 16 bytes.** Justo *antes* de ejecutar un `call`, `%rsp` tiene que ser
múltiplo de 16. Como `call` empuja 8 bytes, al entrar a la función queda en `múltiplo+8`.
Por eso el `pushq %rbp` del prólogo la vuelve a alinear. Si tu rutina en assembler llama a
`printf` y se te cae con *segmentation fault* sin razón aparente, **casi seguro es esto**:
metele un `subq $8, %rsp` antes del `call` y un `addq $8, %rsp` después.

**2. Callee-saved vs caller-saved.**

| Tipo | Registros | Regla |
|---|---|---|
| **Callee-saved** | `%rbx`, `%rbp`, `%r12`–`%r15` | Si tu función los usa, **tenés que guardarlos y restaurarlos** |
| **Caller-saved** | `%rax`, `%rcx`, `%rdx`, `%rsi`, `%rdi`, `%r8`–`%r11` | Los podés pisar libremente |

Si tu rutina ASM usa `%rbx` y no lo restaurás, el C que te llamó se va a romper de una
forma rarísima y difícil de encontrar.

**3. Red zone.** Los 128 bytes *debajo* de `%rsp` son zona segura que una función *leaf*
(que no llama a nadie) puede usar sin mover `%rsp`. No lo vas a necesitar, pero si ves
offsets negativos sin `sub`, es esto.

---

## Parte 6 — El TP en sí: arquitectura propuesta

### 6.1 Las tres capas

```
┌─────────────────────────────────────────────┐
│  PYTHON            python/cliente.py        │
│  · consulta la API REST con urllib          │
│  · parsea el JSON                           │
│  · invoca al binario de C con los datos     │
│  · muestra el resultado final               │
└──────────────────┬──────────────────────────┘
                   │  argumentos por línea de comandos
                   ▼
┌─────────────────────────────────────────────┐
│  C                 c/main.c                 │
│  · recibe los datos crudos (argv)           │
│  · llama a las rutinas de assembler         │
│  · imprime el resultado por stdout          │
└──────────────────┬──────────────────────────┘
                   │  convención de llamadas — POR LA PILA
                   ▼
┌─────────────────────────────────────────────┐
│  ASSEMBLER         asm/conversiones.s       │
│  · arma su stack frame                      │
│  · lee los parámetros de 16(%rbp), 24(%rbp) │
│  · HACE EL CÁLCULO                          │
│  · devuelve en %rax                         │
└─────────────────────────────────────────────┘
```

El resultado vuelve para arriba: `%rax` → C lo imprime → Python lo captura y lo muestra.

### 6.2 Qué API elegimos y por qué

**Decisión del grupo: [dolarapi.com](https://dolarapi.com).** Gratis, sin API key y sin
registro.

Los criterios que pesaron, en orden:

1. **Sin clave ni registro.** Si el profesor no puede correr el trabajo en su máquina sin
   darse de alta en ningún lado, el trabajo no sirve.
2. **Que devuelva decimales.** Es el criterio decisivo: el corazón del TP es la conversión
   de punto flotante a entero. Una API que devuelva enteros deja esa operación vacía.
3. **Que el cálculo use multiplicación *y* división.** Ahí aparecen `imulq`, `cqto` e
   `idivq`, que son instrucciones no triviales y dan material real para mostrar en la
   defensa. Una suma sola no alcanza.
4. **JSON plano.** Cuanto menos tiempo se pierde parseando en Python, más queda para lo
   que la materia evalúa.

Y una razón de fondo que no es solo conveniencia: **el dinero es el ejemplo canónico de
por qué no se usa punto flotante**. Trabajar en centavos no es un rodeo para esquivar los
registros `%xmm`, es lo que hace cualquier sistema financiero real, porque `0.1` no tiene
representación exacta en binario y los errores se acumulan. La decisión de diseño se
sostiene por sí misma.

Se descartó Open-Meteo (temperaturas, Celsius → Fahrenheit), que era la recomendación
anterior de esta guía. Es igual de válida técnicamente, pero la justificación del punto
fijo es más débil y el tema es menos propio.

#### Los endpoints

```
GET https://dolarapi.com/v1/dolares/blue
GET https://dolarapi.com/v1/dolares/oficial
```

Respuesta real de la API, obtenida con `curl` el 12/10/2026 (Paso 0):

```json
{
  "moneda": "USD",
  "casa": "blue",
  "nombre": "Blue",
  "compra": 1520,
  "venta": 1540,
  "fechaActualizacion": "2026-10-12T12:55:00.000Z"
}
```

```json
{
  "moneda": "USD",
  "casa": "oficial",
  "nombre": "Oficial",
  "compra": 1485,
  "venta": 1535,
  "fechaActualizacion": "2026-10-09T18:55:00.000Z"
}
```

Los campos que usamos son **`venta`** y **`fechaActualizacion`**.

Dos observaciones sobre estos datos:

- **Los precios pueden venir enteros o con decimales.** Ese día llegaron como `1540`,
  pero otros días llegan como `1535.57`. El parseo tiene que aceptar las dos formas.
- **Las fechas de actualización pueden no coincidir.** El 12/10 es feriado y el oficial
  no se actualiza, así que ese día el blue era del 12 y el oficial del 9. El programa
  muestra las dos fechas junto al resultado, para que quede claro qué se está comparando.

#### El cálculo

Usamos el precio de **venta** de las dos cotizaciones: es lo que paga quien compra
dólares y es la cifra que se publica habitualmente. Con el de compra la brecha da otro
número, así que la elección queda fijada acá.

La **brecha cambiaria** entre el dólar blue y el oficial:

```
brecha % = (blue − oficial) × 100 / oficial
```

Resta, multiplicación y división en una sola rutina, con los dos operandos entrando por
la pila. Como segunda rutina, la conversión de un monto en pesos a dólares:

```
dólares = pesos × 100 / cotización
```

#### La aritmética de punto fijo

La API puede devolver `1535.57`. Hacer punto flotante en ensamblador obliga a meterse con
SSE y los registros `%xmm`, que es otro tema entero. La solución es **trabajar en
centavos**: Python multiplica por 100 y manda enteros, el ensamblador opera con enteros, y
Python divide por 100 al mostrar.

Con los valores reales de venta del 12/10/2026, pasados por la rutina:

```
blue    = 1540,00  →  154000 centavos
oficial = 1535,00  →  153500 centavos

ASM:  (154000 − 153500) × 10000 / 153500  =  32

32 centésimas de punto porcentual  →  Python muestra 0,32 %
```

El valor exacto es 0,3257 %; el ensamblador trunca a 0,32 % porque `idivq` descarta el
resto.

#### La conversión a centavos: `round()`, no `int()`

Pasar el precio a centavos parece trivial y tiene una trampa:

```python
centavos = int(dato["venta"] * 100)            # MAL
centavos = round(float(dato["venta"]) * 100)   # BIEN
```

El punto flotante no representa exactamente la mayoría de los decimales, y `int()`
trunca hacia abajo:

```
1024.09 * 100  =  102408.99999999999   →   int() = 102408   (debería ser 102409)
```

Probando todos los precios posibles entre $1000,00 y $1999,99, **`int()` da un centavo de
menos en 4588 de cada 100.000**. `round()` los corrige a todos. El `float()` previo es para
aceptar tanto `1540` como `1535.57`, que son las dos formas en que llega el dato.

Este error es, en sí mismo, la mejor justificación de la decisión de diseño: el punto
flotante falla incluso en algo tan simple como pasar pesos a centavos.

El factor es `10000` y no `100` porque se quieren dos decimales en el resultado: `100`
para el porcentaje y `100` más para las centésimas.

### 6.3 Las rutinas en ensamblador

Este código está **probado y verificado**: compila, corre y da los resultados correctos,
incluidos los casos de brecha negativa y brecha cero.

```asm
# conversiones.s — rutinas de cálculo del TP, en sintaxis AT&T
#
# Los dos argumentos útiles entran POR LA PILA: la función se declara en C con
# ocho parámetros, los seis primeros se pasan en cero y se ignoran, y la ABI
# System V AMD64 obliga al compilador a empujar el 7mo y el 8vo a la pila.
#
# Mapa del stack frame visto desde %rbp:
#   24(%rbp) -> 8vo parámetro
#   16(%rbp) -> 7mo parámetro
#    8(%rbp) -> dirección de retorno (la puso 'call')
#    0(%rbp) -> %rbp del llamador (lo puso 'pushq %rbp')

    .section .text

# brecha_cambiaria(0,0,0,0,0,0, blue_cent, oficial_cent) -> centésimas de %
    .globl  brecha_cambiaria
    .type   brecha_cambiaria, @function
brecha_cambiaria:
    pushq   %rbp
    movq    %rsp, %rbp

    movq    16(%rbp), %rax      # %rax = blue
    subq    24(%rbp), %rax      # %rax = blue - oficial
    imulq   $10000, %rax        # %rax = (blue - oficial) * 10000
    cqto                        # extiende el signo de %rax hacia %rdx:%rax
    idivq   24(%rbp)            # %rax = cociente, %rdx = resto

    popq    %rbp
    ret
    .size   brecha_cambiaria, .-brecha_cambiaria

# pesos_a_dolares(0,0,0,0,0,0, pesos_cent, cotiz_cent) -> centavos de dólar
    .globl  pesos_a_dolares
    .type   pesos_a_dolares, @function
pesos_a_dolares:
    pushq   %rbp
    movq    %rsp, %rbp

    movq    16(%rbp), %rax      # %rax = pesos en centavos
    imulq   $100, %rax          # %rax = pesos * 100
    cqto
    idivq   24(%rbp)

    popq    %rbp
    ret
    .size   pesos_a_dolares, .-pesos_a_dolares

    .section .note.GNU-stack,"",@progbits
```

Tres detalles que conviene entender porque los van a preguntar:

- **`cqto` antes de `idivq` no es opcional.** `idivq` divide el valor de 128 bits que
  forman `%rdx:%rax` por el operando. Si `%rdx` tiene basura, el resultado es basura o el
  programa aborta. `cqto` extiende el signo de `%rax` hacia `%rdx`, dejando el dividendo
  bien formado. Es lo que hace que la brecha negativa dé bien.
- **`imulq $10000, %rax` es la forma de dos operandos**, que deja el resultado de 64 bits
  en `%rax`. Existe también `imulq %rcx` de un operando, que produce 128 bits en
  `%rdx:%rax` — pero combinarla con `cqto` después es un error, porque `cqto` pisa `%rdx`
  y destruye la mitad alta.
- **La línea `.note.GNU-stack`** evita el aviso `missing .note.GNU-stack section implies
  executable stack` que tiran los archivos del repositorio de cátedra.

#### Verificación de que los argumentos van por la pila

El desensamblado del llamador confirma el mecanismo:

```
push   -0x20(%rbp)          <- 8vo argumento a la pila
push   -0x18(%rbp)          <- 7mo argumento a la pila
mov    $0x0,%r9d            <- argumentos 1 a 6 por registros
mov    $0x0,%r8d
mov    $0x0,%ecx
mov    $0x0,%edx
mov    $0x0,%esi
mov    $0x0,%edi
call   <brecha_cambiaria>
add    $0x10,%rsp           <- el llamador limpia los 16 bytes
```

Y la rutina leyéndolos:

```
brecha_cambiaria:
    push   %rbp
    mov    %rsp,%rbp
    mov    0x10(%rbp),%rax       <- 7mo argumento
    sub    0x18(%rbp),%rax       <- 8vo argumento
    imul   $0x2710,%rax,%rax
    cqto
    idivq  0x18(%rbp)
    pop    %rbp
    ret
```

#### Probarla sola: `asm/prueba.c`

El `.s` no se puede ejecutar por sí mismo: necesita un programa que lo llame. Antes de
conectarlo con nada, se lo prueba con un `main` mínimo en C que le pasa valores fijos,
escritos a mano. Es probar el motor en el banco antes de montarlo en el auto.

```c
/* prueba.c — prueba de las rutinas en ensamblador con valores fijos.
   Los precios van en centavos: 1540,00 pesos = 154000. */
#include <stdio.h>

extern long brecha_cambiaria(long, long, long, long, long, long, long, long);
extern long pesos_a_dolares(long, long, long, long, long, long, long, long);

int main(void) {
    long blue    = 154000;   /* venta blue    del 12/10/2026 */
    long oficial = 153500;   /* venta oficial del 09/10/2026 */

    long brecha = brecha_cambiaria(0, 0, 0, 0, 0, 0, blue, oficial);
    printf("brecha: %ld centesimas = %ld.%02ld %%\n", brecha, brecha / 100, brecha % 100);

    long pesos   = 1000000;  /* 10.000,00 pesos */
    long dolares = pesos_a_dolares(0, 0, 0, 0, 0, 0, pesos, blue);
    printf("10000 pesos al blue: %ld centavos = USD %ld.%02ld\n", dolares, dolares / 100, dolares % 100);

    return 0;
}
```

Fijate en las llamadas: van **ocho** argumentos, seis ceros y los dos valores. Es a
propósito: como solo seis entran por registros, el compilador está obligado a mandar los
dos últimos **por la pila**.

Para compilar y correr, desde la carpeta `asm/`:

```bash
as --64 -g -o conversiones.o conversiones.s
gcc -g3 -O0 -c prueba.c -o prueba.o
gcc -o prueba prueba.o conversiones.o
./prueba
```

Tiene que imprimir exactamente:

```
brecha: 32 centesimas = 0.32 %
10000 pesos al blue: 649 centavos = USD 6.49
```

Y se verifica con la calculadora: (1540 − 1535) / 1535 × 100 = 0,3257 → **0,32 %**, y
10000 / 1540 = 6,4935 → **6,49**.

No tiene que aparecer el aviso de `.note.GNU-stack`: la última línea del `.s` lo evita. Si
aparece, el bloque no se copió entero.

### 6.4 La capa de C: `c/main.c`

Recibe los precios en centavos por línea de comandos, los valida, llama a las rutinas e
imprime los resultados como líneas `clave=valor`, que es un formato fácil de leer desde
Python.

```c
/* main.c — capa intermedia del TP.
 *
 * Recibe los precios en centavos por linea de comandos, los valida y llama a las
 * rutinas de calculo. Imprime los resultados como lineas clave=valor para que la
 * capa de Python los lea.
 *
 * Uso:  ./calculadora <blue_centavos> <oficial_centavos> [pesos_centavos]
 *
 * Las rutinas se declaran con ocho parametros: los seis primeros viajan por
 * registros y se pasan en cero; el 7mo y el 8vo no entran en los registros y la
 * ABI obliga a pasarlos por la pila.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

extern long brecha_cambiaria(long, long, long, long, long, long, long, long);
extern long pesos_a_dolares(long, long, long, long, long, long, long, long);

/* Cota de cordura: 1 billon de pesos. Por encima, las multiplicaciones de las
   rutinas podrian desbordar los 64 bits. */
#define MAX_CENTAVOS 100000000000000L

/* Convierte un argumento a long. Devuelve 0 si es un numero valido en rango. */
static int leer_centavos(const char *texto, const char *nombre, long *destino) {
    char *fin;
    errno = 0;
    long valor = strtol(texto, &fin, 10);

    if (fin == texto || *fin != '\0') {
        fprintf(stderr, "%s no es un numero entero: '%s'\n", nombre, texto);
        return 1;
    }
    if (errno == ERANGE || valor <= 0 || valor > MAX_CENTAVOS) {
        fprintf(stderr, "%s fuera de rango: '%s' (entre 1 y %ld centavos)\n", nombre, texto, MAX_CENTAVOS);
        return 1;
    }
    *destino = valor;
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc != 3 && argc != 4) {
        fprintf(stderr, "uso: %s <blue_centavos> <oficial_centavos> [pesos_centavos]\n", argv[0]);
        return 2;
    }

    long blue, oficial, pesos = 0;
    if (leer_centavos(argv[1], "blue", &blue))       return 1;
    if (leer_centavos(argv[2], "oficial", &oficial)) return 1;
    if (argc == 4 && leer_centavos(argv[3], "pesos", &pesos)) return 1;

    /* La validacion anterior garantiza oficial > 0 y blue > 0: idivq con
       divisor cero no devuelve un error, mata el proceso. */
    long brecha = brecha_cambiaria(0, 0, 0, 0, 0, 0, blue, oficial);
    printf("brecha_centesimas=%ld\n", brecha);

    if (argc == 4) {
        long dolares = pesos_a_dolares(0, 0, 0, 0, 0, 0, pesos, blue);
        printf("dolares_centavos=%ld\n", dolares);
    }
    return 0;
}
```

La validación no es decorativa. `idivq` con divisor cero **no devuelve un error: mata el
proceso** con una excepción del procesador. Por eso `main.c` rechaza el cero, los
negativos, el texto y los números fuera de rango **antes** de llamar a la rutina. Probado:

```
./calculadora 154000 0           ->  oficial fuera de rango: '0' (entre 1 y 100000000000000 centavos)
./calculadora abc 153500         ->  blue no es un numero entero: 'abc'
./calculadora 154000x 153500     ->  blue no es un numero entero: '154000x'
./calculadora 154000 153500 1000000
brecha_centesimas=32
dolares_centavos=649
```

La cota `MAX_CENTAVOS` existe porque las rutinas multiplican por 10.000: con números
gigantes la cuenta desbordaría los 64 bits y daría un resultado sin sentido, sin ningún
aviso.

#### La Iteración 1: `c/conversiones_c.c`

La consigna pide dos iteraciones: primero todo con C y Python **sin ensamblador**, y
después con ensamblador. Para no escribir dos programas, se escriben las mismas dos
rutinas en C puro, **con exactamente la misma firma**:

```c
/* conversiones_c.c — las mismas rutinas que asm/conversiones.s, en C puro.
 *
 * Es la Iteracion 1 del TP: todo resuelto con C y Python, sin ensamblador.
 * Tiene exactamente la misma firma que la version en ensamblador, asi main.c no
 * cambia entre iteraciones: solo se enlaza contra uno u otro archivo.
 *
 * La division entera de C trunca hacia cero, igual que idivq, de modo que las dos
 * versiones dan el mismo resultado tambien con brecha negativa.
 */

long brecha_cambiaria(long r1, long r2, long r3, long r4, long r5, long r6,
                      long blue, long oficial) {
    (void)r1; (void)r2; (void)r3; (void)r4; (void)r5; (void)r6;
    return (blue - oficial) * 10000 / oficial;
}

long pesos_a_dolares(long r1, long r2, long r3, long r4, long r5, long r6,
                     long pesos, long cotizacion) {
    (void)r1; (void)r2; (void)r3; (void)r4; (void)r5; (void)r6;
    return pesos * 100 / cotizacion;
}
```

`main.c` no cambia entre iteraciones: se enlaza contra `conversiones_c.c` para la primera
y contra `conversiones.s` para la segunda. El `Makefile` genera los dos binarios.

Tener las dos versiones sirve además como verificación cruzada: si dan distinto, el bug
está en el ensamblador. Comparadas sobre **2000 casos al azar, dan idéntico en todos**,
incluidas las brechas negativas, porque la división entera de C trunca hacia cero igual
que `idivq`.

### 6.5 La capa de Python: `python/cliente.py`

Baja las dos cotizaciones, convierte los precios a centavos con `round()`, llama al
binario de C y muestra el resultado.

Usa **solo la biblioteca estándar** (`urllib` en vez de `requests`): en Ubuntu,
`pip install` falla con *externally-managed-environment*, y así no hay nada que instalar.

```python
#!/usr/bin/env python3
"""cliente.py — capa superior del TP.

Consulta la cotizacion del dolar blue y oficial en dolarapi.com, convierte los
precios de venta a centavos y se los pasa al programa en C, que hace el calculo
llamando a las rutinas en ensamblador. Despues muestra el resultado.

Uso (desde la raiz del repositorio):
    python3 python/cliente.py                 brecha entre blue y oficial
    python3 python/cliente.py 10000           ademas, cuantos dolares son 10000 pesos
    python3 python/cliente.py 10000 --sin-asm usa la version en C puro (Iteracion 1)
    python3 python/cliente.py --solo-api      solo baja y muestra los datos, sin calcular

Usa solo la biblioteca estandar: no hace falta instalar nada con pip.
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# La URL base se puede cambiar con una variable de entorno, por ejemplo para
# probar contra un servidor local sin depender de internet.
API = os.environ.get("DOLARAPI_URL", "https://dolarapi.com/v1/dolares")
RAIZ = Path(__file__).resolve().parent.parent
TIMEOUT = 10  # segundos
# Algunas APIs rechazan con 403 el identificador por defecto de urllib
# ("Python-urllib/3.x") porque lo toman como un bot.
CABECERAS = {"User-Agent": "practico2-sistemas-de-computacion/1.0"}


def a_centavos(valor):
    """Convierte un precio en pesos a centavos enteros.

    round() y no int(): el punto flotante no representa exactamente la mayoria
    de los decimales, e int() trunca. 1024.09 * 100 da 102408.99999999999.
    """
    return round(float(valor) * 100)


def formatear(n):
    """Formatea centavos o centesimas al estilo argentino: 154000 -> '1.540,00'."""
    signo = "-" if n < 0 else ""
    entero, decimales = divmod(abs(n), 100)
    return f"{signo}{entero:,}".replace(",", ".") + f",{decimales:02d}"


def formatear_fecha(iso):
    """'2026-10-12T12:55:00.000Z' -> '12/10/2026 12:55 UTC'."""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M UTC")
    except (ValueError, AttributeError):
        return str(iso)


def obtener(casa):
    """Devuelve (precio de venta en centavos, fecha de actualizacion)."""
    url = f"{API}/{casa}"
    try:
        pedido = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(pedido, timeout=TIMEOUT) as respuesta:
            datos = json.load(respuesta)
    except urllib.error.HTTPError as e:
        sys.exit(f"Error: la API respondio {e.code} al pedir {url}")
    except urllib.error.URLError as e:
        sys.exit(f"Error: no se pudo conectar con {url} ({e.reason})")
    except TimeoutError:
        sys.exit(f"Error: la API no respondio en {TIMEOUT} segundos ({url})")
    except json.JSONDecodeError:
        sys.exit(f"Error: la respuesta de {url} no es JSON valido")

    if "venta" not in datos:
        sys.exit(f"Error: la respuesta de {url} no trae el campo 'venta'")
    try:
        centavos = a_centavos(datos["venta"])
    except (TypeError, ValueError):
        sys.exit(f"Error: el precio de venta de {url} no es un numero: {datos['venta']!r}")
    if centavos <= 0:
        sys.exit(f"Error: el precio de venta de {casa} es {datos['venta']}, no se puede calcular")

    return centavos, datos.get("fechaActualizacion", "sin fecha")


def calcular(binario, blue, oficial, pesos):
    """Invoca la capa de C y devuelve sus resultados como diccionario."""
    argumentos = [str(binario), str(blue), str(oficial)]
    if pesos is not None:
        argumentos.append(str(pesos))

    resultado = subprocess.run(argumentos, capture_output=True, text=True)
    if resultado.returncode != 0:
        sys.exit(f"Error en la capa de C: {resultado.stderr.strip()}")

    # La capa de C imprime lineas clave=valor.
    return {clave: int(valor)
            for clave, valor in (linea.split("=", 1) for linea in resultado.stdout.split())}


def main():
    argumentos = sys.argv[1:]
    sin_asm = "--sin-asm" in argumentos
    solo_api = "--solo-api" in argumentos
    argumentos = [a for a in argumentos if a not in ("--sin-asm", "--solo-api")]

    if solo_api:
        # Prueba de la capa de Python sola: no hace falta tener nada compilado.
        for casa in ("blue", "oficial"):
            centavos, fecha = obtener(casa)
            print(f"{casa:8} venta = {centavos} centavos  ({formatear_fecha(fecha)})")
        return

    pesos = None
    if argumentos:
        try:
            pesos = a_centavos(argumentos[0].replace(",", "."))
        except ValueError:
            sys.exit(f"Error: '{argumentos[0]}' no es un monto valido")
        if pesos <= 0:
            sys.exit("Error: el monto tiene que ser mayor que cero")

    binario = RAIZ / ("calculadora_c" if sin_asm else "calculadora")
    if not binario.exists():
        sys.exit(f"Error: no existe {binario.name}. Compila primero con 'make'.")

    blue, fecha_blue = obtener("blue")
    oficial, fecha_oficial = obtener("oficial")

    resultado = calcular(binario, blue, oficial, pesos)

    print(f"Dolar blue     venta $ {formatear(blue):>10}   (actualizado {formatear_fecha(fecha_blue)})")
    print(f"Dolar oficial  venta $ {formatear(oficial):>10}   (actualizado {formatear_fecha(fecha_oficial)})")
    print()
    print(f"Brecha cambiaria: {formatear(resultado['brecha_centesimas'])} %")
    if pesos is not None:
        print(f"$ {formatear(pesos)} al dolar blue = USD {formatear(resultado['dolares_centavos'])}")
    print()
    capa = "C puro (Iteracion 1)" if sin_asm else "ensamblador (Iteracion 2)"
    print(f"Calculo realizado en: {capa}")


if __name__ == "__main__":
    main()
```

Formas de usarlo, siempre desde la raíz del repositorio:

```bash
python3 python/cliente.py --solo-api        # paso 2: solo la API, sin nada compilado
python3 python/cliente.py                   # brecha entre blue y oficial
python3 python/cliente.py 10000             # ademas, cuantos dolares son $10.000
python3 python/cliente.py 10000 --sin-asm   # lo mismo con la Iteracion 1 (C puro)
```

Salida esperada con los datos del 12/10/2026:

```
Dolar blue     venta $   1.540,00   (actualizado 12/10/2026 12:55 UTC)
Dolar oficial  venta $   1.535,00   (actualizado 09/10/2026 18:55 UTC)

Brecha cambiaria: 0,32 %
$ 10.000,00 al dolar blue = USD 6,49

Calculo realizado en: ensamblador (Iteracion 2)
```

Los errores salen como un mensaje claro, sin volcado de Python. Probados: API caída, API
que responde 500, respuesta que no es JSON, falta el campo `venta`, precio en cero, monto
inválido, y binario sin compilar.

> **Sobre la prueba.** Desde el entorno donde se armó esta guía no se puede llegar a
> dolarapi.com, así que el cliente se probó contra un servidor local que devuelve
> **exactamente** el JSON obtenido con `curl` en el Paso 0. La URL base se puede cambiar
> con la variable de entorno `DOLARAPI_URL` justamente para eso. Hay que correrlo una vez
> contra la API real para confirmar.

### 6.6 El `Makefile`

Para no tipear los `as` y `gcc` a mano cada vez:

```make
# Makefile — compila las dos iteraciones del TP.
#
#   make          compila las dos versiones
#   make iter1    calculadora_c : C puro, sin ensamblador (Iteracion 1)
#   make iter2    calculadora   : C + ensamblador         (Iteracion 2)
#   make prueba   compila y corre asm/prueba.c contra el ensamblador
#   make clean    borra todo lo compilado
#
# OJO: las lineas de las recetas (las que tienen comandos) tienen que empezar
# con un TAB, no con espacios. Si make dice "missing separator", es eso.

CC      = gcc
AS      = as
CFLAGS  = -g3 -O0 -Wall -Wextra
ASFLAGS = --64 -g

.PHONY: all iter1 iter2 prueba clean

all: iter1 iter2

iter1: calculadora_c
iter2: calculadora

calculadora: c/main.o asm/conversiones.o
	$(CC) -o $@ $^

calculadora_c: c/main.o c/conversiones_c.o
	$(CC) -o $@ $^

asm/prueba: asm/prueba.o asm/conversiones.o
	$(CC) -o $@ $^

prueba: asm/prueba
	./asm/prueba

c/%.o: c/%.c
	$(CC) $(CFLAGS) -c -o $@ $<

asm/%.o: asm/%.c
	$(CC) $(CFLAGS) -c -o $@ $<

asm/%.o: asm/%.s
	$(AS) $(ASFLAGS) -o $@ $<

clean:
	rm -f c/*.o asm/*.o calculadora calculadora_c asm/prueba
```

> Las líneas con comandos **tienen que empezar con un TAB**, no con espacios. Si al pegar
> el editor convierte los TAB en espacios, `make` falla con `missing separator`. En VS
> Code se ve abajo a la derecha: tiene que decir "Tab Size", no "Spaces".

### 6.7 Cómo correr todo

Desde la raíz del repositorio:

```bash
make                                   # compila las dos iteraciones
make prueba                            # corre asm/prueba.c
python3 python/cliente.py 10000        # el TP completo
```

Los binarios `calculadora`, `calculadora_c` y `asm/prueba`, y los `.o`, **no se suben**:
son resultado de compilar y cada uno los genera en su máquina. Ya están en `.gitignore`.

### 6.8 La sesión de GDB: el stack antes, durante y después

Es el requisito que más pesa: la consigna pide **mostrar con GDB el estado del área de
memoria que contiene el stack antes, durante y después de la función**. Se depura el TP
real, `./calculadora`, con los valores del 12/10/2026.

```bash
make
gdb --args ./calculadora 154000 153500 1000000
```

`--args` le dice a GDB que lo que sigue son los argumentos del programa.

Dentro de GDB, **un comando por línea**:

```
dashboard memory watch $rsp 48
break main.c:55
break brecha_cambiaria
run
```

La línea 55 de `main.c` es la llamada a `brecha_cambiaria`. El programa se detiene ahí,
antes de preparar los argumentos.

#### ANTES — el llamador prepara la llamada

```
x/12i $pc
info registers rsp rbp
```

`x/12i $pc` muestra las doce instrucciones que siguen. Es la evidencia central de que los
argumentos van por la pila:

```
mov    -0x28(%rbp),%rdx           <- carga oficial
mov    -0x30(%rbp),%rax           <- carga blue
push   %rdx                       <- 8vo argumento (oficial) a la pila
push   %rax                       <- 7mo argumento (blue) a la pila
mov    $0x0,%r9d                  <- argumentos 1 a 6 por registros, en cero
mov    $0x0,%r8d
mov    $0x0,%ecx
mov    $0x0,%edx
mov    $0x0,%esi
mov    $0x0,%edi
call   <brecha_cambiaria>
add    $0x10,%rsp                 <- al volver, el llamador limpia los 16 bytes
```

📸 **Captura 1.** Anotar los valores de `%rsp` y `%rbp`: son la referencia del "antes".

Ahora se ejecutan los dos `push`. Hacer `stepi` y mirar el panel **Assembly** hasta que la
flecha quede sobre el primer `mov $0x0,%r9d` (son 4 `stepi`: los dos `mov` y los dos
`push`; con otra versión de gcc puede variar). Entonces:

```
info registers rsp
x/2gx $rsp
```

```
0x...880:  0x0000000000025990  0x000000000002579c
```

`0x25990` es **154000** (blue) y `0x2579c` es **153500** (oficial): los dos argumentos ya
están en la cima de la pila, y `%rsp` bajó **16 bytes**. El blue queda en la dirección más
baja porque se empujó último.

📸 **Captura 2.**

#### DURANTE — la rutina lee sus argumentos de la pila

```
continue
```

El programa se detiene en la primera instrucción de `brecha_cambiaria`, antes del
prólogo:

```
x/3gx $rsp
```

```
0x...878:  0x00005555555553aa  0x0000000000025990
0x...888:  0x000000000002579c
```

El `call` apiló la **dirección de retorno** (`main+295`, la instrucción `add $0x10,%rsp`
que se vio en la Captura 1) encima de los argumentos. `%rsp` bajó otros 8 bytes.

Se ejecuta el prólogo (`pushq %rbp` y `movq %rsp,%rbp`):

```
stepi
stepi
x/4gx $rbp
```

```
0x...870:  0x00007fffffffc8d0  0x00005555555553aa     <- 0(%rbp)  y 8(%rbp)
0x...880:  0x0000000000025990  0x000000000002579c     <- 16(%rbp) y 24(%rbp)
```

Este es **el marco completo**, exactamente como lo describe el comentario de
`conversiones.s`:

| Dirección | Contenido | Quién lo puso |
|---|---|---|
| `0(%rbp)` | `%rbp` de `main` | `pushq %rbp` del prólogo |
| `8(%rbp)` | dirección de retorno, `main+295` | `call` |
| `16(%rbp)` | `0x25990` = 154000, blue | `push %rax` de `main` |
| `24(%rbp)` | `0x2579c` = 153500, oficial | `push %rdx` de `main` |

📸 **Captura 3. Es la más importante del TP:** muestra que la rutina recibe sus
parámetros por la pila y no por registros.

Se deja correr la cuenta hasta el epílogo:

```
advance 28
info registers rax rdx
```

`advance 28` avanza hasta la línea 28 de `conversiones.s`, el `popq %rbp`.

```
rax  0x20     32
rdx  0x157c0  88000
```

`%rax` = **32** centésimas = 0,32 %. `%rdx` tiene el **resto** de la división, que `idivq`
deja ahí y que se descarta: 5.000.000 = 32 × 153.500 + 88.000.

📸 **Captura 4.**

#### DESPUÉS — el stack vuelve a su estado original

```
stepi
stepi
x/i $pc
info registers rsp
```

El `popq %rbp` y el `ret` ya se ejecutaron: estamos de vuelta en `main`, parados en el
`add $0x10,%rsp`. `%rsp` todavía apunta a los dos argumentos: **la rutina no los limpia, lo
hace el llamador**.

```
stepi
info registers rsp rbp rax
```

Después del `add`, `%rsp` y `%rbp` tienen **exactamente los mismos valores que en la
Captura 1**, y el resultado sigue en `%rax`.

📸 **Captura 5.**

El recorrido completo de `%rsp`:

```
antes    2 push    call    prólogo   epílogo    ret     add $0x10
 c890  →  c880  →  c878  →  c870  →   c878  →   c880  →   c890
         −16       −8       −8        +8        +8        +16
```

#### Qué tiene que coincidir en tu máquina

Las direcciones del stack (`0x7fffffffc...`) y los desplazamientos como `main+295` pueden
ser distintos según la máquina y la versión de gcc. Lo que **tiene** que coincidir:

- los valores `0x25990`, `0x2579c`, `0x20` y `0x157c0`;
- las **diferencias** de `%rsp` del cuadro anterior;
- que en `8(%rbp)` esté la dirección de la instrucción `add $0x10,%rsp`;
- que en la Captura 5, `%rsp` y `%rbp` sean iguales a los de la Captura 1.

### 6.9 Paso a paso, commit por commit

La consigna pide un commit por funcionalidad implementada **y validada**. Este desglose
cumple eso y además permite repartir el trabajo entre los tres.

| # | Paso | Qué tiene que quedar validado |
|---|---|---|
| 0 | `curl` a los dos endpoints, mirar el JSON crudo | ✅ Hecho: los campos son `venta` y `fechaActualizacion` |
| 1 | Escribir la decisión de punto fijo | ✅ Hecho: centavos (×100), precio de venta, `round()` al convertir |
| 2 | `python/cliente.py` (sección 6.5), probado con `--solo-api` | Python solo, sin nada compilado |
| 3 | `asm/conversiones.s` + `asm/prueba.c` (sección 6.3) | `./prueba` da 0,32 % y USD 6,49 |
| 4 | `c/main.c` + `c/conversiones_c.c` + `Makefile` (6.4 y 6.6) | `make` compila las dos iteraciones sin warnings |
| 5 | Integración: `python3 python/cliente.py 10000` | Las tres capas conectadas, contra la API real |
| 6 | Sesión de GDB de la sección 6.8 | **El requisito que más pesa**: las 5 capturas |
| 7 | Probar los casos de error de 6.4 y 6.5 | Cada error da un mensaje claro y no se rompe nada |
| 8 | README con compilación, uso y evidencia | Listo para entregar |

Dos cosas sobre el orden, que no son caprichosas:

- **El paso 3 va antes que el 4** a propósito. Primero la rutina con valores fijos y un
  `main.c` mínimo; recién cuando da bien se la conecta a la entrada real. Si se hace todo
  junto y falla, no se sabe si el problema está en el parseo de Python, en el pasaje de
  argumentos o en el ensamblador.
- **El paso 6 no es el último.** Si GDB se deja para el final y algo no cierra, hay que
  rehacer la rutina con el informe ya escrito.

#### El caso borde que hay que cubrir sí o sí

`idivq` **aborta el programa** si el divisor es cero — no devuelve un error, lo mata con
una excepción de hardware. Si la API devolviera el oficial en `0`, o si el parseo fallara
y mandara un `0`, el binario se cae. La validación va en C antes de llamar a la rutina, y
está resuelto en `main.c` (sección 6.4); el paso 7 es comprobarlo.

### 6.10 Estructura de archivos

```
practico2/
├── README.md              portada e instrucciones de compilación
├── CONSIGNA.md            los requisitos del TP
├── GUIA.md                esta guía
├── PROCEDIMIENTO.md       el registro de lo hecho, con capturas
├── Makefile               para no tipear los as/gcc a mano
├── asm/
│   ├── conversiones.s     las rutinas de cálculo (Iteración 2)
│   └── prueba.c           prueba de las rutinas con valores fijos
├── c/
│   ├── main.c             capa intermedia
│   └── conversiones_c.c   las mismas rutinas en C puro (Iteración 1)
├── python/
│   └── cliente.py         capa superior
└── capturas/              las capturas de las sesiones de GDB
```

`make` genera además `calculadora`, `calculadora_c` y `asm/prueba`, que no se suben.

---

## Parte 7 — Por dónde seguir

Las Partes 1 a 5 están terminadas y documentadas en `PROCEDIMIENTO.md`. Lo que queda es
el TP propiamente dicho, siguiendo la tabla de 6.9. Todo el código está en las
secciones 6.3 a 6.6, probado; cada paso consiste en crear los archivos, compilar,
verificar que la salida coincida con la de la guía, y commitear.

1. ~~Paso 0: verificar los campos de la API~~ y ~~Paso 1: decidir el punto fijo~~ — hechos
   (ver 6.2).
2. Pasos 2 y 3 en paralelo, que no dependen uno del otro: uno arma `python/cliente.py` y
   lo prueba con `--solo-api`; otro arma `asm/conversiones.s` y `asm/prueba.c`.
3. Paso 4 cuando el 3 esté validado.
4. Integración, GDB y errores, en ese orden.

---

## Referencia rápida de comandos GDB

| Comando | Qué hace |
|---|---|
| `break *funcion` | Breakpoint en la primera instrucción (sin saltar el prólogo) |
| `run` | Arranca el programa |
| `stepi` / `si` | Ejecuta **una** instrucción de máquina |
| `nexti` / `ni` | Igual, pero sin entrar a los `call` |
| `continue` / `c` | Sigue hasta el próximo breakpoint |
| `info registers rsp rbp rip` | Muestra esos registros |
| `x/4gx $rsp` | 4 quadwords en hexa desde la cima de la pila |
| `x/1gx $rbp+16` | El quadword en `rbp+16` (el 7mo argumento) |
| `disassemble funcion` | Desensambla la función |
| `p $rax` | Imprime el valor de un registro |
| `backtrace` / `bt` | Cadena de llamadas (usa los `%rbp` encadenados) |
| `quit` | Salir |
