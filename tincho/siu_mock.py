"""SIU simulado SOLO para desarrollo y tests (TINCHO_SIU_MOCK=1). Datos ficticios."""
import re

PERSONAS = {
    "30123456": {"persona": 101, "email": "ana.demo@example.com"},
    "20999888": {"persona": 102, "email": None},
}
DOCENTES = {"20999888": {"docente": 501}}


def get(path, params):
    if path == "/personas":
        p = PERSONAS.get(params.get("numero_documento"))
        return [{"persona": p["persona"], "email": p["email"], "telefono": "x"}] if p else []
    if path == "/docentes":
        dni = str(params.get("nro_documento", "")).split(";")[-1]
        d = DOCENTES.get(dni)
        return [{"docente": d["docente"]}] if d else []
    m = re.match(r"^/personas/(\d+)/(\w[\w-]*)$", path)
    if m:
        pid, rec = int(m.group(1)), m.group(2)
        if pid == 101 and rec == "cursadas":
            return [{"actividad_nombre": "Introducción a la Ciencia de Datos", "comision_nombre": "A",
                     "propuesta_nombre_abreviado": "Tec. Ciencia de Datos",
                     "fecha_inicio_dictado": "2027-03-08", "fecha_fin_dictado": "2027-07-04"}]
        if pid == 101 and rec == "inscripciones-examen":
            return [{"actividad_nombre": "Matemática I", "fecha": "2027-07-14T09:00:00", "turno_nombre": "Julio", "llamado": "1"}]
        if pid == 101 and rec == "resumen-academico":
            return [{"propuesta_nombre": "Tecnicatura en Ciencia de Datos", "promedio_con_aplazos": 7.4,
                     "promedio_sin_aplazos": 7.8, "cantidad_aprobadas": 5, "cantidad_actividades_plan": 22}]
        return []
    m = re.match(r"^/docentes/(\d+)/comisiones$", path)
    if m and int(m.group(1)) == 501:
        return [{"actividad_nombre": "Estadística", "comision_nombre": "B"}]
    return []
