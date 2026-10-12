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
    