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
