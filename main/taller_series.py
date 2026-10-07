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

# Estados exactamente como en el AFD del diagrama.
INICIAL = "q0"
FINAL = "q23"
SUMIDERO = "qs"
ARCHIVO_JSON = Path(__file__).with_name("historial_series.json")

# Cada regla representa una flecha del AFD:
# (estado_origen, simbolos_permitidos, estado_destino)
REGLAS = [
    # Nombre de la serie: Bocchi_the_Rock_
    ("q0", ALFANUMERICOS, "q1"),
    ("q1", ALFANUMERICOS, "q1"),
    ("q1", "_", "q2"),
    ("q2", ALFANUMERICOS, "q1"),
    ("q2", "(", "q3"),

    # Año entre 1900 y 2026
    ("q3", "1", "q4"),
    ("q3", "2", "q5"),

    # Rama 19xx
    ("q4", "9", "q6"),
    ("q6", DIGITOS, "q8"),
    ("q8", DIGITOS, "q10"),
    ("q10", ")", "q12"),

    # Rama 2000-2019
    ("q5", "0", "q7"),
    ("q7", "01", "q24"),
    ("q24", DIGITOS, "q11"),

    # Rama 2020-2026
    ("q7", "2", "q9"),
    ("q9", "0123456", "q11"),
    ("q11", ")", "q12"),

    # Separador y temporada: _S1, _S2, ...
    ("q12", "_", "q13"),
    ("q13", "S", "q14"),
    ("q14", POSITIVOS, "q15"),
    ("q15", DIGITOS, "q15"),
    ("q15", "E", "q16"),

    # Episodio con al menos dos dígitos.
    # Ejemplo E07: q16 --0--> q17 --7--> q19
    ("q16", "0", "q17"),
    ("q16", POSITIVOS, "q18"),
    ("q17", "0", "q17"),
    ("q17", POSITIVOS, "q19"),
    ("q18", DIGITOS, "q25"),
    ("q19", DIGITOS, "q19"),
    ("q25", DIGITOS, "q25"),

    # Punto y extensión de 3 letras: .mkv
    ("q19", ".", "q20"),
    ("q25", ".", "q20"),
    ("q20", string.ascii_lowercase, "q21"),
    ("q21", string.ascii_lowercase, "q22"),
    ("q22", string.ascii_lowercase, "q23"),
]

# Incluimos q0...q25 y qs para que los nombres de estado coincidan
# con el diagrama, aunque algunas rutas no usen todos a la vez.
ESTADOS = frozenset({f"q{i}" for i in range(26)} | {SUMIDERO})

# Toda transición no dibujada en el AFD cae al estado basura qs.
TRANSICIONES = {(q, c): SUMIDERO for q in ESTADOS for c in ALFABETO}
for origen, simbolos, destino in REGLAS:
    for simbolo in simbolos:
        TRANSICIONES[origen, simbolo] = destino

# qs es estado basura: una vez se entra, no se puede salir.
for simbolo in ALFABETO:
    TRANSICIONES[SUMIDERO, simbolo] = SUMIDERO


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
