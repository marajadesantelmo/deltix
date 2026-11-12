"""Arma tincho/data/kb/chunks.json a partir de:
  - data/kb/paginas.json            (crawler de undelta.edu.ar)
  - data/institucional/*.json       (carreras, ingreso, recursos, links: datos curados por el equipo)

Uso: python tincho/scripts/build_kb.py
Las fuentes "curadas" llevan más peso que el texto crudo de la web: así prevalecen las
correcciones del equipo (horario 9:30, inscripción abierta, etc.) sobre páginas desactualizadas.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from tincho.carreras_util import duracion_legible  # noqa: E402

DATA = os.path.join(HERE, "..", "data")
MAX_CHARS = 900

# Páginas que NO se indexan, con el motivo. Revisar al re-crawlear.
EXCLUIR = {
    "https://undelta.edu.ar/inscripciones/": "dice que la inscripción abre el 1/10 y todavía no abrió; está desactualizada (ver correcciones del 8-oct)",
    "https://undelta.edu.ar/carreras/": "se usa el JSON estructurado de carreras (más limpio)",
    "https://undelta.edu.ar/formulario-transparencia/": "solo formulario",
    "https://carpinchia.undelta.edu.ar/": "sitio de evento (hackathon), no es información de la universidad",
}
# Frases que delatan texto viejo dentro de páginas que sí se indexan.
OBSOLETO = re.compile(r"abren el 1 de octubre|todav[ií]a no (abri[óo]|pod[eé]s anotarte)|9:00 a 19:00", re.I)


def leer(nombre):
    with open(os.path.join(DATA, nombre), encoding="utf-8") as f:
        return json.load(f)


def partir(texto, max_chars=MAX_CHARS):
    """Corta por encabezados '## ' y luego por párrafos hasta max_chars."""
    secciones = re.split(r"\n(?=## )", texto)
    for sec in secciones:
        lineas, acc = sec.split("\n"), ""
        encabezado = lineas[0] if lineas and lineas[0].startswith("## ") else ""
        for l in lineas:
            if len(acc) + len(l) > max_chars and acc.strip():
                yield acc.strip()
                acc = (encabezado + "\n") if encabezado and l != encabezado else ""
            acc += l + "\n"
        if acc.strip():
            yield acc.strip()


def main():
    chunks = []

    def add(fuente, titulo, texto, url, peso=1.0):
        chunks.append({"id": len(chunks), "fuente": fuente, "titulo": titulo, "texto": texto.strip(),
                       "url": url, "peso": peso})

    # 1) Web pública
    web = leer("kb/paginas.json")
    for p in web["paginas"]:
        if p["url"] in EXCLUIR:
            continue
        for trozo in partir(p["texto"]):
            if OBSOLETO.search(trozo) or len(trozo) < 60:
                continue
            add("web", p["titulo"], trozo, p["url"])

    # 2) Carreras (estructurado)
    car = leer("institucional/carreras-undelta.json")
    for area in car["areas"]:
        add("carreras", f"Instituto de {area['nombre']}",
            f"El Instituto de {area['nombre']} de la UNDelta ofrece estas carreras: "
            + "; ".join(c["nombre"] for c in area["carreras"]) + ".",
            "https://undelta.edu.ar/carreras/", 1.3)
        for c in area["carreras"]:
            dur = duracion_legible(c.get("duracion"))
            base = (f"{c['nombre']}. Instituto: {area['nombre']}. Título que otorga: {c.get('tituloOtorgado')}. "
                    f"Duración: {dur}. Carga horaria: {c.get('cargaHoraria')}. Modalidad: {c.get('modalidad')}. "
                    f"Gratuita y presencial. Contacto del instituto: {c.get('contacto')}.")
            add("carreras", c["nombre"], base, c.get("url") or "https://undelta.edu.ar/carreras/", 1.5)
            if c.get("descripcion"):
                add("carreras", f"Sobre {c['nombre']}", c["descripcion"], c.get("url"), 1.3)
            if c.get("perfil"):
                add("carreras", f"Perfil del graduado de {c['nombre']}",
                    "El graduado/a de esta carrera podrá:\n- " + "\n- ".join(c["perfil"]), c.get("url"), 1.2)

    # 3) Ingreso / CPU / documentación (curado)
    ing = leer("institucional/ingreso-undelta.json")
    s = ing["sede"]
    url_ing = "https://undelta.edu.ar/servicios-academicos/"
    add("ingreso", "Secretaría Académica: dónde y cuándo",
        f"Dirección de la sede y ubicación: {s['lugar']}, {s['direccion']}. Horario de atención: {s['horario']}. "
        f"Contacto de estudiantes: {ing['contacto']['email']}, WhatsApp {ing['contacto']['telefono']}.", url_ing, 2.0)
    add("ingreso", "Documentación para inscribirse",
        "Documentación que hay que acercar a la sede de San Fernando (Secretaría Académica): "
        + " ".join(ing["documentacion"]) + f" {ing['secundarioEnCurso']} {ing['secundarioExtranjero']} {ing['sinRecursosTecnologicos']}",
        url_ing, 2.0)
    add("ingreso", "Cómo inscribirse paso a paso",
        f"{ing['inscripcion']['texto']} {ing['gratuidad']} No tienen costo, arancel ni cuota. Pasos: "
        + " ".join(f"{i}. {p['titulo']}: {p['texto']}" for i, p in enumerate(ing["pasos"], 1))
        + f" {ing['yaEstudiante']} Preinscripción: https://guarani.undelta.edu.ar/guarani_preinscripcion/?__o=e",
        "https://undelta.edu.ar/inscripciones/", 2.0)
    cpu = ing["cpu"]
    add("ingreso", "Curso de Preparación Universitaria (CPU)",
        f"{cpu['nombre']}: {cpu['descripcion']} Ejes: " + "; ".join(cpu["ejes"]) + f". {cpu['modalidad']} Turnos: {cpu['turnos']} "
        f"Inicio del CPU: {ing['fechas']['inicioCPU']}. Inicio de clases: {ing['fechas']['inicioClases']}.", url_ing, 2.0)
    add("ingreso", "Quiénes están exentos del CPU (exenciones)",
        "Pueden quedar eximidos del CPU: " + " ".join(cpu["exenciones"]), url_ing, 2.0)

    # 3b) Calendario académico (estructurado: cada fila "fecha: evento" va junta)
    from tincho import calendario
    for titulo, texto in calendario.chunks_para_kb():
        add("calendario", titulo, texto, calendario.URL_PAGINA, 1.8)

    # 4) Recursos y links
    for r in leer("institucional/recursos-undelta.json")["recursos"]:
        add("recursos", r["nombre"], r["texto"].replace("*", ""), None, 1.4)
    lk = leer("institucional/links.json")
    add("links", "Links útiles de la UNDelta",
        f"Carreras: {lk['carreras']}. Preinscripción en SIU Guaraní: {lk['preinscripcionSiu']}. "
        f"Autogestión de estudiantes (SIU Guaraní): {lk['autogestionSiu']}. Campus virtual: {lk['campusVirtual']}. "
        f"Instructivo SIU: {lk['instructivoSiu']}. Calendario académico: {lk['calendario2026Pdf']}. Contacto: {lk['contacto']}.",
        None, 1.4)

    for c in chunks:  # ids estables
        c["id"] = chunks.index(c)
    out = os.path.join(DATA, "kb", "chunks.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"generado_de": web.get("obtenido"), "excluidas": EXCLUIR, "chunks": chunks}, f,
                  ensure_ascii=False, indent=1)
    print(f"{len(chunks)} chunks -> {out}")


if __name__ == "__main__":
    main()
