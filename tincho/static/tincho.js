(function () {
  const root = document.querySelector('.app');
  const PREFIX = root.dataset.prefix || '';
  const chat = document.getElementById('chat');
  const opciones = document.getElementById('opciones');
  const form = document.getElementById('form');
  const msg = document.getElementById('msg');

  // Render seguro: solo nodos de texto + enlaces http(s) + *negrita*. Nunca innerHTML.
  function render(el, texto) {
    const partes = texto.split(/(https?:\/\/[^\s)]+|\*[^*\n]+\*)/g);
    for (const p of partes) {
      if (!p) continue;
      if (/^https?:\/\//.test(p)) {
        const a = document.createElement('a');
        a.href = p; a.textContent = p; a.target = '_blank'; a.rel = 'noopener noreferrer';
        el.appendChild(a);
      } else if (/^\*[^*\n]+\*$/.test(p)) {
        const b = document.createElement('strong'); b.textContent = p.slice(1, -1); el.appendChild(b);
      } else {
        el.appendChild(document.createTextNode(p));
      }
    }
  }

  function burbuja(texto, quien) {
    const d = document.createElement('div');
    d.className = 'm ' + quien;
    render(d, texto);
    chat.appendChild(d);
    chat.scrollTop = chat.scrollHeight;
  }

  function botones(lista) {
    opciones.replaceChildren();
    for (const o of lista || []) {
      const b = document.createElement('button');
      b.type = 'button'; b.textContent = o.label;
      b.addEventListener('click', () => enviar('', o.id, o.label));
      opciones.appendChild(b);
    }
  }

  async function enviar(texto, option, etiqueta) {
    if (texto || etiqueta) burbuja(texto || etiqueta, 'yo');
    opciones.replaceChildren();
    try {
      const r = await fetch(PREFIX + '/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin', body: JSON.stringify({ message: texto, option: option || null }),
      });
      const j = await r.json();
      burbuja(j.reply || 'Tuve un problema técnico. Probá de nuevo.', 'bot');
      botones(j.options);
    } catch (e) {
      burbuja('No pude conectarme. Revisá tu conexión e intentá de nuevo.', 'bot');
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const t = msg.value.trim();
    if (!t) return;
    msg.value = '';
    enviar(t, null);
  });
  document.getElementById('reset').addEventListener('click', () => enviar('chau', null));
  enviar('', null); // saludo inicial
})();
