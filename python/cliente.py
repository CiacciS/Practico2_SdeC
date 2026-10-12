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
    