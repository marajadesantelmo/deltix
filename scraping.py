"""
scraping.py — Actualiza imágenes y datos de mareas, WindGurú e Hidrografía.

Cada sección es independiente: si una falla, las demás siguen ejecutándose.
Pensado para correr como tarea programada en PythonAnywhere.
"""

import urllib.request
import time
import traceback
from datetime import datetime

LOG_PATH = "/home/facundol/deltix/scraping.log"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── 1. Mareas INA (descarga directa, sin Selenium) ───────────────────────────

try:
    log("Descargando imagen de mareas INA...")
    req = urllib.request.Request(
        "https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open("/home/facundol/deltix/marea.png", "wb") as f:
        f.write(data)
    log(f"Mareas INA OK — {len(data):,} bytes guardados.")
except Exception as e:
    log(f"ERROR mareas INA: {e}\n{traceback.format_exc()}")

# ── 2. WindGurú (Selenium) ────────────────────────────────────────────────────

try:
    log("Iniciando Selenium para WindGurú...")
    from selenium import webdriver

    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.windguru.cz/632702")
    time.sleep(20)
    driver.save_screenshot("/home/facundol/deltix/windguru.png")
    log("WindGurú OK.")
except Exception as e:
    log(f"ERROR WindGurú: {e}\n{traceback.format_exc()}")
    driver = None

# ── 3. Hidrografía Naval (Selenium, reutiliza driver si sigue abierto) ────────

try:
    if driver is None:
        log("Selenium no disponible, saltando Hidrografía.")
        raise RuntimeError("driver no inicializado")

    from bs4 import BeautifulSoup

    log("Scrapeando Hidrografía Naval...")
    driver.get("https://www.hidro.gov.ar/oceanografia/pronostico.asp")
    time.sleep(10)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    raw_table_data = []
    if table:
        for row in table.find_all("tr"):
            cols = [ele.text.strip() for ele in row.find_all("td")]
            raw_table_data.append(cols)

    processed_data = []
    san_fernando_data = []
    current_port = None
    is_san_fernando = False

    for row in raw_table_data:
        if not row:
            continue
        if row[0]:
            current_port = row[0]
            is_san_fernando = "SAN FERNANDO" in current_port.upper()
        if len(row) >= 4 and is_san_fernando:
            processed_data.append([current_port or ""] + row[1:])
            san_fernando_data.append(row[1:])

    table_text = ""
    if processed_data:
        table_text += f"{processed_data[0][0]}\n"
        table_text += "Tipo\tHora\tAltura\tFecha\n"
        for row in san_fernando_data:
            if len(row) >= 4:
                table_text += f"{row[0]}\t{row[1]}\t{row[2]}\t{row[3]}\n"

    with open("/home/facundol/deltix/table_data.txt", "w", encoding="utf-8") as f:
        f.write(table_text)

    log(f"Hidrografía OK — {len(san_fernando_data)} filas de San Fernando.")

except Exception as e:
    log(f"ERROR Hidrografía: {e}\n{traceback.format_exc()}")

finally:
    try:
        if driver:
            driver.quit()
    except Exception:
        pass

log("scraping.py finalizado.")
