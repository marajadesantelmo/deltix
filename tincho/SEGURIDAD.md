# Tincho — Nota de seguridad y privacidad (para validación con las autoridades)

## 1. Alcance
Asistente web público de la UNDelta: información institucional (carreras, ingreso, trámites) y, opcionalmente,
consultas personales al SIU Guaraní previa verificación de identidad.

## 2. Datos y su tratamiento

| Dato | Dónde vive | Qué se hace |
|---|---|---|
| Preguntas en texto libre | Se envían (junto con fragmentos públicos) al proveedor de LLM | Aviso en pantalla de no compartir datos personales. El LLM **nunca** recibe datos del SIU |
| Documento (DNI) | Solo en memoria durante la verificación | No se guarda; para límites y auditoría se usa un **hash HMAC** |
| Correo registrado en SIU | Solo en memoria durante el envío del código | No se muestra ni se guarda |
| Código de verificación | Hash HMAC en SQLite, 10 min, un solo uso | Nunca se devuelve al navegador |
| Datos académicos del SIU | Se leen en el momento y se muestran | No se almacenan; se formatean con plantillas fijas (sin LLM) |
| Auditoría | SQLite local (`tincho.db`) | Evento + HMAC corto de la sesión; **sin DNI, nombres ni correos** |
| **Histórico de conversaciones** | SQLite local (`conversaciones.db`) | Fecha, sesión anónima (HMAC), tipo, texto de la persona y respuesta del bot, para auditar la calidad de las respuestas. **No se guardan** los pasos de DNI/código, la clave de inicio ni las respuestas del SIU (se reemplazan por marcadores); en el texto libre se enmascaran números largos y correos. **Retención indefinida** por decisión del equipo (hay `convlog.purgar(dias)` para uso manual). La pantalla del bot avisa que las conversaciones se guardan |

## 3. Verificación de identidad
1. La persona informa su documento.
2. Se envía un código de 6 dígitos al **correo que figura en el SIU** (no a uno que elija quien consulta).
3. La respuesta es idéntica exista o no el documento (no permite averiguar quién es alumno).
4. Máx. 5 intentos por código; 3 envíos/hora por documento y 10/hora por IP.
5. Identidad vigente 30 min de inactividad (tope 2 h); `desvincular`, `chau` o "Cerrar sesión" la borran al instante.
6. **Modo "no identificar"** (`no identificar` / `demo`): igual que en el bot de pruebas de WhatsApp, permite consultar por DNI sin código. Fue acordado con las autoridades de la UNDelta y **solo está activo si el bot exige la clave de inicio** (`TINCHO_CLAVE_INICIO`); sin clave, queda apagado. Tiene tope de 20 intentos/hora por IP y cada ingreso se audita. Riesgo asumido: quien conozca la clave y un DNI ajeno puede ver los datos de esa persona; se apaga con `TINCHO_NO_IDENTIFICAR=0`.

## 4. Palabras clave
Se mantienen las del routing del bot institucional (ver README). Son órdenes de navegación y de seguridad:
`desvincular` y `chau` cierran sesión y borran la identidad; `menú`/`inicio` cancelan cualquier verificación en curso.
`baja`/`alta` se reconocen por compatibilidad (la versión web no envía avisos). `TINCHO_CLAVE_INICIO`
restringe el acceso al bot a quien conozca una clave (modo testing, como `testing-tincho-undelta`) y es condición del modo "no identificar".

## 5. Acceso al SIU
- Solo **GET** y solo a una **lista blanca** de rutas (`/personas`, `…/cursadas`, `…/inscripciones-examen`,
  `…/resumen-academico`, `/docentes`, `…/comisiones`, `…/mesas`); cualquier otra se rechaza (hay test).
- Mínimo privilegio: no se usa `datospersonales` (domicilio, teléfonos, fecha de nacimiento); el correo para el código sale de `/personas` o `/docentes`.
- Cada consulta se hace con el id de persona **de la sesión verificada**, nunca con uno enviado por el navegador.
- TLS siempre verificado. Credenciales solo en variables de entorno / `tokens.py` fuera del repositorio.
- Recomendado: un usuario de API de **solo lectura** dedicado a Tincho, y apuntar a producción únicamente tras la validación.

## 6. Contra abusos
Límite general por IP; límites de preguntas al LLM **por sesión** (5/min, 40/h, 120/día) y **por IP real** (40/min, 300/h, 1000/día, más altos porque un aula o el wifi de la universidad comparten IP), configurables por entorno; al bloquear, el bot dice cuántos minutos esperar. Detrás del proxy de PythonAnywhere se usa la cabecera `X-Real-IP` (si el sitio se expusiera sin ese proxy, la cabecera se podría falsificar: en ese caso `TINCHO_PROXY_HEADER=` la desactiva). Mensajes ≤ 500 caracteres,
guardia anti-prompt-injection (patrones + instrucciones del sistema que tratan fuentes y mensajes como datos),
respuesta "no tengo ese dato" ante preguntas sin respaldo en la base (umbral de relevancia).

## 7. Aplicación web
Cookie de sesión `HttpOnly`, `SameSite=Lax`, `Secure` bajo HTTPS; CSP estricta (sin scripts ni estilos inline, sin
iframes), `nosniff`, `no-referrer`, `no-store`; CSRF mitigado (solo JSON + verificación de `Origin`); el navegador
construye el texto con `textContent` (sin `innerHTML`) y solo enlaza URLs `http(s)`.

## 8. Riesgos residuales / pendientes
- Contenido y exactitud: el RAG puede errar; la interfaz remite a undelta.edu.ar y a la Secretaría.
- El proveedor de LLM (OpenRouter) procesa el texto libre: definir si es aceptable para la institución o usar un modelo propio.
- Correo del SIU desactualizado o comprometido → el código llegaría a esa casilla (riesgo inherente a cualquier OTP por mail).
- Falta una prueba de intrusión formal y definir una política de retención del histórico (hoy indefinida).
- El texto libre puede contener datos personales que escriba la persona (se enmascaran números y correos, pero no nombres u otros datos): el aviso en pantalla lo advierte, y conviene que el acceso al dashboard sea solo para quienes auditan.
- El dashboard se opera en una PC local con una copia de la base; esa copia y el token de PythonAnywhere (`tincho/dashboard/.env`) deben protegerse.
- Falta probar los formatos de respuesta reales del SIU y definir con Sistemas el usuario de API de solo lectura.
