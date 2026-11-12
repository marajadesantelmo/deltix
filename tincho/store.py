"""Almacén SQLite (stdlib) compartido entre workers: estado de conversación, códigos OTP,
límites de uso y auditoría. Los datos personales del SIU NO se guardan acá: solo ids internos
y, para auditar, un hash HMAC del documento."""
import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time

from . import config

_lock = threading.Lock()
_conn = None


def _db():
    global _conn
    if _conn is None:
        os.makedirs(config.VAR_DIR, exist_ok=True)
        _conn = sqlite3.connect(os.path.join(config.VAR_DIR, "tincho.db"),
                                check_same_thread=False, timeout=15, isolation_level=None)
        _conn.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS sesiones(sid TEXT PRIMARY KEY, estado TEXT, ts REAL);
            CREATE TABLE IF NOT EXISTS otp(sid TEXT PRIMARY KEY, doc_hash TEXT, code_hash TEXT,
                                            exp REAL, intentos INTEGER, contexto TEXT);
            CREATE TABLE IF NOT EXISTS hits(clave TEXT, ts REAL);
            CREATE INDEX IF NOT EXISTS ix_hits ON hits(clave, ts);
            CREATE TABLE IF NOT EXISTS auditoria(ts REAL, sid TEXT, evento TEXT, detalle TEXT);
        """)
    return _conn


def reset_for_tests(path):
    """Apunta el almacén a otro directorio (tests)."""
    global _conn
    if _conn is not None:
        _conn.close()
    _conn = None
    config.VAR_DIR = path


def hmac_hex(valor: str) -> str:
    return hmac.new(config.SECRET.encode(), valor.encode(), hashlib.sha256).hexdigest()


# ── sesiones ──
def cargar_estado(sid):
    with _lock:
        row = _db().execute("SELECT estado, ts FROM sesiones WHERE sid=?", (sid,)).fetchone()
    if not row or time.time() - row[1] > config.SESSION_IDLE_SECONDS:
        return {}
    return json.loads(row[0])


def guardar_estado(sid, estado):
    with _lock:
        _db().execute("INSERT OR REPLACE INTO sesiones VALUES(?,?,?)",
                      (sid, json.dumps(estado, ensure_ascii=False), time.time()))
        # limpieza oportunista
        _db().execute("DELETE FROM sesiones WHERE ts<?", (time.time() - 86400,))
        _db().execute("DELETE FROM hits WHERE ts<?", (time.time() - 86400,))


def borrar_sesion(sid):
    with _lock:
        _db().execute("DELETE FROM sesiones WHERE sid=?", (sid,))
        _db().execute("DELETE FROM otp WHERE sid=?", (sid,))


# ── límites de uso ──
def hit(clave, max_n, ventana_s):
    """Registra un uso; devuelve False (sin registrar) si ya se alcanzó el máximo en la ventana."""
    now = time.time()
    with _lock:
        n = _db().execute("SELECT COUNT(*) FROM hits WHERE clave=? AND ts>?",
                          (clave, now - ventana_s)).fetchone()[0]
        if n >= max_n:
            return False
        _db().execute("INSERT INTO hits VALUES(?,?)", (clave, now))
    return True


def hit_all(reglas):
    """reglas: lista de (clave, máximo, ventana_s). Si TODAS permiten, registra un uso en cada una y devuelve
    (True, 0). Si alguna se pasó, no registra nada y devuelve (False, segundos hasta poder volver a intentar).
    Es atómico: un intento rechazado no gasta cupo de las otras reglas."""
    now = time.time()
    with _lock:
        espera = 0.0
        for clave, max_n, ventana in reglas:
            tss = [r[0] for r in _db().execute("SELECT ts FROM hits WHERE clave=? AND ts>? ORDER BY ts",
                                                (clave, now - ventana))]
            if len(tss) >= max_n:
                espera = max(espera, tss[len(tss) - max_n] + ventana - now)
        if espera > 0:
            return False, espera
        for clave, _, _ in reglas:
            _db().execute("INSERT INTO hits VALUES(?,?)", (clave, now))
    return True, 0


# ── OTP ──
def guardar_otp(sid, doc_hash, code, contexto):
    with _lock:
        _db().execute("INSERT OR REPLACE INTO otp VALUES(?,?,?,?,0,?)",
                      (sid, doc_hash, hmac_hex(f"{sid}:{code}"),
                       time.time() + config.OTP_TTL_SECONDS, json.dumps(contexto)))


def verificar_otp(sid, code):
    """Devuelve (estado, contexto). estado ∈ ok | invalido | vencido | agotado | inexistente."""
    with _lock:
        row = _db().execute("SELECT code_hash, exp, intentos, contexto FROM otp WHERE sid=?",
                            (sid,)).fetchone()
        if not row:
            return "inexistente", None
        code_hash, exp, intentos, ctx = row
        if time.time() > exp:
            _db().execute("DELETE FROM otp WHERE sid=?", (sid,))
            return "vencido", None
        if intentos >= config.OTP_MAX_ATTEMPTS:
            _db().execute("DELETE FROM otp WHERE sid=?", (sid,))
            return "agotado", None
        if hmac.compare_digest(code_hash, hmac_hex(f"{sid}:{code}")):
            _db().execute("DELETE FROM otp WHERE sid=?", (sid,))  # un solo uso
            return "ok", json.loads(ctx)
        _db().execute("UPDATE otp SET intentos=intentos+1 WHERE sid=?", (sid,))
        if intentos + 1 >= config.OTP_MAX_ATTEMPTS:
            _db().execute("DELETE FROM otp WHERE sid=?", (sid,))
            return "agotado", None
        return "invalido", None


# ── auditoría (sin datos personales) ──
def auditar(sid, evento, detalle=""):
    with _lock:
        _db().execute("INSERT INTO auditoria VALUES(?,?,?,?)",
                      (time.time(), hmac_hex("sesion:" + (sid or ""))[:10], evento, str(detalle)[:200]))
