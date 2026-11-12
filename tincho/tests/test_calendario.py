"""Calendario académico y límites de uso. Casos tomados del reporte de prueba del 11/11/2026."""
import os
import sqlite3
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from test_tincho import Base, config, store  # noqa: E402
from tincho import calendario, convlog, kb  # noqa: E402

# (pregunta, fecha correcta publicada). Antes, el LLM contestaba con la fecha de la fila siguiente.
REPORTE = [
    ("¿Cuándo es la inscripción a materias del segundo cuatrimestre?", "27/07 al 02/08"),
    ("¿Cuándo es el receso invernal?", "27/07 al 08/08"),
    ("¿Cuándo empieza el segundo cuatrimestre?", "10/08"),
    ("¿Cuándo termina el segundo cuatrimestre?", "28/11"),
    ("¿Cuándo es el segundo llamado de finales de julio?", "20/07 al 25/07"),
    ("¿Cuándo es la inscripción a finales de diciembre en modalidad libre?", "08/12 al 09/12"),
    ("¿Cuándo es el primer llamado de finales de diciembre?", "07/12 al 12/12"),
    ("¿Cuándo es el cambio de carrera?", "07/07 al 10/07"),
]


class TestCalendario(Base):
    def test_cada_pregunta_del_reporte_da_su_propia_fecha(self):
        for pregunta, fecha in REPORTE:
            r = self.say(pregunta)["reply"]
            self.assertIn(f": {fecha}\n", r + "\n", pregunta)
            self.assertEqual(r.count("📅"), 1, pregunta)      # una sola fila, no la de al lado

    def test_se_registra_como_calendario_sin_usar_el_llm(self):
        with mock.patch("tincho.llm.responder", side_effect=AssertionError("no debe llamar al LLM")):
            r = self.say("¿Cuándo termina el segundo cuatrimestre?")
        self.assertIn("28/11", r["reply"])
        self.assertIn("vale la resolución", r["reply"])
        con = sqlite3.connect(convlog.ruta())
        try:
            self.assertEqual(con.execute("SELECT tipo FROM mensajes ORDER BY id DESC LIMIT 1").fetchone()[0], "calendario")
        finally:
            con.close()

    def test_pregunta_ambigua_devuelve_las_filas_en_orden_del_calendario(self):
        r = self.say("¿cuándo empiezan las clases?")["reply"]
        self.assertLess(r.index("23/03"), r.index("10/08"))

    def test_no_captura_preguntas_ajenas(self):
        for q in ("qué carreras tiene la UNDelta", "cuánto cuesta estudiar", "quién es el rector"):
            self.assertFalse(calendario.es_pregunta_de_calendario(q), q)

    def test_sin_fila_parecida_cae_al_flujo_normal(self):
        self.assertIsNone(calendario.responder("cuándo es la mesa de examen de física cuántica avanzada"))

    def test_menu_y_palabra_clave_muestran_las_fechas(self):
        for texto in ("calendario", "calendario académico"):
            r = self.say(texto)["reply"]
            self.assertIn("27/07 al 08/08: Receso invernal estudiantil", r)
            self.assertIn("28/11: Finalización del segundo cuatrimestre", r)
        self.say("inscripciones")
        self.assertIn("10/08: Inicio del segundo cuatrimestre", self.say(option="ing:cal")["reply"])

    def test_fragmentos_del_rag_mantienen_fecha_y_evento_juntos(self):
        chunks = [c for c in kb.get_retriever().chunks if c["fuente"] == "calendario"]
        self.assertTrue(chunks)
        todo = "\n".join(c["texto"] for c in chunks)
        self.assertIn("- 27/07 al 08/08: Receso invernal estudiantil", todo)
        self.assertIn("- 10/08: Inicio del segundo cuatrimestre", todo)
        # ya no queda la tabla aplastada del crawler viejo
        self.assertFalse([c for c in kb.get_retriever().chunks if "Fecha\nQué pasa" in c["texto"]])


class TestCrawlerTablas(unittest.TestCase):
    HTML = ("<table class='tabla-cal'><caption>Cursada 2026. Vale la resolución.</caption>"
            "<tr class='mes'><th colspan='2' scope='colgroup'>Julio</th></tr>"
            "<tr><th scope='row'>27/07 al 02/08</th><td>Inscripción a materias</td></tr>"
            "<tr><th scope='row'>27/07 al 08/08</th><td>Receso invernal</td></tr>"
            "<tr class='mes'><th colspan='2' scope='colgroup'>Agosto</th></tr>"
            "<tr class='hito'><th scope='row'>10/08</th><td>Inicio <span class='sello-hito'>hito del año</span></td></tr></table>")

    def setUp(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

    def test_extrae_pares_fecha_evento(self):
        import crawl_undelta as c
        from bs4 import BeautifulSoup
        cal = c.extraer_calendario(BeautifulSoup("<h2>Calendario académico 2026</h2>" + self.HTML, "html.parser"))
        self.assertEqual([(f["mes"], f["fecha"], f["evento"], f["hito"]) for f in cal["filas"]],
                         [("Julio", "27/07 al 02/08", "Inscripción a materias", False),
                          ("Julio", "27/07 al 08/08", "Receso invernal", False),
                          ("Agosto", "10/08", "Inicio", True)])
        self.assertIn("Vale la resolución", cal["aclaracion"])

    def test_otras_tablas_se_aplanan_por_fila(self):
        import crawl_undelta as c
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<main><table><tr><th>Cargo</th><td>Rectora</td></tr>"
                             "<tr><th>Área</th><td>Gestión</td></tr></table></main>", "html.parser")
        self.assertEqual(c.limpiar(soup), "Cargo — Rectora\nÁrea — Gestión")


class TestLimites(Base):
    def test_hit_all_es_atomico_y_informa_la_espera(self):
        reglas = [("a", 2, 60), ("b", 1, 3600)]
        self.assertEqual(store.hit_all(reglas), (True, 0))
        ok, espera = store.hit_all(reglas)                 # "b" ya se agotó
        self.assertFalse(ok)
        self.assertGreater(espera, 3500)
        n_a = store._db().execute("SELECT COUNT(*) FROM hits WHERE clave='a'").fetchone()[0]
        self.assertEqual(n_a, 1)                           # el intento rechazado NO gastó cupo de "a"

    def test_limite_por_sesion_avisa_cuanto_esperar_y_no_afecta_a_otra_sesion(self):
        for i in range(config.LLM_SID_MIN):
            self.assertNotIn("muchas consultas", self.say(f"pregunta de prueba número {i} sobre becas")["reply"])
        r = self.say("una pregunta más sobre becas")
        self.assertIn("muchas consultas", r["reply"])
        self.assertRegex(r["reply"], r"(un minuto|\d+ minutos)")
        self.sid = "otra" * 6                              # otra persona, misma IP: no queda bloqueada
        self.assertNotIn("muchas consultas", self.say("pregunta de otra persona sobre becas")["reply"])

    def test_el_limite_por_ip_protege_aunque_se_roten_cookies(self):
        with mock.patch.object(config, "LLM_IP_MIN", 3):
            resp = []
            for i in range(5):
                self.sid = f"s{i}" * 10
                resp.append(self.say("pregunta sobre becas de estudio")["reply"])
        self.assertEqual(sum("muchas consultas" in r for r in resp), 2)

    def test_calendario_y_menus_no_gastan_cupo_del_llm(self):
        for _ in range(config.LLM_SID_MIN + 3):
            self.say("¿Cuándo es el receso invernal?")
            self.say("carreras")
        self.assertNotIn("muchas consultas", self.say("pregunta de prueba sobre becas")["reply"])


class TestIPCliente(Base):
    def test_usa_x_real_ip_detras_del_proxy(self):
        from flask import Flask
        from tincho.blueprint import _ip_cliente
        app = Flask(__name__)
        base = {"REMOTE_ADDR": "10.0.0.1"}
        with app.test_request_context("/", environ_base=base, headers={"X-Real-IP": "190.2.3.4"}):
            self.assertEqual(_ip_cliente(), "190.2.3.4")
        with app.test_request_context("/", environ_base=base, headers={"X-Real-IP": "no-es-una-ip"}):
            self.assertEqual(_ip_cliente(), "10.0.0.1")     # cabecera inválida: se ignora
        with app.test_request_context("/", environ_base=base):
            self.assertEqual(_ip_cliente(), "10.0.0.1")     # sin cabecera
        with mock.patch.object(config, "PROXY_HEADER", ""), \
                app.test_request_context("/", environ_base=base, headers={"X-Real-IP": "190.2.3.4"}):
            self.assertEqual(_ip_cliente(), "10.0.0.1")     # cabecera desactivada


if __name__ == "__main__":
    unittest.main()
