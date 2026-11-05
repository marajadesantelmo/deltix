# Tincho — el bot web de la UNDelta

Subproyecto de Deltix. Chat público en `www.deltix.com.ar/tincho` (prefijo configurable con `TINCHO_PREFIX`)
que integra las funciones del bot de WhatsApp de la UNDelta (`undelta_bot`) y suma un RAG sobre `undelta.edu.ar`.

## Qué hace

| Función | Cómo |
|---|---|
| **Menús predefinidos** | 🎓 Carreras (Instituto → carrera → sobre / perfil / cómo inscribirme / contacto, con "⬅️ Volver a carreras de este Instituto"), 📝 Inscripciones (pasos, documentación, CPU, sede y horarios, calendario), 🆔 Consultas SIU, 📚 Guía Estudiantes, ☎️ Contacto |
| **Palabras clave** | Las mismas del routing de WhatsApp: `menú` `inicio` `desvincular` `baja` `alta` (sistema) · `chau` `chao` `adiós` `salir` `finalizar` · `carreras` `oferta` `planes` `alumno` `docente` `ayuda` · saludos, `iniciar`, `empezar`. Más atajos: `siu`, `cpu`, `documentación`, `inscripciones`, `contacto` |
| **RAG** | Texto libre → búsqueda BM25 sobre 625 fragmentos (web pública + datos curados) → respuesta redactada por el LLM *solo* con esos fragmentos, o extracto con enlace si no hay LLM |
| **SIU Guaraní** | Alumno: mis materias, mis mesas de examen, resumen académico. Docente: mis comisiones. Solo lectura, previa verificación por código al correo registrado en el SIU |

## Estructura

```
tincho/
  blueprint.py      rutas Flask (/, /chat, /health) + cabeceras de seguridad
  flows.py          motor: menús, palabras clave, verificación, consultas SIU
  kb.py             recuperación BM25 (Python puro, sin embeddings)
  llm.py            respuesta fundamentada + guardia anti-jailbreak
  siu.py            cliente SIU de solo lectura con lista blanca de rutas
  siu_mock.py       SIU simulado para desarrollo/tests
  mailer.py         SMTP para los códigos
  store.py          SQLite: sesiones, OTP (hash), límites, auditoría sin datos personales
  data/institucional/  carreras, ingreso, links, recursos (curados por el equipo, copiados de undelta_bot)
  data/kb/             paginas.json (crawler) y chunks.json (índice)
  scripts/crawl_undelta.py, build_kb.py
  tests/test_tincho.py
```

## Puesta en marcha

`web_app.py` ya registra el blueprint (si falla su carga, Deltix sigue andando). Variables de entorno
(o en `tokens.py`, que está en `.gitignore`):

| Variable | Para qué | Obligatoria |
|---|---|---|
| `OPENROUTER_API_KEY` | LLM del RAG (sin ella: respuestas extractivas) | no |
| `SIU_API_URL`, `SIU_API_USER`, `SIU_API_PASSWORD` | API REST del SIU (por defecto el ambiente **test**) | para consultas SIU |
| `TINCHO_SMTP_USER`, `TINCHO_SMTP_PASSWORD` (`_HOST`, `_PORT`, `_FROM`) | Envío del código OTP | para consultas SIU |
| `TINCHO_SECRET` | Clave para firmar hashes | **sí en producción** |
| `TINCHO_PREFIX` | Ruta pública (default `/tincho`) | no |
| `TINCHO_CLAVE_INICIO` | Clave para empezar a conversar. **Por defecto `testing-tincho-undelta`**, igual que en WhatsApp; `chau` o 30 min de inactividad la vuelven a pedir. `sin-clave` deja el bot público (y apaga el modo "no identificar") | no |
| `TINCHO_NO_IDENTIFICAR` | `1` (default) habilita el modo "no identificar" (consulta por DNI sin código), **solo si hay `TINCHO_CLAVE_INICIO`** | no |
| `TINCHO_SIU_MOCK=1` | SIU simulado, **solo desarrollo** (el código OTP se imprime en la consola del servidor) | no |

Sin credenciales SIU, las consultas personales quedan **deshabilitadas** (falla cerrado) y el resto funciona. Sin SMTP solo funciona el modo "no identificar" (no hay códigos por correo).

**Modo "no identificar"** (`no identificar` o `demo`, desde el paso de DNI de Consultas SIU): consulta por DNI sin verificar, como en el bot de pruebas de WhatsApp. Acordado con las autoridades de la UNDelta; rige únicamente mientras el bot esté protegido por la clave de inicio. Cada ingreso queda auditado (`sinid_ingreso`).

## Mantenimiento de la base de conocimiento

```
python tincho/scripts/crawl_undelta.py   # re-lee undelta.edu.ar → data/kb/paginas.json
python tincho/scripts/build_kb.py        # regenera data/kb/chunks.json
```
`build_kb.py` mantiene una lista `EXCLUIR` de páginas desactualizadas (hoy `/inscripciones/`, que todavía dice
que la inscripción abre el 1/10) y descarta frases obsoletas; los datos curados (`data/institucional/`) pesan más
que el texto crudo de la web, así prevalecen las correcciones del 8-oct (9:30 hs, inscripción abierta, original y copia).
Cuando la web se corrija, revisar `EXCLUIR`.

## Tests

```
python -m unittest discover -s tincho/tests -v
```

## Pendiente / a validar

- Formatos del SIU de test verificados el 4-nov con respuestas reales: `personas`, `docentes`, `cursadas`, `resumen-academico`.
  **Sin verificar** (las personas de prueba no tienen datos): `inscripciones-examen` y `docentes/{id}/comisiones`.
- El SIU está detrás de Cloudflare: bloquea el User-Agent por defecto de Python (error 1010); `siu.py` envía el suyo.
- Con varios *workers* de PythonAnywhere el estado compartido es SQLite (`tincho/var/`); si se migra a la VM de
  BAEHOST, mover a Postgres/Redis.
- Deltix tiene un service worker en `/`; se lo excluyó de `/deltix/*` (`static/service-worker.js`).
