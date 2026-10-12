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

	