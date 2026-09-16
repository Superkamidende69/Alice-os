const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const vm = require("node:vm");

const flush = async () => { for (let index = 0; index < 12; index += 1) await Promise.resolve(); };
const source = readFileSync(resolve(__dirname, "../web/hands-free.js"), "utf8");

function harness(options = {}) {
  const streams = [], sockets = [], contexts = [], worklets = [], requests = [], states = [], wakes = [], speech = [], transcripts = [], errors = [];
  const timers = new Map();
  let timerId = 0;
  const document = Object.assign(new EventTarget(), { hidden: false });
  const window = new EventTarget();
  class Track extends EventTarget {
    constructor() { super(); this.stops = 0; this.readyState = "live"; }
    stop() { this.stops += 1; this.readyState = "ended"; }
  }
  function makeStream() {
    const track = new Track();
    const stream = { track, getTracks: () => [track] };
    streams.push(stream);
    return stream;
  }
  class AudioNode {
    constructor() { this.connections = []; this.disconnects = 0; }
    connect(node) { this.connections.push(node); return node; }
    disconnect() { this.disconnects += 1; }
  }
  class AudioContext extends EventTarget {
    constructor(configuration) {
      super();
      this.configuration = configuration;
      this.sampleRate = options.sampleRate || 16000;
      this.state = "suspended";
      this.closes = 0;
      this.destination = {};
      this.modules = [];
      this.audioWorklet = { addModule: async (url) => { this.modules.push(url); await options.addModule?.(); } };
      contexts.push(this);
    }
    async resume() { this.state = "running"; }
    close() { this.closes += 1; this.state = "closed"; this.dispatchEvent(new Event("statechange")); return Promise.resolve(); }
    createMediaStreamSource(stream) { this.mediaSource = Object.assign(new AudioNode(), { stream }); return this.mediaSource; }
    createGain() { this.mute = Object.assign(new AudioNode(), { gain: { value: 1 } }); return this.mute; }
  }
  class Worklet extends AudioNode {
    constructor(context, name) { super(); this.context = context; this.name = name; this.port = {}; worklets.push(this); }
    packet(bytes = new ArrayBuffer(1920)) { this.port.onmessage?.({ data: bytes }); }
  }
  class Socket {
    static OPEN = 1;
    constructor(url) { this.url = String(url); this.readyState = 0; this.bufferedAmount = 0; this.sent = []; this.closes = 0; sockets.push(this); }
    send(value) { if (options.sendError) throw new Error("send failed"); this.sent.push(value); }
    close() { this.closes += 1; this.readyState = 3; this.onclose?.(); }
    open() { this.readyState = 1; this.onopen?.(); }
    message(message) { this.onmessage?.({ data: JSON.stringify(message) }); }
    json() { return this.sent.filter((value) => typeof value === "string").map((value) => JSON.parse(value)); }
  }
  Object.assign(window, { AudioContext, AudioWorkletNode: Worklet, WebSocket: Socket });
  const navigator = { mediaDevices: { getUserMedia: async (configuration) => {
    requests.push(configuration);
    return options.getUserMedia ? options.getUserMedia() : makeStream();
  } } };
  const context = vm.createContext({
    window, document, navigator, location: { href: "http://localhost:8765/", protocol: "http:" },
    URL, ArrayBuffer, console,
    setTimeout: (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id; },
    clearTimeout: (id) => timers.delete(id),
  });
  vm.runInContext(source, context);
  const client = new window.AliceHandsFree({
    onState: (event) => states.push(event), onWake: (event) => wakes.push(event),
    onSpeechStart: (event) => speech.push(event), onTranscript: (event) => transcripts.push(event), onError: (error) => errors.push(error),
  });
  const ready = (socket = sockets.at(-1)) => {
    socket.open();
    socket.message({ event: "ready", sample_rate: 16000, frame_ms: 20, local: true });
  };
  const start = async (configuration) => {
    const pending = client.start(configuration);
    await flush();
    ready();
    assert.equal(await pending, true);
    return sockets.at(-1);
  };
  const event = (kind, extra = {}) => ({ event: kind, context_revision: client.contextRevision, ...extra });
  return { client, window, document, navigator, sockets, streams, contexts, worklets, requests, timers, states, wakes, speech, transcripts, errors, makeStream, ready, start, event };
}

test("hands-free stays off until explicitly started and needs no browser recognition API", async () => {
  const api = harness();
  assert.equal(api.requests.length, 0);
  assert.equal(api.client.active, false);
  assert.equal(api.window.SpeechRecognition, undefined);
  const socket = await api.start({ wake_phrase: "hey alice", end_silence_ms: 1100, followup_seconds: 8 });
  assert.equal(socket.url, "ws://localhost:8765/api/voice/conversation");
  assert.deepEqual(socket.json()[0], { type: "configure", wake_phrase: "hey alice", end_silence_ms: 1100, followup_seconds: 8 });
  assert.equal(socket.json()[1].type, "context");
  assert.equal(socket.json()[1].revision, api.client.contextRevision);
  assert.equal(api.client.active, true);
  assert.equal(api.client.connecting, false);
  assert.equal(api.timers.size, 0);
  api.client.stop();
});

test("microphone audio waits for server readiness and is always routed through zero gain", async () => {
  const api = harness();
  const pending = api.client.start();
  await flush();
  const socket = api.sockets[0];
  socket.open();
  assert.equal(api.worklets.length, 0);
  assert.equal(socket.sent.length, 0);
  assert.equal(api.contexts[0].mediaSource, undefined);
  api.ready();
  assert.equal(await pending, true);
  const context = api.contexts[0];
  const worklet = api.worklets[0];
  assert.equal(context.mute.gain.value, 0);
  assert.deepEqual(context.mediaSource.connections, [worklet]);
  assert.deepEqual(worklet.connections, [context.mute]);
  assert.deepEqual(context.mute.connections, [context.destination]);
  worklet.packet();
  assert.equal(socket.sent.at(-1).byteLength, 1920);
  api.client.stop();
});

test("stop resolves a pending permission request immediately and reclaims a late microphone", async () => {
  let grant;
  const api = harness({ getUserMedia: () => new Promise((resolve) => { grant = resolve; }) });
  const pending = api.client.start();
  api.client.stop();
  assert.equal(await pending, false);
  const stream = api.makeStream();
  grant(stream);
  await flush();
  assert.equal(stream.track.stops, 1);
  assert.equal(api.contexts.length, 0);
  assert.equal(api.sockets.length, 0);
  assert.equal(api.errors.length, 0);
});

test("stopping while the worklet loads releases the context and prevents a late connection", async () => {
  let loaded;
  const api = harness({ addModule: () => new Promise((resolve) => { loaded = resolve; }) });
  const pending = api.client.start();
  await flush();
  api.client.stop();
  assert.equal(await pending, false);
  loaded();
  await flush();
  assert.equal(api.streams[0].track.stops, 1);
  assert.equal(api.contexts[0].closes, 1);
  assert.equal(api.sockets.length, 0);
});

test("the startup deadline releases the microphone and a late ready event cannot restart it", async () => {
  const api = harness();
  const pending = api.client.start();
  await flush();
  const socket = api.sockets[0];
  const lateMessage = socket.onmessage;
  const deadline = [...api.timers.values()][0];
  assert.equal(deadline.delay, 30000);
  deadline.fn();
  assert.equal(await pending, false);
  lateMessage({ data: JSON.stringify({ event: "ready", sample_rate: 16000 }) });
  assert.equal(api.client.active, false);
  assert.equal(api.streams[0].track.stops, 1);
  assert.equal(socket.closes, 1);
  assert.equal(api.worklets.length, 0);
  assert.equal(api.errors.length, 1);
  assert.match(api.errors[0].message, /in time/);
});

test("server disconnect releases every capture resource and does not reconnect automatically", async () => {
  const api = harness();
  const socket = await api.start();
  socket.close();
  assert.equal(api.client.active, false);
  assert.equal(api.streams[0].track.stops, 1);
  assert.equal(api.contexts[0].closes, 1);
  assert.equal(api.contexts[0].mediaSource.disconnects, 1);
  assert.equal(api.worklets[0].disconnects, 1);
  assert.equal(api.contexts[0].mute.disconnects, 1);
  assert.equal(api.worklets[0].port.onmessage, null);
  assert.equal(api.timers.size, 0);
  assert.match(api.errors[0].message, /disconnected/);
  await flush();
  assert.equal(api.requests.length, 1);
});

test("microphone loss and audio processor failure both end the session visibly", async () => {
  for (const trigger of [
    (api) => api.streams[0].track.dispatchEvent(new Event("ended")),
    (api) => api.worklets[0].onprocessorerror(),
    (api) => { api.contexts[0].state = "suspended"; api.contexts[0].dispatchEvent(new Event("statechange")); },
  ]) {
    const api = harness();
    await api.start();
    trigger(api);
    assert.equal(api.client.active, false);
    assert.equal(api.streams[0].track.stops, 1);
    assert.equal(api.errors.length, 1);
  }
});

test("hidden, pagehide, and offline release capture; showing the page never resumes it", async () => {
  for (const kind of ["visibilitychange", "pagehide", "offline"]) {
    const api = harness();
    await api.start();
    if (kind === "visibilitychange") { api.document.hidden = true; api.document.dispatchEvent(new Event(kind)); }
    else api.window.dispatchEvent(new Event(kind));
    assert.equal(api.client.active, false);
    assert.equal(api.streams[0].track.stops, 1);
    api.document.hidden = false;
    api.document.dispatchEvent(new Event("visibilitychange"));
    assert.equal(api.requests.length, 1);
    assert.equal(api.timers.size, 0);
  }
});

test("outbound audio is bounded and stops before sending an oversized buffer", async () => {
  const api = harness();
  const socket = await api.start();
  socket.bufferedAmount = 32000 - 1920;
  api.worklets[0].packet();
  const sent = socket.sent.length;
  socket.bufferedAmount += 1;
  api.worklets[0].packet();
  assert.equal(socket.sent.length, sent);
  assert.equal(api.client.active, false);
  assert.equal(api.streams[0].track.stops, 1);
  assert.match(api.errors[0].message, /falling behind/);
});

test("wake, state, and one transcript are delivered without automatically acknowledging or submitting", async () => {
  const api = harness();
  const socket = await api.start();
  socket.message(api.event("state", { state: "listening", followup_remaining_ms: 5000 }));
  socket.message(api.event("wake", { wake_phrase: "hey jarvis" }));
  const speech = api.event("speech_start", { turn_id: "turn-1", interrupt: true });
  socket.message(speech);
  socket.message(speech);
  const transcript = api.event("transcript", { turn_id: "turn-1", text: "Tell me the time" });
  socket.message(transcript);
  socket.message(transcript);
  assert.equal(api.states.at(-1).state, "listening");
  assert.equal(api.wakes.length, 1);
  assert.equal(api.speech.length, 1);
  assert.equal(api.speech[0].interrupt, true);
  assert.equal(api.transcripts.length, 1);
  assert.equal(socket.json().filter((item) => item.type === "ack").length, 0);
  assert.equal(api.client.acknowledge("turn-1", { accepted: true }), true);
  assert.deepEqual(socket.json().at(-1), { type: "ack", turn_id: "turn-1", accepted: true, context_revision: api.client.contextRevision });
  assert.equal(api.client.acknowledge("turn-1", { accepted: true }), false);
  assert.equal(api.client.acknowledge("unknown", { accepted: true }), false);
  api.client.stop();
});

test("playback updates retain a captured interruption while explicit invalidation drops stale results", async () => {
  const api = harness();
  const socket = await api.start();
  const revision = api.client.contextRevision;
  api.client.setContext({ busy: true, playback: true });
  socket.message(api.event("speech_start", { turn_id: "interrupt", interrupt: true }));
  api.client.setContext({ busy: false, playback: false });
  assert.equal(api.client.contextRevision, revision);
  socket.message(api.event("transcript", { turn_id: "interrupt", text: "Actually explain the second option" }));
  assert.equal(api.transcripts.length, 1);
  assert.equal(api.client.invalidate(), revision + 1);
  assert.equal(socket.json().at(-1).type, "reset");
  socket.message({ event: "transcript", turn_id: "late", text: "Old result", context_revision: revision });
  socket.message({ event: "speech_start", turn_id: "late", context_revision: revision });
  socket.message({ event: "state", state: "transcribing", context_revision: revision });
  assert.equal(api.transcripts.length, 1);
  assert.equal(api.speech.length, 1);
  assert.equal(api.client.acknowledge("interrupt", { accepted: true }), false);
  assert.throws(() => api.client.setContext({ revision }), /must increase/);
  api.client.stop();
});

test("results and errors from an earlier socket cannot affect a new microphone session", async () => {
  const api = harness();
  const first = await api.start();
  const oldMessage = first.onmessage;
  const oldError = first.onerror;
  const oldRevision = api.client.contextRevision;
  const second = await api.start();
  oldMessage({ data: JSON.stringify({ event: "transcript", turn_id: "old", text: "Late result", context_revision: oldRevision }) });
  oldError();
  assert.equal(api.transcripts.length, 0);
  assert.equal(api.errors.length, 0);
  assert.equal(api.client.socket, second);
  assert.equal(api.client.active, true);
  assert.equal(api.streams[0].track.stops, 1);
  assert.equal(api.streams[1].track.stops, 0);
  api.client.stop();
});

test("missing context or turn identifiers never dispatch recognitions", async () => {
  const api = harness();
  const socket = await api.start();
  socket.message({ event: "transcript", turn_id: "x", text: "No revision" });
  socket.message(api.event("transcript", { text: "No turn" }));
  socket.message(api.event("transcript", { turn_id: "empty", text: " " }));
  socket.message({ event: "speech_start", turn_id: "x" });
  assert.equal(api.transcripts.length, 0);
  assert.equal(api.speech.length, 0);
  api.client.stop();
});

test("recoverable recognition errors stay visible and fatal server errors release capture", async () => {
  const api = harness();
  const socket = await api.start();
  socket.message({ event: "error", code: "unclear", message: "Please say that again.", recoverable: true });
  assert.equal(api.client.active, true);
  assert.equal(api.errors[0].recoverable, true);
  assert.equal(api.errors[0].code, "unclear");
  socket.message({ event: "error", code: "unavailable", message: "Install the local speech model.", recoverable: false });
  assert.equal(api.client.active, false);
  assert.equal(api.errors[1].message, "Install the local speech model.");
  assert.equal(api.streams[0].track.stops, 1);
});

test("a server setup error before readiness preserves its actionable message", async () => {
  const api = harness();
  const pending = api.client.start();
  await flush();
  api.sockets[0].open();
  api.sockets[0].message({ event: "error", message: "Local Whisper is not installed.", recoverable: false });
  assert.equal(await pending, false);
  assert.equal(api.errors.length, 1);
  assert.equal(api.errors[0].message, "Local Whisper is not installed.");
  assert.equal(api.streams[0].track.stops, 1);
});

test("unsupported sample rate and invalid configuration release or avoid microphone acquisition", async () => {
  const api = harness({ sampleRate: 48000 });
  assert.equal(await api.client.start(), false);
  assert.equal(api.streams[0].track.stops, 1);
  assert.equal(api.contexts[0].closes, 1);
  assert.equal(api.sockets.length, 0);
  assert.match(api.errors[0].message, /16 kHz/);
  const invalid = harness();
  assert.equal(await invalid.client.start({ wake_phrase: "listen" }), false);
  assert.equal(invalid.requests.length, 0);
  assert.equal(invalid.timers.size, 0);
});

test("malformed server messages stop microphone capture instead of leaving a silent session", async () => {
  const api = harness();
  const socket = await api.start();
  socket.onmessage({ data: "not JSON" });
  assert.equal(api.client.active, false);
  assert.equal(api.streams[0].track.stops, 1);
  assert.equal(api.errors.length, 1);
  assert.match(api.errors[0].message, /invalid server/);
});

test("follow-up is a one-shot signal and a new microphone session clears old busy context", async () => {
  const api = harness();
  const socket = await api.start();
  api.client.setContext({ busy: false, followup: true });
  assert.equal(socket.json().at(-1).followup, true);
  api.client.setContext({ playback: false });
  assert.equal(socket.json().at(-1).followup, false);
  api.client.setContext({ busy: true, awaiting_approval: true });
  api.client.stop();
  const next = await api.start();
  assert.equal(next.json().at(-1).busy, false);
  assert.equal(next.json().at(-1).awaiting_approval, false);
  api.client.stop();
});
