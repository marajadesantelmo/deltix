(function () {
  const body = document.body;
  const PREFIX = body.dataset.prefix || '';
  const chat = document.getElementById('chat-messages');
  const landingChips = document.getElementById('landing-chips');
  const form = document.getElementById('form');
  const msg = document.getElementById('msg');
  const sendBtn = form.querySelector('.send-btn');
  let saludo = null;       // primera respuesta del bot (se muestra al salir de la bienvenida)
  let ocupado = false;

  // Render seguro: solo nodos de texto + enlaces http(s) + *negrita*. Nunca innerHTML.
  function render(el, texto) {
    for (const p of texto.split(/(https?:\/\/[^\s)]+|\*[^*\n]+\*)/g)) {
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

  function quitarOpciones() { chat.querySelectorAll('.quick-replies').forEach((n) => n.remove()); }
  function bajar() { chat.scrollTop = chat.scrollHeight; }

  function fila(quien) {
    const row = document.createElement('div');
    row.className = 'msg-row ' + quien;
    if (quien === 'bot') {
      const av = document.createElement('div'); av.className = 'bot-avatar'; av.textContent = 'T'; av.setAttribute('aria-hidden', 'true');
      row.appendChild(av);
    }
    const col = document.createElement('div'); col.className = 'msg-col';
    row.appendChild(col);
    chat.appendChild(row);
    return col;
  }

  function burbuja(texto, quien) {
    const col = fila(quien);
    const b = document.createElement('div'); b.className = 'bubble ' + quien;
    render(b, texto); col.appendChild(b);
    bajar();
    return col;
  }

  function botones(contenedor, lista) {
    for (const o of lista || []) {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'qr-btn'; b.textContent = o.label;
      b.addEventListener('click', () => enviar('', o.id, o.label));
      contenedor.appendChild(b);
    }
  }

  function mostrarBot(j) {
    const col = burbuja(j.reply || 'Tuve un problema técnico. Probá de nuevo.', 'bot');
    if (j.options && j.options.length) {
      const q = document.createElement('div'); q.className = 'quick-replies';
      botones(q, j.options); col.appendChild(q);
    }
    bajar();
  }

  function entrarAlChat() {
    if (!body.classList.contains('is-landing')) return;
    body.classList.remove('is-landing'); body.classList.add('is-chat');
    if (saludo) burbuja(saludo, 'bot');
  }

  function escribiendo(on) {
    const prev = document.getElementById('typing-row');
    if (prev) prev.remove();
    if (!on) return;
    const col = fila('bot'); col.parentElement.id = 'typing-row';
    const t = document.createElement('div'); t.className = 'typing';
    for (let i = 0; i < 3; i++) t.appendChild(document.createElement('span'));
    col.appendChild(t); bajar();
  }

  async function pedir(texto, option) {
    const r = await fetch(PREFIX + '/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin',
      body: JSON.stringify({ message: texto, option: option || null }),
    });
    return r.json();
  }

  async function enviar(texto, option, etiqueta) {
    if (ocupado) return;
    ocupado = true; sendBtn.disabled = true;
    entrarAlChat();
    quitarOpciones();
    if (texto || etiqueta) burbuja(texto || etiqueta, 'user');
    escribiendo(true);
    try {
      const j = await pedir(texto, option);
      escribiendo(false);
      mostrarBot(j);
    } catch (e) {
      escribiendo(false);
      mostrarBot({ reply: 'No pude conectarme. Revisá tu conexión e intentá de nuevo.' });
    } finally {
      ocupado = false; sendBtn.disabled = false; msg.focus();
    }
  }

  // Saludo inicial: se pide al servidor, pero se muestra recién al primer movimiento de la persona.
  (async function iniciar() {
    try {
      const j = await pedir('', null);
      saludo = j.reply;
      botones(landingChips, j.options);
      // Sin opciones = el bot pide la clave de acceso: se lo explicamos en la bienvenida.
      if (!(j.options && j.options.length) && j.reply) document.getElementById('landing-sub').textContent = j.reply;
    } catch (e) { /* queda la bienvenida sin botones; se puede escribir igual */ }
  })();

  // Entrada: Enter envía, Shift+Enter salto de línea; el campo crece hasta 120px.
  function ajustar() { msg.style.height = 'auto'; msg.style.height = Math.min(msg.scrollHeight, 120) + 'px'; }
  msg.addEventListener('input', ajustar);
  msg.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const t = msg.value.trim();
    if (!t) return;
    msg.value = ''; ajustar();
    enviar(t, null);
  });
  document.getElementById('reset').addEventListener('click', () => enviar('chau', null));
})();
