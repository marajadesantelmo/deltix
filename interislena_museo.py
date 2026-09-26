# -*- coding: utf-8 -*-
"""
Horarios de Interisleña en el Museo Sarmiento.

El Museo Casa de Domingo Faustino Sarmiento es la parada mas pedida del Delta:
TODOS los recorridos de Interisleña pasan por ahi, asi que sirve de referencia
para cualquiera que vaya o vuelva de la isla sin importar por que arroyo entre.

Fuente: el cartel del muelle del Museo, fotografiado en
colectivas/interislena_deep/Interisleña Museo - Tigre.jpeg
El cartel dice "DIAS DE SEMANA": no trae fines de semana, y eso se avisa.

Validacion: los 16 horarios de la columna "DE TIGRE" existen los 16 en las
salidas de lunes a viernes que ya estaban cargadas en rag/interislena.txt,
repartidos entre varias rutas. O sea que la columna es la union de las rutas que
pasan por el Museo, y confirma que el cartel es de Interisleña.

Los tres horarios de lunes a viernes que tenemos y el cartel no lista (17:00,
18:00 y 18:30) son de las rutas Espera / Cruz Colorada y de los "solo viernes",
que aparentemente no pasan por el Museo.

Este dato vive en un modulo propio porque lo usan deltix_funciones (Telegram) y
web_app (Flask), que no se importan entre si. Duplicarlo en los dos garantiza
que tarde o temprano uno quede viejo.
"""

# Columna "DE TIGRE" del cartel: salidas desde la Estacion Fluvial de Tigre.
DE_TIGRE = ["7:00", "8:00", "8:30", "9:00", "10:00", "11:30", "12:45", "14:15",
            "15:00", "15:30", "16:15", "17:30", "18:10", "19:00", "20:00", "21:00"]

# Columna "A TIGRE" del cartel: horarios en que la lancha pasa por el muelle del
# Museo rumbo a Tigre. No son horarios de llegada a Tigre: cruzados con las
# llegadas de lunes a viernes de rag/interislena.txt, cada uno cae entre 30 y 50
# minutos antes del arribo siguiente a la Estacion Fluvial (promedio 41). La
# dispersion es real y no un error de transcripcion: por el Museo pasan lanchas
# de recorridos distintos, y lo que falta de viaje depende de cual sea.
A_TIGRE = ["5:50", "6:50", "7:30", "7:50", "9:45", "10:45", "11:45", "14:00",
           "15:30", "16:00", "17:30", "18:15", "19:30"]

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


def texto_museo(html=False):
    """El mensaje completo. Con html=True usa <b> para Telegram (parse_mode
    HTML); sin el, texto plano para la web."""
    def b(t):
        return "<b>%s</b>" % t if html else t

    return (
        "%s\n"
        "Días de semana (lunes a viernes)\n\n"
        "%s\n"
        "salidas desde la Estación Fluvial\n"
        "%s\n\n"
        "%s\n"
        "horarios en que la lancha pasa por el muelle del Museo\n"
        "%s\n\n"
        "Ojo: el cartel del muelle es solo de días de semana. "
        "Para sábados y domingos conviene llamar a Interisleña al %s."
        % (b("Interisleña — Museo Sarmiento ⛵"),
           b("🚤 De Tigre al Museo"), _en_filas(DE_TIGRE),
           b("🏛️ Del Museo a Tigre"), _en_filas(A_TIGRE),
           TELEFONO)
    )
