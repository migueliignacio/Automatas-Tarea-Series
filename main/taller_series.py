"""AFD para nombres de episodios. Ejecutar con Python 3: python taller_series.py.

No requiere bibliotecas externas. La tabla TRANSICIONES representa la máquina;
no se usan expresiones regulares ni conversiones a enteros para validar.
"""

import json
import string
from datetime import datetime
from pathlib import Path

LETRAS = string.ascii_letters
DIGITOS = string.digits
POSITIVOS = "123456789"
ALFANUMERICOS = LETRAS + DIGITOS
ALFABETO = frozenset(ALFANUMERICOS + "_().")
INICIAL = "q0"
FINAL = "q_final"
SUMIDERO = "q_error"
ARCHIVO_JSON = Path(__file__).with_name("historial_series.json")

# Cada fila: estado de origen, símbolos permitidos, estado de destino.
# Los conjuntos de símbolos de las filas de un mismo origen son disjuntos.
REGLAS = [
    ("q0", ALFANUMERICOS, "q_nombre"),
    ("q_nombre", ALFANUMERICOS, "q_nombre"),
    ("q_nombre", "_", "q_guion"),
    ("q_guion", ALFANUMERICOS, "q_nombre"),
    ("q_guion", "(", "q_anio"),
    ("q_anio", "1", "q_1"),
    ("q_anio", "2", "q_2"),
    ("q_1", "9", "q_19"),
    ("q_19", DIGITOS, "q_19d"),
    ("q_19d", DIGITOS, "q_anio_fin"),
    ("q_2", "0", "q_20"),
    ("q_20", "01", "q_200_201"),
    ("q_200_201", DIGITOS, "q_anio_fin"),
    ("q_20", "2", "q_202"),
    ("q_202", "0123456", "q_anio_fin"),
    ("q_anio_fin", ")", "q_parentesis"),
    ("q_parentesis", "_", "q_separador"),
    ("q_separador", "S", "q_S"),
    ("q_S", POSITIVOS, "q_temporada"),
    ("q_temporada", DIGITOS, "q_temporada"),
    ("q_temporada", "E", "q_E"),
    ("q_E", "0", "q_ep_un_cero"),
    ("q_E", POSITIVOS, "q_ep_un_positivo"),
    ("q_ep_un_cero", "0", "q_ep_ceros"),
    ("q_ep_un_cero", POSITIVOS, "q_episodio"),
    ("q_ep_un_positivo", DIGITOS, "q_episodio"),
    ("q_ep_ceros", "0", "q_ep_ceros"),
    ("q_ep_ceros", POSITIVOS, "q_episodio"),
    ("q_episodio", DIGITOS, "q_episodio"),
    ("q_episodio", ".", "q_punto"),
    ("q_punto", string.ascii_lowercase, "q_ext1"),
    ("q_ext1", string.ascii_lowercase, "q_ext2"),
    ("q_ext2", string.ascii_lowercase, FINAL),
]

ESTADOS = frozenset(
    {INICIAL, FINAL, SUMIDERO}
    | {origen for origen, _, _ in REGLAS}
    | {destino for _, _, destino in REGLAS}
)
# Función total delta: todo par no especificado conduce al sumidero.
TRANSICIONES = {(q, c): SUMIDERO for q in ESTADOS for c in ALFABETO}
for origen, simbolos, destino in REGLAS:
    for simbolo in simbolos:
        TRANSICIONES[origen, simbolo] = destino


def simular_afd(cadena):
    """Devuelve (aceptada, recorrido); consume la cadena completa, sin alterarla."""
    estado = INICIAL
    recorrido = []
    for simbolo in cadena:
        siguiente = TRANSICIONES.get((estado, simbolo), SUMIDERO)
        recorrido.append((estado, simbolo, siguiente))
        estado = siguiente
    return estado == FINAL, recorrido


def afd_token(token, mostrar=True):
    valido, recorrido = simular_afd(token)
    if mostrar:
        print("\n--- RECORRIDO DEL AFD ---")
        print("Estado inicial:", INICIAL)
        for origen, simbolo, destino in recorrido:
            print(f"{origen} --[{simbolo!r}]--> {destino}")
        print("Resultado AFD:", "VÁLIDO" if valido else "INVÁLIDO")
        if not valido:
            fallo = next((i for i, paso in enumerate(recorrido, 1)
                          if paso[2] == SUMIDERO), None)
            if fallo is not None:
                print(f"Transición no permitida en la posición {fallo}.")
            else:
                print("La cadena terminó antes de alcanzar el estado final.")
    return valido


def obtener_derivacion(token):
    """Gramática lineal derecha: Q_origen -> símbolo Q_destino; Q_final -> ε.

    Se utiliza la gramática equivalente a la tabla, sin producciones al sumidero.
    Cada paso sustituye un único no terminal mediante una producción real.
    """
    no_terminal = INICIAL
    prefijo = ""
    pasos = [f"<{INICIAL}>"]
    for simbolo in token:
        destino = TRANSICIONES.get((no_terminal, simbolo), SUMIDERO)
        if destino == SUMIDERO:
            return False, pasos
        prefijo += simbolo
        no_terminal = destino
        pasos.append(f"{prefijo}<{no_terminal}>")
    if no_terminal != FINAL:
        return False, pasos
    pasos.append(prefijo)  # <q_final> -> ε
    return True, pasos


def derivacion_gramatical(token):
    valido, pasos = obtener_derivacion(token)
    print("\n--- DERIVACIÓN GRAMATICAL ---")
    for numero, paso in enumerate(pasos, 1):
        print(f"({numero}) {paso}")
    print("Resultado gramatical:", "VÁLIDO" if valido else "INVÁLIDO")
    if not valido:
        print("No existe una derivación completa para esta cadena.")
    return valido


def leer_registros():
    if not ARCHIVO_JSON.exists():
        return []
    with ARCHIVO_JSON.open(encoding="utf-8") as archivo:
        registros = json.load(archivo)
    if not isinstance(registros, list) or any(
        not isinstance(r, dict)
        or not {"token", "valido", "tipo", "fecha"}.issubset(r)
        or not isinstance(r["valido"], bool)
        for r in registros
    ):
        raise ValueError("El historial no tiene el formato esperado.")
    return registros


def guardar_resultado_json(token, valido, tipo, derivacion=None):
    try:
        registros = leer_registros()
        registros.append({
            "token": token,
            "valido": valido,
            "tipo": tipo,
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "derivacion": derivacion,
        })
        temporal = ARCHIVO_JSON.with_suffix(".tmp")
        temporal.write_text(json.dumps(registros, ensure_ascii=False, indent=4),
                            encoding="utf-8")
        temporal.replace(ARCHIVO_JSON)
    except (OSError, ValueError) as error:
        print(f"No se pudo guardar el resultado: {error}")
        print("El historial existente no fue reemplazado.")


def mostrar_registros():
    try:
        registros = leer_registros()
    except (OSError, ValueError) as error:
        print(f"No se pudo leer el historial: {error}")
        return
    print("\n--- HISTORIAL ---")
    if not registros:
        print("No hay registros.")
    for registro in registros:
        estado = "VÁLIDO" if registro["valido"] else "INVÁLIDO"
        print(f"{registro['fecha']} | {registro['tipo']} | "
              f"{registro['token']!r} | {estado}")


def crear_token(nombre, anio, temporada, episodio, extension):
    # Solo la creación convierte los espacios entre palabras en guiones bajos.
    nombre = nombre.strip().replace(" ", "_")
    return f"{nombre}_({anio})_S{temporada}E{episodio}.{extension}"


def mostrar_reglas():
    print("\nFormato: NOMBRE_SERIE_(AÑO)_S#E##.ext")
    print("Nombre: letras A-Z, a-z y números; palabras separadas por un solo _.")
    print("Año: entre 1900 y 2026, inclusive.")
    print("Temporada: entero positivo sin ceros iniciales, sin límite de dígitos.")
    print("Episodio: al menos dos dígitos y alguno distinto de cero (01, 10, 001).")
    print("Extensión: exactamente tres letras de a-z, sin incluir el punto.")
    print("Ejemplo: Bocchi_the_Rock_(2022)_S1E07.mkv")


def menu():
    while True:
        print("\n--- MENÚ DE EPISODIOS ---")
        print("1. Crear nombre de archivo")
        print("2. Comprobar por AFD")
        print("3. Comprobar por gramática")
        print("4. Ver historial")
        print("5. Salir")
        print("6. Ver reglas y ejemplo")
        opcion = input("Elige una opción: ").strip()
        if opcion == "1":
            mostrar_reglas()
            token = crear_token(
                input("Nombre de la serie: "),
                input("Año: "),
                input("Temporada (ej. 1): "),
                input("Episodio (ej. 07): "),
                input("Extensión (ej. mkv): "),
            )
            print(f"\nNombre propuesto: {token}")
            valido = afd_token(token)
            derivacion_gramatical(token)
            _, pasos = obtener_derivacion(token)
            guardar_resultado_json(token, valido, "creacion", pasos)
        elif opcion == "2":
            token = input("Nombre de archivo a comprobar: ")
            guardar_resultado_json(token, afd_token(token), "AFD")
        elif opcion == "3":
            token = input("Nombre de archivo para derivar: ")
            valido = derivacion_gramatical(token)
            _, pasos = obtener_derivacion(token)
            guardar_resultado_json(token, valido, "gramatica", pasos)
        elif opcion == "4":
            mostrar_registros()
        elif opcion == "5":
            print("Saliendo...")
            break
        elif opcion == "6":
            mostrar_reglas()
        else:
            print("Opción inválida. Elige entre 1 y 6.")


if __name__ == "__main__":
    try:
        menu()
    except (EOFError, KeyboardInterrupt):
        print("\nPrograma finalizado.")
