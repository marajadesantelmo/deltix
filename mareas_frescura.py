# -*- coding: utf-8 -*-
"""
Frescura de los datos de mareas.

El scraper corre en el server y refresca table_data.txt y marea.png. Cuando se
cae, los archivos quedan con el ultimo dato bueno y el bot los sigue sirviendo
como si fueran de hoy. Ya paso con el INA: quedo el rastro en la linea comentada
de deltix_funciones.py que avisaba a mano que no habia pronostico, un parche
manual que despues se comento y nadie volvio a activar.

Esto detecta el caso para poder avisar en vez de afirmar un horario vencido.
La gente usa el dato para cruzar el rio.

Vive en un modulo propio, como interislena_museo, porque lo usan deltix_funciones
(Telegram) y web_app (Flask), que no se importan entre si.
"""

import os
from datetime import datetime

if os.path.exists('/home/facundol/deltix/'):
    BASE_PATH = '/home/facundol/deltix/'
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# La tabla trae el pronostico del dia; un dia de margen por husos y hora de corrida.
TABLA_DIAS_TOLERANCIA = 1
# La imagen del INA se baja una vez por dia.
PNG_DIAS_TOLERANCIA = 2

TELEFONO_HIDROGRAFIA = "4749-0900"


def _leer_tabla():
    try:
        with open(os.path.join(BASE_PATH, "table_data.txt"), 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def fecha_mas_nueva_tabla():
    """Fecha mas nueva de table_data.txt (4a columna, dd/mm/aaaa), o None."""
    fechas = []
    for linea in _leer_tabla().splitlines()[2:]:
        partes = linea.strip().split('\t')
        if len(partes) >= 4:
            try:
                fechas.append(datetime.strptime(partes[3].strip(), "%d/%m/%Y").date())
            except ValueError:
                continue    # las filas sin dato traen '---'
    return max(fechas) if fechas else None


def dias_de_atraso_tabla():
    """Dias de atraso de la tabla respecto de hoy. 0 = al dia, None = sin fecha usable."""
    fecha = fecha_mas_nueva_tabla()
    if fecha is None:
        return None
    return max(0, (datetime.now().date() - fecha).days)


def dias_de_atraso_png():
    """Dias desde la ultima descarga de marea.png, o None si no esta el archivo."""
    try:
        mtime = os.path.getmtime(os.path.join(BASE_PATH, "marea.png"))
    except OSError:
        return None
    return max(0, (datetime.now() - datetime.fromtimestamp(mtime)).days)


def tabla_vencida():
    return (dias_de_atraso_tabla() or 0) > TABLA_DIAS_TOLERANCIA


def aviso_tabla_vieja():
    """Aviso para el usuario si la tabla esta vencida, o '' si esta al dia."""
    if not tabla_vencida():
        return ""
    fecha = fecha_mas_nueva_tabla()
    return ("⚠️ Ojo: el último dato que tengo es del %s. Puede estar vencido — "
            "confirmá con Hidrografía Naval antes de salir."
            % fecha.strftime("%d/%m/%Y"))


def aviso_png_viejo():
    """Aviso para el usuario si marea.png quedo viejo, o '' si esta al dia."""
    atraso = dias_de_atraso_png()
    if atraso is None or atraso <= PNG_DIAS_TOLERANCIA:
        return ""
    return ("este gráfico se actualizó hace %d días — el INA puede estar sin "
            "publicar. Confirmá antes de salir." % atraso)


def instruccion_para_llm():
    """Instruccion extra para el LLM si la tabla esta vencida, o '' si no."""
    atraso = dias_de_atraso_tabla()
    if atraso is None or atraso <= TABLA_DIAS_TOLERANCIA:
        return ""
    return ("ATENCION: esa tabla tiene %d dias de atraso, no es de hoy. No afirmes "
            "esos horarios como si fueran de hoy: decile al usuario que el dato esta "
            "desactualizado y que confirme con Hidrografia Naval al %s."
            % (atraso, TELEFONO_HIDROGRAFIA))
