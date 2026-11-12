"""Crawler de undelta.edu.ar para la base de conocimiento (RAG) de Tincho.

Uso:  python tincho/scripts/crawl_undelta.py
Salida: tincho/data/kb/paginas.json  (texto limpio por página + PDFs enlazados)

Solo lee páginas públicas, respeta robots.txt (sin /wp-admin/) y espera entre pedidos.
"""
import json
import os
import re
import time
from datetime import date
from urllib.parse import urljoin, urldefrag, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://undelta.edu.ar"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "kb", "paginas.json")
OUT_CAL = os.path.join(HERE, "..", "data", "institucional", "calendario.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; TinchoBot-indexador; +https://www.deltix.com.ar)"}
SKIP = ("/wp-admin", "/wp-content/uploads/", "/feed", "/wp-json", "/xmlrpc", "/sample-page", "/hello-world", "campusvirtual.", "/campus", "/login", "forgot_password", "dataprivacy", "/charlas/")


def sitemap_urls():
    urls = set()
    for s in ("page", "post", "category"):
        try:
            r = requests.get(f"{BASE}/{s}-sitemap1.xml", headers=UA, timeout=30)
            urls.update(re.findall(r"<loc>([^<]+)</loc>", r.text))
        except requests.RequestException:
            pass
    return urls


def _txt(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True))


def extraer_calendario(soup):
    """Lee la tabla del calendario académico FILA POR FILA (fecha en el <th scope=row>, evento en el <td>).
    Si se aplasta a texto suelto, las fechas y los eventos quedan sin par y el modelo los asocia mal."""
    tabla = soup.find("table", class_="tabla-cal")
    if not tabla:
        return None
    h2 = tabla.find_previous(["h2", "h3"])
    cap = tabla.find("caption")
    mes, filas = "", []
    for tr in tabla.find_all("tr"):
        celdas = tr.find_all(["th", "td"])
        if len(celdas) == 1 and celdas[0].get("colspan"):      # fila de mes
            mes = _txt(celdas[0])
        elif len(celdas) == 2 and celdas[0].get("scope") == "row":
            sello = tr.find(class_="sello-hito")
            evento = _txt(celdas[1])
            if sello:
                evento = evento.replace(_txt(sello), "").strip()
            filas.append({"mes": mes, "fecha": _txt(celdas[0]), "evento": evento, "hito": bool(sello)})
    return {"titulo": _txt(h2) if h2 else "Calendario académico",
            "aclaracion": _txt(cap) if cap else "", "filas": filas}


def aplanar_tablas(main):
    """Resto de las tablas del sitio: una línea por fila, con las celdas unidas ('a — b — c')."""
    for tabla in main.find_all("table"):
        div = BeautifulSoup("<div></div>", "html.parser").div
        for tr in tabla.find_all("tr"):
            celdas = [_txt(c) for c in tr.find_all(["th", "td"]) if _txt(c)]
            if celdas:
                p = BeautifulSoup("<p></p>", "html.parser").p
                p.string = " — ".join(celdas)
                div.append(p)
        tabla.replace_with(div)


def limpiar(soup):
    for t in soup(["script", "style", "noscript", "nav", "footer", "header", "form", "svg", "iframe"]):
        t.decompose()
    for t in soup.find_all("table", class_="tabla-cal"):   # el calendario va aparte, estructurado
        t.decompose()
    aplanar_tablas(soup)
    main = soup.find("main") or soup.find("article") or soup.body or soup
    # Un salto de línea por bloque, para poder cortar en chunks coherentes.
    for br in main.find_all("br"):
        br.replace_with("\n")
    lineas = []
    for el in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th", "a", "span", "div"]):
        if el.name in ("a", "span", "div") and el.find(["p", "li", "h1", "h2", "h3", "h4", "div"]):
            continue
        txt = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        if not txt:
            continue
        if el.name in ("h1", "h2", "h3", "h4"):
            txt = "## " + txt
        elif el.name == "li":
            txt = "- " + txt
        if not lineas or lineas[-1] != txt:
            lineas.append(txt)
    # Quita líneas contenidas en la anterior (anidados duplicados).
    out = []
    for l in lineas:
        if out and l in out[-1]:
            continue
        out.append(l)
    return "\n".join(out)


def main():
    cola = sorted(sitemap_urls() | {BASE + "/"})
    vistas, paginas, pdfs, calendario = set(), [], {}, None
    while cola:
        url = urldefrag(cola.pop(0))[0]
        if url in vistas or any(s in url for s in SKIP):
            continue
        vistas.add(url)
        try:
            r = requests.get(url, headers=UA, timeout=30)
        except requests.RequestException as e:
            print("ERROR", url, e)
            continue
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
            continue
        soup = BeautifulSoup(r.content, "html.parser")   # bytes: respeta el <meta charset> (evita "debatiÃ³")
        # Enlaces: internos nuevos a la cola, PDFs/externos relevantes al registro.
        for a in soup.find_all("a", href=True):
            h = urldefrag(urljoin(url, a["href"]))[0]
            if urlparse(h).netloc.endswith("undelta.edu.ar"):
                if h.lower().endswith(".pdf"):
                    pdfs[h] = re.sub(r"\s+", " ", a.get_text(" ", strip=True)) or pdfs.get(h, "")
                elif h not in vistas and not any(s in h for s in SKIP) and "?" not in h:
                    cola.append(h)
            elif re.search(r"(guarani|campusvirtual|forms\.gle|drive\.google)", h):
                pdfs.setdefault(h, re.sub(r"\s+", " ", a.get_text(" ", strip=True)))
        cal = extraer_calendario(soup)
        if cal and cal["filas"]:
            calendario = dict(cal, url=url)
        titulo = (soup.find("h1") or soup.title)
        titulo = re.sub(r"\s+", " ", titulo.get_text(" ", strip=True)) if titulo else url
        texto = limpiar(soup)
        if len(texto) > 150:
            paginas.append({"url": url, "titulo": titulo, "texto": texto})
        print(f"OK {len(texto):6d}  {url}")
        time.sleep(0.7)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"obtenido": date.today().isoformat(), "fuente": BASE,
                   "paginas": paginas,
                   "documentos_y_enlaces": [{"url": u, "texto": t} for u, t in sorted(pdfs.items())]},
                  f, ensure_ascii=False, indent=1)
    if calendario:
        calendario["obtenido"] = date.today().isoformat()
        with open(OUT_CAL, "w", encoding="utf-8") as f:
            json.dump(calendario, f, ensure_ascii=False, indent=1)
        print(f"calendario: {len(calendario['filas'])} filas -> {OUT_CAL}")
    else:
        print("AVISO: no se encontró la tabla del calendario; se conserva el calendario.json anterior")
    print(f"{len(paginas)} páginas, {len(pdfs)} enlaces/documentos -> {OUT}")


if __name__ == "__main__":
    main()
