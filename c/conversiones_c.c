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
