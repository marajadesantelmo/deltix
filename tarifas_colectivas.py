# -*- coding: utf-8 -*-
"""
Tarifas de las lanchas colectivas (servicios regulares de transporte público
fluvial de pasajeros del Delta de la Provincia de Buenos Aires).

Fuente: cartel "Actualización tarifaria - Noviembre 2026" (foto del equipo Deltix).
Los valores están transcriptos tal cual figuran en el cartel (en pesos).

Cada fila es: sección, residente ida, residente ida y vuelta (con descuento),
no residente ida, no residente ida y vuelta (con descuento).

Vive en un módulo propio porque lo usan deltix_funciones (Telegram), web_app
(Flask) y los dos conectores LLM, que no se importan entre sí: así hay un solo
lugar para actualizar cuando salga la próxima tarifa.
"""

ACTUALIZACION = "noviembre 2026"

TARIFAS = [
    ("Tránsito mínimo", "307,25",   "491,60",   "593,97",    "950,35"),
    ("1° sección",      "604,26",   "966,82",   "4.004,35",  "6.406,96"),
    ("2° sección",      "727,16",   "1.163,46", "4.895,41",  "7.832,66"),
    ("3° sección",      "857,81",   "1.372,50", "6.791,25",  "10.866,00"),
    ("4° sección",      "942,21",   "1.507,53", "8.193,20",  "13.109,13"),
    ("5° sección",      "1.290,40", "2.064,64", "10.354,23", "16.566,77"),
    ("6° sección",      "1.546,50", "2.474,40", "11.839,20", "18.942,72"),
    ("7° sección",      "1.894,69", "3.031,51", "13.314,00", "21.302,40"),
    ("8° sección",      "2.150,67", "3.441,07", "14.655,68", "23.449,08"),
]


def texto_tarifas(html=False):
    """El mensaje completo. Con html=True usa <b>/<i> para Telegram (parse_mode
    HTML); sin el, texto plano para la web y para el contexto del LLM."""
    def b(t):
        return "<b>%s</b>" % t if html else t

    def i(t):
        return "<i>%s</i>" % t if html else t

    residente = "\n".join(
        "%s: $%s ida · $%s ida y vuelta" % (sec, r_ida, r_iv)
        for sec, r_ida, r_iv, _, _ in TARIFAS)
    no_residente = "\n".join(
        "%s: $%s ida · $%s ida y vuelta" % (sec, n_ida, n_iv)
        for sec, _, _, n_ida, n_iv in TARIFAS)

    return (
        "%s\n"
        "%s\n\n"
        "%s\n%s\n\n"
        "%s\n%s\n\n"
        "%s"
        % (b("💲 Tarifas de lanchas colectivas — actualización %s" % ACTUALIZACION),
           i("Servicios regulares de transporte público fluvial de pasajeros del "
             "Delta de la Provincia de Buenos Aires. Valores en pesos."),
           b("🏠 Categoría Residente"), residente,
           b("🧳 Categoría No residente"), no_residente,
           i("El precio de ida y vuelta es la tarifa con descuento para quien "
             "hace los dos pasajes. La tarifa depende de la sección (distancia) "
             "que se recorre. Los valores pueden cambiar: ante cualquier duda, "
             "consultá con la empresa.")))
