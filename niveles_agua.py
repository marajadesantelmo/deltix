# -*- coding: utf-8 -*-
"""
Escala de altura del agua en el Delta.

Referencia del equipo Deltix para interpretar las alturas de la tabla de
Hidrografia Naval, que vienen en metros y sin ninguna lectura: "0.45" no le dice
nada a nadie que no viva midiendo el rio.

Bandas:
    menos de 0,40 m   muy baja
    0,40 a 1 m        baja
    1 a 3 m           alta
    3 a 4 m           muy alta
    4 m o mas         evacuacion

OJO con el tramo de 2 a 3 metros: la referencia original decia "1 a 2 metros
alta" y "3 metros muy alta", sin nombrar que pasa en el medio. Se extiende
"alta" hasta los 3 porque es la unica lectura que no deja un hueco, pero si el
tramo de 2 a 3 tiene que ser su propia categoria, se cambia aca y sale en los
dos lados.

Vive en un modulo propio, como interislena_museo y mareas_frescura, porque lo
usan deltix_funciones (Telegram) y web_app (Flask), que no se importan entre si.
"""

# (piso en metros, etiqueta). De mayor a menor: se devuelve la primera que entra.
BANDAS = [
    (4.0,  "evacuación"),
    (3.0,  "muy alta"),
    (1.0,  "alta"),
    (0.40, "baja"),
    (0.0,  "muy baja"),
]

# Texto para el LLM. Es la misma escala de BANDAS escrita en prosa: si se toca
# una hay que tocar la otra, por eso estan pegadas.
ESCALA_PARA_LLM = (
    "Escala de altura del agua en el Delta, para interpretar las alturas en metros "
    "de la tabla: menos de 0,40 m es MUY BAJA; de 0,40 a 1 m es BAJA; de 1 a 3 m es "
    "ALTA; de 3 a 4 m es MUY ALTA; 4 m o mas es situacion de EVACUACION. "
    "Usa esta escala para decir si el agua va a estar alta o baja, en vez de dar el "
    "numero solo. Si la altura llega a 3 m o mas, avisale al usuario que es una "
    "creciente importante; si llega a 4 m, decile que es situacion de evacuacion y "
    "que se contacte con Prefectura. No inventes alturas que no esten en la tabla."
)


def clasificar(altura):
    """Etiqueta para una altura en metros. None si no es un numero usable.

    Acepta el string crudo de la tabla, que puede venir '---' o con coma decimal.
    """
    if altura is None:
        return None
    if isinstance(altura, str):
        altura = altura.strip().replace(',', '.')
        if altura.strip('-') == '':
            return None          # las filas sin dato vienen '---'
    try:
        metros = float(altura)
    except (TypeError, ValueError):
        return None
    for piso, etiqueta in BANDAS:
        if metros >= piso:
            return etiqueta
    return None


def describir(altura):
    """'0.45' -> 'baja'. Devuelve '' si no se puede clasificar, para poder
    concatenarlo sin chequear."""
    etiqueta = clasificar(altura)
    return etiqueta or ""


def frase(altura):
    """Texto listo para pegar despues de la altura en un mensaje. La banda de
    evacuacion no se escribe como adjetivo ('agua evacuacion' no quiere decir
    nada): va como alerta."""
    etiqueta = clasificar(altura)
    if etiqueta is None:
        return ""
    if etiqueta == "evacuación":
        return "⚠️ NIVEL DE EVACUACIÓN"
    return "agua %s" % etiqueta
