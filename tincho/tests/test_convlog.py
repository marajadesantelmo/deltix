"""Tests del histórico de conversaciones. Correr:  python -m unittest discover -s tincho/tests -v"""
import os
import sqlite3
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from test_tincho import Base, config, flows, store  # noqa: E402
from tincho import convlog  # noqa: E402


class TestConvlog(Base):
    def filas(self):
        con = sqlite3.connect(convlog.ruta())
        try:
            return con.execute("SELECT tipo, usuario, bot, fuentes, opciones, sesion FROM mensajes ORDER BY id").fetchall()
        finally:
            con.close()

    def volcado(self):
        return " ".join(str(c) for f in self.filas() for c in f)

    def test_registra_menu_y_rag(self):
        self.say()                          # carga inicial de la página
        self.say("hola")
        self.say(option="carreras")
        self.say("cuánto dura enfermería universitaria")
        self.say("receta de milanesas con papas")
        tipos = [f[0] for f in self.filas()]
        self.assertEqual(tipos, ["inicio", "comando", "opcion", "rag", "rag_sin_dato"])
        rag = self.filas()[3]
        self.assertIn("3 años", rag[2])
        self.assertTrue(rag[3].startswith("https://"))       # fuentes
        self.assertIn("Menú principal", rag[4])              # opciones ofrecidas

    def test_no_guarda_datos_sensibles_del_siu(self):
        self.say("siu")
        _, code = self.codigo_enviado("30123456")
        self.say(code)
        self.say(option="sa:cursadas")
        self.say(option="sa:resumen")
        v = self.volcado()
        for prohibido in ("30123456", code, "Introducción a la Ciencia de Datos", "5 de 22", "example.com"):
            self.assertNotIn(prohibido, v)
        tipos = [f[0] for f in self.filas()]
        self.assertEqual(tipos.count("siu_verificacion"), 2)
        self.assertEqual(tipos.count("siu_consulta"), 2)
        self.assertIn(convlog.SIU_OMITIDA, v)
        self.assertIn(convlog.SENSIBLE, v)

    def test_modo_no_identificar_tampoco_guarda_el_dni(self):
        config.CLAVE_INICIO = "clave-prueba"
        for t in ("clave-prueba", "siu", "no identificar", "30123456"):
            self.say(t)
        self.say(option="sa:cursadas")
        v = self.volcado()
        self.assertNotIn("30123456", v)
        self.assertNotIn("Ciencia de Datos", v)

    def test_clave_de_inicio_no_se_guarda(self):
        config.CLAVE_INICIO = "clave-secreta-xyz"
        self.say("hola")
        self.say("clave-secreta-xyz")
        v = self.volcado()
        self.assertNotIn("clave-secreta-xyz", v)
        self.assertIn(convlog.ANTES_DE_CLAVE, v)
        self.assertIn("[clave]", v)
        self.assertEqual([f[0] for f in self.filas()], ["sistema", "clave"])

    def test_enmascara_numeros_y_correos_en_texto_libre(self):
        self.say("mi dni es 30.123.456 y mi cel 1155653035, escribime a ana@example.com")
        u = self.filas()[0][1]
        for prohibido in ("30.123.456", "1155653035", "ana@example.com"):
            self.assertNotIn(prohibido, u)
        self.assertIn("[número]", u)
        self.assertIn("[correo]", u)

    def test_sesion_es_hmac_no_la_cookie(self):
        self.say("hola")
        ses = self.filas()[0][5]
        self.assertNotIn(self.sid[:6], ses)
        self.assertEqual(len(ses), 10)

    def test_auditoria_tampoco_guarda_parte_de_la_cookie(self):
        self.say("siu")
        self.codigo_enviado("30123456")
        eventos = store._db().execute("SELECT sid FROM auditoria").fetchall()
        self.assertTrue(eventos)
        for (s,) in eventos:
            self.assertNotIn(self.sid[:6], s)

    def test_si_el_log_falla_el_bot_responde(self):
        archivo = os.path.join(self.tmp.name, "no_es_carpeta")
        open(archivo, "w").close()
        # la base del histórico apunta a una ruta imposible; la de sesiones sigue sana
        with mock.patch.object(convlog, "ruta", return_value=os.path.join(archivo, "x.db")):
            r = self.say("hola")
            convlog.registrar(self.sid, "rag", "x", "y")   # tampoco debe lanzar
        self.assertIn("Tincho", r["reply"])

    def test_purgar_manual(self):
        self.say("hola")
        con = sqlite3.connect(convlog.ruta())
        con.execute("UPDATE mensajes SET ts='2020-01-01 00:00:00'")
        con.commit(); con.close()
        self.say("carreras")
        self.assertEqual(convlog.purgar(90), 1)
        self.assertEqual(len(self.filas()), 1)

    def test_el_navegador_no_recibe_claves_internas(self):
        r = flows.procesar(self.sid, self.ip, "cuánto dura enfermería universitaria")
        self.assertEqual(set(r), {"reply", "options"})


if __name__ == "__main__":
    unittest.main()
