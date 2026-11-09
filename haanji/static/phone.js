// Haanji helpline: a phone in the browser. Records your voice as 16 kHz WAV, sends each turn to the server
// (Gnani speech-to-text -> code answers from the shop's records -> Gnani text-to-speech), then plays the reply.
// The waveform on the phone is drawn from the real audio playing (or your microphone).
(function () {
  const $ = id => document.getElementById(id);
  const H = window.HAANJI;
  let callId = null, busy = false, recorder = null, timerId = null, callStart = 0;

  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const setStatus = t => { $('status').textContent = t; };
  const initials = label => label.startsWith('Unknown') ? '?' : label.split(/[ ,]/).filter(Boolean).slice(0, 2).map(w => w[0]).join('');

  // ---------------------------------------------------------------- live waveform
  let actx = null, analyser = null, vizColor = '#f76707', vizOn = false;
  function audioCtx() {
    if (!actx) {
      actx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = actx.createAnalyser(); analyser.fftSize = 512; analyser.smoothingTimeConstant = 0.7;
      analyser.connect(actx.destination);
      draw();
    }
    if (actx.state === 'suspended') actx.resume();
    return actx;
  }
  function draw() {
    const c = $('viz'), g = c.getContext('2d'), data = new Uint8Array(analyser.frequencyBinCount);
    const bars = 42;
    (function frame() {
      requestAnimationFrame(frame);
      g.clearRect(0, 0, c.width, c.height);
      analyser.getByteFrequencyData(data);
      const w = c.width / bars;
      for (let i = 0; i < bars; i++) {
        const v = vizOn ? data[Math.floor(i * data.length / bars / 1.6)] / 255 : 0;
        const h = Math.max(6, v * c.height * 0.95);
        g.fillStyle = vizOn ? vizColor : 'rgba(255,255,255,.18)';
        const x = i * w + w * 0.25, y = (c.height - h) / 2;
        g.beginPath(); g.roundRect ? g.roundRect(x, y, w * 0.5, h, 4) : g.rect(x, y, w * 0.5, h); g.fill();
      }
    })();
  }
  function speaking(who) {
    vizOn = !!who; vizColor = who === 'caller' ? '#e9ecef' : '#f76707';
    $('device').classList.toggle('talking', who === 'agent');
    $('speaker').textContent = who === 'agent' ? '🔊 Haanji is speaking' : who === 'caller' ? '🗣️ Caller is speaking' : who === 'mic' ? '🎙️ Listening to you' : '';
  }

  function playUrl(url, who) {
    return new Promise(resolve => {
      if (!url) return resolve();
      const a = new Audio(url);
      try { const ctx = audioCtx(); ctx.createMediaElementSource(a).connect(analyser); } catch (e) { /* visual only */ }
      a.onended = a.onerror = () => { speaking(null); resolve(); };
      speaking(who);
      a.play().catch(() => { speaking(null); resolve(); });
    });
  }

  // ---------------------------------------------------------------- stages, order card, phone face
  function stage(name, text) {
    const order = ['hear', 'think', 'speak'];
    order.forEach((s, i) => {
      const el = $('st-' + s);
      el.classList.toggle('on', s === name);
      el.classList.toggle('done', name && order.indexOf(name) > i);
    });
    if (text && name) $('st-' + name + '-t').textContent = text;
  }
  function stagesDone() { ['hear', 'think', 'speak'].forEach(s => { $('st-' + s).classList.remove('on'); $('st-' + s).classList.add('done'); }); }

  const STATUS = { in_transit: 'On the way', delivered: 'Delivered', packed: 'Packed, not shipped' };
  function showOrder(o) {
    if (!o) return;
    $('order-empty').hidden = true; $('order-dl').hidden = false;
    $('order-id').textContent = '#' + o.id; $('order-id').className = 'badge brand';
    const rows = [['Item', o.item], ['Amount', '₹' + o.amount.toLocaleString('en-IN')], ['Status', STATUS[o.status] || o.status],
      ['Courier', o.courier ? `${o.courier} · ${o.awb}` : '—'], ['Shipped', o.shipped_on || '—'],
      [o.delivered_on ? 'Delivered' : 'Expected', o.delivered_on || o.expected_on || '—'], ['Proof', o.proof || (o.last_scan ? 'Last scan: ' + o.last_scan : '—')]];
    $('order-dl').innerHTML = rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('');
    const card = $('order-card'); card.classList.remove('flash'); void card.offsetWidth; card.classList.add('flash');
  }

  function face() {
    const opt = $('caller').selectedOptions[0];
    const label = opt.dataset.label;
    $('avatar').textContent = initials(label);
    $('avatar').classList.toggle('unknown', label.startsWith('Unknown'));
    $('who-name').textContent = label.split(',')[0];
    $('who-num').textContent = opt.dataset.phone + (label.includes(',') ? ' · ' + label.split(',')[1].trim() : '');
  }

  function tick() { const s = Math.floor((Date.now() - callStart) / 1000); $('timer').textContent = `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`; }

  // ---------------------------------------------------------------- conversation
  function add(html, cls) {
    $('empty')?.remove();
    const d = document.createElement('div'); d.className = cls; d.innerHTML = html;
    $('convo').appendChild(d); $('convo').scrollTop = $('convo').scrollHeight;
    return d;
  }
  function agentRow(r) {
    let h = `<div class="who">Haanji${r.tts_s ? `<span class="badge">voice in ${r.tts_s}s</span>` : ''}</div>${esc(r.reply)}`;
    if (r.facts && r.facts.length) h += `<div class="facts"><b>📋 From the shop's records</b>${r.facts.map(esc).join(' · ')}</div>`;
    if (r.ticket) h += `<div class="ticket ${r.ticket.risk ? 'risk' : ''}">🎫 <b>Ticket for the seller:</b> ${esc(r.ticket.summary)}. Waiting for the seller's approval.` +
      (r.ticket.risk ? `<div style="margin-top:4px;color:var(--bad)"><b>⚠ ${esc(r.ticket.risk)}</b></div>` : '') + `</div>`;
    return add(`<div class="av">हाँ</div><div class="msg agent">${h}</div>`, 'row agent');
  }
  function callerRow(r) {
    const opt = $('caller').selectedOptions[0];
    return add(`<div class="av">${esc(initials(opt.dataset.label))}</div><div class="msg caller"><div class="who">${esc(opt.dataset.label.split(',')[0])}` +
      `${r.stt_s != null ? `<span class="badge g">heard by Gnani in ${r.stt_s}s</span>` : ''}</div>${esc(r.heard || '(silence)')}` +
      `<div class="meta"><span class="badge">intent: ${esc(r.intent)}</span>${r.order_id ? `<span class="badge">order ${esc(r.order_id)}</span>` : ''}</div></div>`, 'row caller');
  }

  function setInCall(on) {
    $('call').disabled = on; $('hangup').disabled = !on; $('caller').disabled = on;
    if ($('mic')) $('mic').disabled = !on;
    $('typed-text').disabled = !on; $('typed').querySelector('button').disabled = !on;
    document.querySelectorAll('.samples .chip').forEach(b => { b.disabled = !on; });
  }

  function renderSamples() {
    face();
    const list = $('sample-list');
    if (!list) return;
    const c = H.samples[$('caller').value];
    list.innerHTML = c.lines.map((l, j) => `<button class="chip" data-line="${j}" disabled><span class="pl">▶</span><span>“${esc(l)}”</span></button>`).join('');
    list.querySelectorAll('.chip').forEach(b => b.onclick = () => playSample(+b.dataset.line));
    setInCall(!!callId);
  }

  async function startCall() {
    audioCtx();
    const opt = $('caller').selectedOptions[0];
    busy = true; $('call').disabled = true; setStatus('Ringing…');
    try {
      const r = await (await fetch('/api/call', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone: opt.dataset.phone }) })).json();
      if (r.error) throw new Error(r.error);
      callId = r.call_id; callStart = Date.now(); tick(); timerId = setInterval(tick, 1000);
      document.querySelectorAll('#convo .row, #convo .typing, #convo .sep').forEach(e => e.remove());
      add(`<span class="badge">📞 ${esc(opt.dataset.label)} · ${esc(opt.dataset.phone)}${$('noisy').checked ? ' · noisy line' : ''}</span>`, 'sep');
      setInCall(true);
      agentRow(r);
      stage('speak', 'greeting');
      setStatus('Connected');
      await playUrl(r.audio && `/audio/${r.audio}.mp3`, 'agent');
      stage(null);
      setStatus('Your turn. Tap 🎙️ or play a line.');
    } catch (e) { setStatus('Could not start the call: ' + e.message); $('call').disabled = false; }
    busy = false;
  }

  function endUi(msg) {
    callId = null; clearInterval(timerId); setInCall(false); speaking(null); setStatus(msg);
  }

  async function hangup() {
    if (callId) await fetch(`/api/call/${callId}/hangup`, { method: 'POST' });
    endUi('Call ended.');
  }

  async function sendTurn(form, typed) {
    if (!callId || busy) return;
    busy = true; setInCall(true);
    stage(typed ? 'think' : 'hear', typed ? 'reading your text' : 'transcribing…');
    const typing = add(`<span class="dots"><span></span><span></span><span></span></span> ${typed ? 'Haanji is checking the records…' : 'Gnani is listening…'}`, 'typing');
    setStatus(typed ? 'Checking the records…' : 'Gnani is transcribing…');
    try {
      const r = await (await fetch(`/api/call/${callId}/turn`, { method: 'POST', body: form })).json();
      typing.remove();
      if (r.error) throw new Error(r.error);
      if (r.stt_s != null) $('st-hear-t').textContent = `heard in ${r.stt_s}s`;
      callerRow(r);
      stage('think', r.order_id ? `order ${r.order_id} · ${r.intent}` : r.intent);
      showOrder(r.order);
      await new Promise(res => setTimeout(res, 450));
      agentRow(r);
      stage('speak', r.tts_s ? `voice in ${r.tts_s}s` : 'voice ready');
      setStatus('Haanji is answering');
      await playUrl(r.audio && `/audio/${r.audio}.mp3`, 'agent');
      stagesDone();
      if (r.ended) endUi('Call ended by Haanji. Check the seller dashboard.');
      else setStatus('Your turn. Tap 🎙️ or play a line.');
    } catch (e) { typing.remove(); stage(null); setStatus('Problem: ' + e.message); }
    busy = false;
  }

  async function playSample(j) {
    if (!callId || busy) return;
    const i = $('caller').value;
    busy = true; setInCall(true);
    const url = `/sample/${i}/${j}.wav${$('noisy').checked ? '?phone=1' : ''}`;
    const blob = await (await fetch(url)).blob();
    setStatus('Caller is speaking');
    await playUrl(URL.createObjectURL(blob), 'caller');
    busy = false;
    const f = new FormData(); f.append('audio', blob, `sample-${i}-${j}.wav`);
    await sendTurn(f);
  }

  // ---------------------------------------------------------------- microphone -> 16 kHz WAV
  async function startMic() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    audioCtx();
    const ctx = new AudioContext({ sampleRate: 16000 });
    const src = ctx.createMediaStreamSource(stream);
    const proc = ctx.createScriptProcessor(4096, 1, 1);
    const chunks = [];
    proc.onaudioprocess = e => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    src.connect(proc); proc.connect(ctx.destination);
    const vizSrc = actx.createMediaStreamSource(stream); vizSrc.connect(analyser);
    recorder = { stop: async () => { vizSrc.disconnect(); proc.disconnect(); src.disconnect(); stream.getTracks().forEach(t => t.stop()); await ctx.close(); return wav(chunks, ctx.sampleRate); } };
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
      try { await startMic(); } catch (e) { setStatus('Microphone not available: ' + e.message); return; }
      btn.classList.add('rec'); $('mic-label').textContent = 'Send'; speaking('mic'); vizColor = '#8ce99a';
      setStatus('Speak now, then tap again.');
    } else {
      const blob = await recorder.stop(); recorder = null;
      btn.classList.remove('rec'); $('mic-label').textContent = 'Speak'; speaking(null);
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
    sendTurn(f, true);
  };
  renderSamples();
})();
