# -*- coding: utf-8 -*-
"""
Horarios de Interisleña en el Museo Sarmiento.

El Museo Casa de Domingo Faustino Sarmiento es la parada mas pedida del Delta:
TODOS los recorridos de Interisleña pasan por ahi, asi que sirve de referencia
para cualquiera que vaya o vuelva de la isla sin importar por que arroyo entre.

Fuente de los horarios: el cartel del muelle del Museo, fotografiado en
colectivas/interislena_deep/Interisleña Museo - Tigre.jpeg, con una correccion
del equipo Deltix: donde el cartel dice 18:10 la salida es 18:30. Si alguien
compara la lista con la foto, esa es la unica diferencia y es a proposito.

El cartel dice "DIAS DE SEMANA" y no trae sabados ni domingos. El fin de semana
lo aporto el equipo Deltix: son los mismos horarios que de lunes a viernes, pero
salen menos lanchas al final del dia, asi que la ultima que sale de Tigre es la
de las 20:00 el sabado y la de las 19:00 el domingo. La vuelta desde el Museo no
cambia. Por eso el fin de semana se calcula recortando la lista de semana en vez
de escribirla aparte: un horario nuevo se agrega en un solo lugar.

Validacion: los 16 horarios de la columna "DE TIGRE" existen los 16 en las
salidas de lunes a viernes que ya estaban cargadas en rag/interislena.txt,
repartidos entre varias rutas. O sea que la columna es la union de las rutas que
pasan por el Museo, y confirma que el cartel es de Interisleña.

Los tres horarios de lunes a viernes que tenemos y esta lista no incluye son
17:00 (Antequera y Abra Vieja, los dos "solo viernes"), 18:00 (Espera / Cruz
Colorada) y 18:10 (Paso del Toro), que aparentemente no paran en el Museo.

Este dato vive en un modulo propio porque lo usan deltix_funciones (Telegram) y
web_app (Flask), que no se importan entre si. Duplicarlo en los dos garantiza
que tarde o temprano uno quede viejo.
"""

# Columna "DE TIGRE" del cartel: salidas desde la Estacion Fluvial de Tigre.
# El 18:30 es la correccion del docstring; el cartel ahi dice 18:10.
DE_TIGRE = ["7:00", "8:00", "8:30", "9:00", "10:00", "11:30", "12:45", "14:15",
            "15:00", "15:30", "16:15", "17:30", "18:30", "19:00", "20:00", "21:00"]

# Columna "A TIGRE" del cartel: horarios en que la lancha pasa por el muelle del
# Museo rumbo a Tigre, no horarios de llegada a la Estacion Fluvial. Esta
# columna es igual todos los dias: el recorte del fin de semana es solo de ida.
A_TIGRE = ["5:50", "6:50", "7:30", "7:50", "9:45", "10:45", "11:45", "14:00",
           "15:30", "16:00", "17:30", "18:15", "19:30"]

# Ultima salida de Tigre cada dia del fin de semana. Ver el docstring.
ULTIMA_SALIDA_FINDE = {"sabado": "20:00", "domingo": "19:00"}

# Tigre <-> Museo. Dato del equipo Deltix, no del cartel.
VIAJE_MINUTOS = 30

TELEFONO = "4749-0900"

# Explicacion del recorrido, tambien usada en el RAG para que el LLM pueda
# responder preguntas sueltas sobre el Museo sin depender del menu.
EXPLICACION = (
    "El Museo Casa de Domingo Faustino Sarmiento es la parada mas pedida del "
    "Delta: todos los recorridos de Interisleña pasan por el Museo, sin importar "
    "por que arroyo sigan despues."
)


def _en_filas(horarios, por_fila=6):
    """Parte la lista en renglones cortos: una tira de 16 horarios seguidos no
    se lee en la pantalla de un celular."""
    return "\n".join(" · ".join(horarios[i:i + por_fila])
                     for i in range(0, len(horarios), por_fila))


def _minutos(horario):
    hora, minuto = horario.split(":")
    return int(hora) * 60 + int(minuto)


def de_tigre(dia="semana"):
    """Salidas de Tigre hacia el Museo. Con dia='sabado' o 'domingo' devuelve
    las mismas de lunes a viernes recortadas en la ultima salida de ese dia."""
    tope = ULTIMA_SALIDA_FINDE.get(dia)
    if tope is None:
        return list(DE_TIGRE)
    return [h for h in DE_TIGRE if _minutos(h) <= _minutos(tope)]


def texto_museo(html=False):
    """El mensaje completo. Con html=True usa <b> para Telegram (parse_mode
    HTML); sin el, texto plano para la web."""
    def b(t):
        return "<b>%s</b>" % t if html else t

    return (
        "%s\n\n"
        "%s\n"
        "salidas desde la Estación Fluvial · unos %d minutos de viaje\n"
        "%s\n"
        "Sábados última lancha a las %s el sábado y domingos última a las %s.\n\n"
        "%s\n"
        "horarios en que la lancha pasa por el muelle del Museo, iguales todos "
        "los días\n"
        "%s"
        % (b("Interisleña — Museo Sarmiento ⛵"),
           b("🚤 De Tigre al Museo"), VIAJE_MINUTOS, _en_filas(DE_TIGRE),
           ULTIMA_SALIDA_FINDE["sabado"], ULTIMA_SALIDA_FINDE["domingo"],
           b("🏛️ Del Museo a Tigre"), _en_filas(A_TIGRE))
    )
