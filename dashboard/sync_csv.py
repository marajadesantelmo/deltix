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

PA_USERNAME    = os.environ.get("PA_USERNAME", "facundol")
PA_API_TOKEN   = os.environ.get("PA_API_TOKEN", "")
ROOT           = Path(__file__).parent.parent
TIMESTAMP_FILE = Path(__file__).parent / ".last_sync"

FILES = [
    ("web_interactions.csv",  ROOT / "web_interactions.csv"),
    ("tg_interactions.csv",   ROOT / "tg_interactions.csv"),
]

# ── Descarga ──────────────────────────────────────────────────────────────────

def download_file(remote_name: str, local_path: Path, headers: dict) -> bool:
    remote_path = f"/home/{PA_USERNAME}/deltix/{remote_name}"
    url = f"https://www.pythonanywhere.com/api/v0/user/{PA_USERNAME}/files/path{remote_path}"
    print(f"  Descargando {remote_name}...")
    try:
        resp = requests.get(url, headers=headers, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"  ERROR de red: {e}")
        return False

    if resp.status_code == 200:
        local_path.write_bytes(resp.content)
        lines = resp.content.count(b"\n")
        print(f"  OK — {lines} filas → {local_path.name}")
        return True
    elif resp.status_code == 404:
        print(f"  AVISO: {remote_name} no existe aún en el servidor (404).")
        return True  # no es un error fatal
    elif resp.status_code == 401:
        print(f"  ERROR 401: Token inválido.")
        return False
    else:
        print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
        return False


def download_all() -> bool:
    if not PA_API_TOKEN:
        print("ERROR: PA_API_TOKEN no está configurado.")
        print("  Creá el archivo dashboard/.env con tu token de PythonAnywhere.")
        print("  Instrucciones: https://www.pythonanywhere.com/account/#api_token")
        return False

    headers = {"Authorization": f"Token {PA_API_TOKEN}"}
    print(f"Sincronizando desde PythonAnywhere ({PA_USERNAME})...")

    results = [download_file(name, path, headers) for name, path in FILES]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    TIMESTAMP_FILE.write_text(now, encoding="utf-8")
    print(f"  Timestamp: {now}")
    return all(results)


if __name__ == "__main__":
    success = download_all()
    sys.exit(0 if success else 1)
