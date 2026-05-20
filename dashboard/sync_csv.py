"""
sync_csv.py — Descarga web_interactions.csv desde PythonAnywhere.

Uso:
    python sync_csv.py

Configuración:
    Crear un archivo .env en la carpeta dashboard/ con:
        PA_USERNAME=facundol
        PA_API_TOKEN=tu_token_aqui

    O definir las variables de entorno manualmente.

Cómo obtener el API token:
    1. Ir a https://www.pythonanywhere.com/account/#api_token
    2. Crear un token si no tenés uno
    3. Copiarlo en .env
"""

import os
import sys
import requests
from pathlib import Path
from datetime import datetime

# ── Configuración ─────────────────────────────────────────────────────────────

# Cargar .env si existe
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            # Strip surrounding quotes (both ' and ") — common when copiando tokens
            val = val.strip().strip("'").strip('"')
            os.environ.setdefault(key.strip(), val)

PA_USERNAME  = os.environ.get("PA_USERNAME", "facundol")
PA_API_TOKEN = os.environ.get("PA_API_TOKEN", "")
REMOTE_PATH  = f"/home/{PA_USERNAME}/deltix/web_interactions.csv"
LOCAL_CSV    = Path(__file__).parent.parent / "web_interactions.csv"
TIMESTAMP_FILE = Path(__file__).parent / ".last_sync"

# ── Descarga ──────────────────────────────────────────────────────────────────

def download_csv() -> bool:
    if not PA_API_TOKEN:
        print("ERROR: PA_API_TOKEN no está configurado.")
        print("  Creá el archivo dashboard/.env con tu token de PythonAnywhere.")
        print("  Instrucciones: https://www.pythonanywhere.com/account/#api_token")
        return False

    url = f"https://www.pythonanywhere.com/api/v0/user/{PA_USERNAME}/files/path{REMOTE_PATH}"
    print(f"Descargando desde PythonAnywhere...")
    print(f"  URL: {url}")

    try:
        resp = requests.get(url, headers={"Authorization": f"Token {PA_API_TOKEN}"}, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"ERROR de red: {e}")
        return False

    if resp.status_code == 200:
        LOCAL_CSV.write_bytes(resp.content)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        TIMESTAMP_FILE.write_text(now, encoding="utf-8")
        lines = resp.content.count(b"\n")
        print(f"  OK — {lines} filas descargadas")
        print(f"  Guardado en: {LOCAL_CSV}")
        print(f"  Timestamp: {now}")
        return True
    elif resp.status_code == 401:
        print("ERROR 401: Token inválido. Verificá PA_API_TOKEN en .env")
    elif resp.status_code == 404:
        print(f"ERROR 404: Archivo no encontrado en {REMOTE_PATH}")
        print("  Verificá que el path sea correcto.")
    else:
        print(f"ERROR {resp.status_code}: {resp.text[:200]}")
    return False


if __name__ == "__main__":
    success = download_csv()
    sys.exit(0 if success else 1)
