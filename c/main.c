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
