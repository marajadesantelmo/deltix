"""Base de conocimiento (RAG) de Tincho: chunking + recuperación BM25 en Python puro.

Sin embeddings ni dependencias pesadas: corre igual en PythonAnywhere. El índice se arma al
cargar desde data/kb/chunks.json (generado por scripts/build_kb.py).
"""
import json
import math
import os
import re
import unicodedata
from collections import Counter

from . import config

CHUNKS_PATH = os.path.join(config.DATA_DIR, "kb", "chunks.json")

STOP = set("""a al algo ante con como cual cuales cuando de del desde donde e el ella ellos en entre es esta estan
este esto esa eso fue ha hay la las le les lo los me mi mis muy ni no nos o para pero por que se si sin sobre su sus
te tu tus un una uno unos unas y ya yo soy son ser puedo quien quiero quisiera saber necesito tengo hola tincho""".split())


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def stem(w):
    for suf in ("aciones", "acion", "mente", "ones", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


# Expansión mínima de sinónimos frecuentes en preguntas de estudiantes.
SINONIMOS = {
    "ubicacion": "direccion sede avellaneda", "queda": "direccion sede avellaneda",
    "ubicada": "direccion sede avellaneda", "domicilio": "direccion sede avellaneda",
    "horario": "horario atencion", "abierto": "horario atencion", "atienden": "horario atencion",
    "atiende": "horario atencion", "anotarme": "inscripcion", "anotar": "inscripcion",
    "inscribirme": "inscripcion", "ingresar": "ingreso inscripcion",
    "papeles": "documentacion", "requisitos": "documentacion", "titulo": "titulo documentacion",
    "plata": "gratuita arancel", "cuesta": "gratuita arancel", "cuota": "gratuita arancel", "arancel": "gratuita",
    "mail": "correo email", "telefono": "whatsapp contacto", "celular": "whatsapp contacto",
    "rector": "rectora rectorado autoridades", "rectora": "rector rectorado autoridades",
    "autoridades": "organigrama rectorado",
}


def expandir(consulta):
    extra = [SINONIMOS[w] for w in re.findall(r"[a-z0-9]+", norm(consulta)) if w in SINONIMOS]
    return consulta + " " + " ".join(extra)


def tokens(text):
    return [stem(w) for w in re.findall(r"[a-z0-9]+", norm(text)) if w not in STOP and len(w) > 1]


class Retriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.docs = [Counter(tokens(c["titulo"] + " " + c["titulo"] + " " + c["texto"])) for c in chunks]
        self.len = [sum(d.values()) for d in self.docs]
        self.avg = (sum(self.len) / len(self.len)) if self.len else 1
        df = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def buscar(self, consulta, k=4, k1=1.4, b=0.75):
        q = tokens(expandir(consulta))
        if not q:
            return []
        scores = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in q:
                f = d.get(t)
                if f:
                    s += self.idf.get(t, 0) * f * (k1 + 1) / (f + k1 * (1 - b + b * self.len[i] / self.avg))
            if s > 0:
                s *= self.chunks[i].get("peso", 1.0)
                scores.append((s, i))
        scores.sort(reverse=True)
        out = []
        for s, i in scores[:k]:
            c = dict(self.chunks[i])
            c["score"] = round(s, 2)
            out.append(c)
        return out


_retriever = None


def get_retriever():
    global _retriever
    if _retriever is None:
        with open(CHUNKS_PATH, encoding="utf-8") as f:
            _retriever = Retriever(json.load(f)["chunks"])
    return _retriever


# Umbral mínimo: por debajo, Tincho dice que no tiene el dato en vez de improvisar.
UMBRAL = 3.0


def contexto_para(pregunta, k=4):
    hits = [h for h in get_retriever().buscar(pregunta, k=k) if h["score"] >= UMBRAL]
    return hits
