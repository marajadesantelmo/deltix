"""Blueprint Flask de Tincho. Se monta en www.deltix.com.ar/<TINCHO_PREFIX> (por defecto /tincho)
sin tocar el resto de Deltix:

    from tincho.blueprint import tincho_bp
    app.register_blueprint(tincho_bp, url_prefix=tincho.config.PREFIX)
"""
import os
import secrets
from urllib.parse import urlparse

from flask import Blueprint, jsonify, make_response, render_template, request

from . import config, flows, store

BASE = os.path.dirname(os.path.abspath(__file__))
tincho_bp = Blueprint("tincho", __name__, template_folder=os.path.join(BASE, "templates"),
                      static_folder=os.path.join(BASE, "static"), static_url_path="/static")

COOKIE = "tincho_sid"


@tincho_bp.after_request
def _cabeceras(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; script-src 'self'; connect-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
    if request.endpoint != "tincho.static":
        resp.headers["Cache-Control"] = "no-store"
    return resp


def _sid():
    sid = request.cookies.get(COOKIE, "")
    return sid if 20 <= len(sid) <= 64 and sid.replace("-", "").replace("_", "").isalnum() else None


def _set_cookie(resp, sid):
    resp.set_cookie(COOKIE, sid, max_age=config.SESSION_IDLE_SECONDS * 4, httponly=True, samesite="Lax",
                    secure=request.is_secure or request.headers.get("X-Forwarded-Proto") == "https",
                    path=(config.PREFIX or "/") )
    return resp


@tincho_bp.route("/")
def index():
    return make_response(render_template("tincho.html", prefix=config.PREFIX.rstrip("/")))


@tincho_bp.route("/health")
def health():
    from . import siu
    return jsonify({"ok": True, "siu": siu.habilitado()})


@tincho_bp.route("/chat", methods=["POST"])
def chat():
    # Anti-CSRF: solo JSON (dispara preflight CORS) y, si hay Origin, debe ser el mismo host.
    if not request.is_json:
        return jsonify({"error": "formato"}), 415
    origin = request.headers.get("Origin")
    if origin and urlparse(origin).netloc != request.host:
        return jsonify({"error": "origen"}), 403
    data = request.get_json(silent=True) or {}
    texto = data.get("message") if isinstance(data.get("message"), str) else ""
    option_id = data.get("option") if isinstance(data.get("option"), str) else None
    nuevo = False
    sid = _sid()
    if not sid:
        sid, nuevo = secrets.token_urlsafe(24), True
    ip = request.remote_addr or "?"
    if not store.hit(f"req:{ip}", 60, 60):  # tope general por IP
        return jsonify({"reply": "Demasiados mensajes seguidos. Esperá un momento. 🌿", "options": []}), 429
    r = flows.procesar(sid, ip, texto, option_id)
    resp = jsonify({"reply": r["reply"], "options": r.get("options", [])})
    return _set_cookie(resp, sid) if nuevo else resp
