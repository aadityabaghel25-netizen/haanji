// Haanji helpline: a phone in the browser. Records your voice as 16 kHz WAV, sends each turn to the server
// (which calls Gnani speech-to-text, answers in code, and calls Gnani text-to-speech), then plays the reply.
(function () {
  const $ = id => document.getElementById(id);
  const H = window.HAANJI;
  let callId = null, busy = false, recorder = null;

  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const setStatus = (text, live) => { $('status').textContent = text; $('dot').classList.toggle('live', !!live); };

  function scrollDown() { const c = $('convo'); c.scrollTop = c.scrollHeight; if (c.scrollHeight <= c.clientHeight + 5) window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); }

  function add(html, cls) {
    $('empty')?.remove();
    const d = document.createElement('div');
    d.className = cls;
    d.innerHTML = html;
    $('convo').appendChild(d);
    scrollDown();
    return d;
  }

  function agentHtml(r) {
    let h = `<div class="who">🔊 Haanji${r.tts_s ? `<span class="badge">voice in ${r.tts_s}s</span>` : ''}</div>${esc(r.reply)}`;
    if (r.facts && r.facts.length) h += `<div class="facts"><b>From the shop's records:</b> ${r.facts.map(esc).join(' · ')}</div>`;
    if (r.ticket) h += `<div class="ticket ${r.ticket.risk ? 'risk' : ''}">🎫 <b>Ticket for the seller:</b> ${esc(r.ticket.summary)}. Waiting for the seller's approval.` +
      (r.ticket.risk ? `<div style="margin-top:4px;color:var(--bad)"><b>⚠ ${esc(r.ticket.risk)}</b></div>` : '') + `</div>`;
    return h;
  }

  function playUrl(url) {
    return new Promise(resolve => {
      if (!url) return resolve();
      const a = new Audio(url);
      a.onended = a.onerror = () => resolve();
      a.play().catch(() => resolve());
    });
  }

  function setInCall(on) {
    $('call').disabled = on; $('hangup').disabled = !on; $('caller').disabled = on;
    if ($('mic')) $('mic').disabled = !on;
    $('typed-text').disabled = !on; $('typed').querySelector('button').disabled = !on;
    document.querySelectorAll('.samples .chip').forEach(b => { b.disabled = !on; });
  }

  function renderSamples() {
    const list = $('sample-list');
    if (!list) return;
    const c = H.samples[$('caller').value];
    list.innerHTML = c.lines.map((l, j) => `<button class="chip" data-line="${j}" disabled>▶ “${esc(l)}”</button>`).join('');
    list.querySelectorAll('.chip').forEach(b => b.onclick = () => playSample(+b.dataset.line));
    setInCall(!!callId);
  }

  async function startCall() {
    const opt = $('caller').selectedOptions[0];
    setStatus('Ringing…', true);
    busy = true; $('call').disabled = true;
    try {
      const r = await (await fetch('/api/call', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: opt.dataset.phone }) })).json();
      if (r.error) throw new Error(r.error);
      callId = r.call_id;
      document.querySelectorAll('#convo .msg, #convo .typing, #convo .sep').forEach(e => e.remove());
      add(`<span class="badge">${esc(opt.textContent)}</span>`, 'sep');
      setInCall(true);
      add(agentHtml(r), 'msg agent');
      setStatus('On the call. Haanji is speaking…', true);
      await playUrl(r.audio && `/audio/${r.audio}.mp3`);
      setStatus('On the call. Your turn.', true);
    } catch (e) { setStatus('Could not start the call: ' + e.message); $('call').disabled = false; }
    busy = false;
  }

  async function hangup() {
    if (callId) await fetch(`/api/call/${callId}/hangup`, { method: 'POST' });
    callId = null; setInCall(false); setStatus('Call ended.');
  }

  async function sendTurn(form, previewText) {
    if (!callId || busy) return;
    busy = true; setInCall(true);
    const typing = add(previewText ? '' : '🎧 Gnani is listening…', 'typing');
    try {
      const r = await (await fetch(`/api/call/${callId}/turn`, { method: 'POST', body: form })).json();
      typing.remove();
      if (r.error) throw new Error(r.error);
      add(`<div class="who">🗣️ Caller${r.stt_s != null ? `<span class="badge">heard by Gnani in ${r.stt_s}s</span>` : ''}</div>${esc(r.heard || '(silence)')}` +
          `<div class="meta"><span class="badge">intent: ${esc(r.intent)}</span>${r.order_id ? `<span class="badge">order ${esc(r.order_id)}</span>` : ''}</div>`, 'msg caller');
      add(agentHtml(r), 'msg agent');
      setStatus('Haanji is speaking…', true);
      await playUrl(r.audio && `/audio/${r.audio}.mp3`);
      if (r.ended) { callId = null; setInCall(false); setStatus('Call ended by Haanji. Check the seller dashboard.'); }
      else setStatus('On the call. Your turn.', true);
    } catch (e) { typing.remove(); setStatus('Problem: ' + e.message, true); }
    busy = false;
  }

  async function playSample(j) {
    if (!callId || busy) return;
    const i = $('caller').value;
    busy = true; setInCall(true);
    setStatus('Caller is speaking…', true);
    const url = `/sample/${i}/${j}.wav${$('noisy').checked ? '?phone=1' : ''}`;
    const blob = await (await fetch(url)).blob();
    await playUrl(URL.createObjectURL(blob));
    busy = false;
    const f = new FormData(); f.append('audio', blob, `sample-${i}-${j}.wav`);
    await sendTurn(f);
  }

  // ---- microphone: raw PCM at 16 kHz -> WAV (Gnani's REST API takes WAV, MP3, OGG, FLAC, AAC, M4A; not WebM)
  async function startMic() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    const ctx = new AudioContext({ sampleRate: 16000 });
    const src = ctx.createMediaStreamSource(stream);
    const proc = ctx.createScriptProcessor(4096, 1, 1);
    const chunks = [];
    proc.onaudioprocess = e => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    src.connect(proc); proc.connect(ctx.destination);
    recorder = { stop: async () => { proc.disconnect(); src.disconnect(); stream.getTracks().forEach(t => t.stop()); await ctx.close(); return wav(chunks, ctx.sampleRate); } };
    setTimeout(() => { if (recorder) toggleMic(); }, 28000);   // Gnani REST takes clips up to 30 s
  }

  function wav(chunks, rate) {
    const n = chunks.reduce((s, c) => s + c.length, 0);
    const buf = new ArrayBuffer(44 + n * 2), v = new DataView(buf);
    const w = (o, s) => [...s].forEach((ch, k) => v.setUint8(o + k, ch.charCodeAt(0)));
    w(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); w(8, 'WAVE'); w(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true);
    v.setUint16(22, 1, true); v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
    w(36, 'data'); v.setUint32(40, n * 2, true);
    let o = 44;
    for (const c of chunks) for (const x of c) { v.setInt16(o, Math.max(-1, Math.min(1, x)) * 0x7fff, true); o += 2; }
    return new Blob([buf], { type: 'audio/wav' });
  }

  async function toggleMic() {
    const btn = $('mic');
    if (!recorder) {
      if (busy || !callId) return;
      try { await startMic(); } catch (e) { setStatus('Microphone not available: ' + e.message, true); return; }
      btn.classList.add('rec'); $('mic-label').textContent = 'Listening… tap to send';
      setStatus('Speak now.', true);
    } else {
      const blob = await recorder.stop(); recorder = null;
      btn.classList.remove('rec'); $('mic-label').textContent = 'Tap to speak';
      const f = new FormData(); f.append('audio', blob, 'mic.wav');
      await sendTurn(f);
    }
  }

  $('call').onclick = startCall;
  $('hangup').onclick = hangup;
  $('caller').onchange = renderSamples;
  if ($('mic')) $('mic').onclick = toggleMic;
  $('typed').onsubmit = e => {
    e.preventDefault();
    const t = $('typed-text').value.trim();
    if (!t) return;
    $('typed-text').value = '';
    const f = new FormData(); f.append('text', t);
    sendTurn(f, t);
  };
  renderSamples();
})();
