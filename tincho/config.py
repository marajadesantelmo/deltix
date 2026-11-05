"""Configuración de Tincho. Todo secreto viene de variables de entorno (o de tokens.py, como Deltix);
nunca se escribe en el repositorio."""
import os

try:  # mismo mecanismo que Deltix en PythonAnywhere
    import tokens as _t
except ImportError:  # pragma: no cover
    _t = None


def _get(name, default=""):
    return os.getenv(name) or getattr(_t, name, None) or default


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
VAR_DIR = os.getenv("TINCHO_VAR_DIR") or os.path.join(BASE_DIR, "var")

# Ruta pública donde se monta el bot dentro de www.deltix.com.ar
PREFIX = _get("TINCHO_PREFIX", "/tincho")

# Clave de inicio, igual que en el bot de WhatsApp: sin escribirla no se puede conversar.
# Para cambiarla definí TINCHO_CLAVE_INICIO; para dejar el bot público sin clave, "sin-clave".
CLAVE_INICIO = _get("TINCHO_CLAVE_INICIO", "testing-tincho-undelta")
if CLAVE_INICIO.strip().lower() in ("sin-clave", "off", "none"):
    CLAVE_INICIO = ""

# Modo "no identificar": consulta el SIU por DNI sin código de verificación. Acordado con las
# autoridades de la UNDelta mientras el bot esté protegido por la clave de inicio. Si no hay
# CLAVE_INICIO, el modo queda desactivado aunque esta variable valga 1 (ver flows.no_identificar_activo).
NO_IDENTIFICAR = _get("TINCHO_NO_IDENTIFICAR", "1") == "1"

# ── LLM (opcional): sin clave, Tincho responde solo con extractos de la base ──
OPENROUTER_KEY = _get("OPENROUTER_API_KEY") or _get("openrouter_key")
LLM_MODEL = _get("TINCHO_LLM_MODEL", "deepseek/deepseek-chat")

# ── SIU Guaraní (solo lectura) ──
SIU_URL = _get("SIU_API_URL", "https://guarani.undelta.edu.ar/guarani_gestion_test/rest/v2")
SIU_USER = _get("SIU_API_USER")
SIU_PASSWORD = _get("SIU_API_PASSWORD")
SIU_TIMEOUT = int(_get("SIU_API_TIMEOUT", "20"))
# "1" = usa un SIU simulado (solo desarrollo). Nunca activar en producción.
SIU_MOCK = _get("TINCHO_SIU_MOCK", "") == "1"

# ── Correo saliente para los códigos de verificación (SMTP) ──
SMTP_HOST = _get("TINCHO_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_get("TINCHO_SMTP_PORT", "465"))
SMTP_USER = _get("TINCHO_SMTP_USER")
SMTP_PASSWORD = _get("TINCHO_SMTP_PASSWORD")
SMTP_FROM = _get("TINCHO_SMTP_FROM", SMTP_USER)

# ── Seguridad ──
SECRET = _get("TINCHO_SECRET") or _get("telegram_token", "") or "cambiar-en-produccion"
SESSION_IDLE_SECONDS = 30 * 60        # sesión conversacional
IDENTITY_TTL_SECONDS = 30 * 60        # identidad verificada (se renueva con uso, tope duro abajo)
IDENTITY_MAX_SECONDS = 2 * 60 * 60
OTP_TTL_SECONDS = 10 * 60
OTP_MAX_ATTEMPTS = 5
OTP_MAX_SENDS_PER_DOC_HOUR = 3
OTP_MAX_SENDS_PER_IP_HOUR = 10
MAX_MESSAGE_CHARS = 500
LLM_PER_MIN, LLM_PER_HOUR, LLM_PER_DAY = 4, 20, 40

CONTACTO_ESTUDIANTES = "estudiantes@undelta.edu.ar"
