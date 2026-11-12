"""
sync_db.py — Descarga conversaciones.db (histórico de Tincho) desde PythonAnywhere.

Uso:
    python sync_db.py

Configuración (igual que dashboard/sync_csv.py de Deltix): crear tincho/dashboard/.env con
    PA_USERNAME=facundol
    PA_API_TOKEN=tu_token_aqui
(o definir las variables de entorno). Token: https://www.pythonanywhere.com/account/#api_token

La base descargada se valida con PRAGMA integrity_check antes de reemplazar la copia local,
así una descarga a medio escribir nunca pisa una copia buena. NO subir data/ ni .env al repositorio.
"""
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import requests

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
LOCAL_DB = Path(os.environ.get("TINCHO_DASH_DB") or DATA_DIR / "conversaciones.db")  # TINCHO_DASH_DB: solo para pruebas
TIMESTAMP_FILE = HERE / ".last_sync"

env_path = HERE / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip("'").strip('"'))


def _config():
    return os.environ.get("PA_USERNAME", "facundol"), os.environ.get("PA_API_TOKEN", "")


def remote_url(user):
    return (f"https://www.pythonanywhere.com/api/v0/user/{user}"
            f"/files/path/home/{user}/deltix/tincho/var/conversaciones.db")


def es_base_valida(path: Path) -> bool:
    try:
        con = sqlite3.connect(str(path))
        try:
            ok = con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            con.execute("SELECT COUNT(*) FROM mensajes").fetchone()
            return ok
        finally:
            con.close()
    except sqlite3.Error:
        return False


def download_all() -> bool:
    user, token = _config()
    if not token:
        print("ERROR: PA_API_TOKEN no está configurado. Creá tincho/dashboard/.env con tu token.")
        return False
    print(f"Descargando conversaciones.db desde PythonAnywhere ({user})...")
    try:
        resp = requests.get(remote_url(user), headers={"Authorization": f"Token {token}"}, timeout=60)
    except requests.exceptions.RequestException as e:
        print(f"  ERROR de red: {e}")
        return False
    if resp.status_code == 404:
        print("  AVISO: todavía no existe conversaciones.db en el servidor (nadie conversó aún).")
        return True
    if resp.status_code == 401:
        print("  ERROR 401: token inválido.")
        return False
    if resp.status_code != 200:
        print(f"  ERROR {resp.status_code}: {resp.text[:200]}")
        return False

    DATA_DIR.mkdir(exist_ok=True)
    tmp = LOCAL_DB.with_suffix(".db.tmp")
    tmp.write_bytes(resp.content)
    if not es_base_valida(tmp):
        tmp.unlink(missing_ok=True)
        print("  ERROR: la base descargada no pasó la validación (¿se estaba escribiendo?). Reintentá.")
        return False
    os.replace(tmp, LOCAL_DB)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    TIMESTAMP_FILE.write_text(now, encoding="utf-8")
    print(f"  OK — {len(resp.content) // 1024} KB → {LOCAL_DB.name} ({now})")
    return True


if __name__ == "__main__":
    sys.exit(0 if download_all() else 1)
