const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const vm = require("node:vm");

function harness(fetch, options = {}) {
  const elements = new Map();
  class Element extends EventTarget {
    constructor() { super(); this.checked = true; this.paused = true; this.value = "1"; this.style = {}; this.dataset = {}; this.scrollHeight = 20; this.clicks = 0; this.submissions = 0; }
    pause() { this.paused = true; this.dispatchEvent(new Event("pause")); }
    load() {}
    removeAttribute(name) { delete this[name]; }
    play() { this.paused = false; return Promise.resolve(); }
    setAttribute(name, value) { this[name] = value; }
    querySelector(selector) { return element(selector); }
    focus() {}
    click() { this.clicks += 1; this.dispatchEvent(new Event("click")); }
    requestSubmit() { this.submissions += 1; }
  }
  const element = (selector) => {
    if (!elements.has(selector)) elements.set(selector, new Element());
    return elements.get(selector);
  };
  const document = Object.assign(new EventTarget(), { querySelector: element, querySelectorAll: () => [], documentElement: { lang: "en-US" }, hidden: false });
  const timers = new Map();
  let timerId = 0;
  const schedule = (fn, delay) => { timers.set(++timerId, { fn, delay }); return timerId; };
  const window = Object.assign(new EventTarget(), { AliceVoiceCommands: require("../web/voice-commands.js"), ...options.window });
  const context = vm.createContext({
    document, window, navigator: options.navigator || {}, crypto: globalThis.crypto, Headers, FormData, Blob, AbortController,
    fetch: fetch || (async () => ({ ok: true, status: 200, headers: new Headers({ "content-type": "application/json" }), json: async () => ({}) })),
    console, Event, setTimeout: options.fakeTimers ? schedule : setTimeout, clearTimeout: options.fakeTimers ? (id) => timers.delete(id) : clearTimeout,
  });
  const source = readFileSync(resolve(__dirname, "../web/app.js"), "utf8");
  vm.runInContext(source.replace("  bootstrap();", "  globalThis.voiceTest = { state, els, voiceChunks, stopVoiceConversation, synthesizeVoiceQueue, playVoiceSegment, configureSpeechRecognition, cancelRun, resumeVoiceQueueAfterManualPlayback, syncHandsFreeContext };"), context);
  return Object.assign(context.voiceTest, { timers, document });
}

function conversation() {
  return { bufferedText: "", textQueue: [], audioQueue: [], cancelled: false, synthesisActive: false, reportedError: false };
}

test("Kokoro keeps a complete phrase and closing quotes in the same speech chunk", () => {
  const api = harness();
  api.els.voiceSpeaker.value = "KOKORO-HEART";
  const turn = conversation();
  const sentence = "Here is a longer thought, with a natural pause in the middle, and enough context to keep the sentence flowing right through to its conclusion.";
  turn.bufferedText = sentence + ' She said "ready." Next';
  api.voiceChunks(turn);
  assert.equal(turn.textQueue[0], sentence);
  assert.equal(turn.textQueue[1], 'She said "ready."');
});

test("manual playback of the last blocked clip releases follow-up listening", async () => {
  const api = harness();
  const contexts = [];
  const turn = conversation();
  turn.autoplayBlocked = true;
  turn.pausedEntry = {url: "/last.wav"};
  api.state.voiceConversation = turn;
  api.state.handsFreeEnabled = true;
  api.state.handsFreeNeedsFollowup = true;
  api.state.handsFree = { setContext: context => contexts.push(context) };
  api.syncHandsFreeContext();
  assert.equal(contexts.at(-1).busy, true);
  assert.equal(contexts.at(-1).followup, undefined);
  api.resumeVoiceQueueAfterManualPlayback();
  assert.equal(turn.autoplayBlocked, false);
  assert.equal(turn.pausedEntry, null);
  assert.equal(contexts.some(context => context.followup), true);
});

test("the first spoken chunk becomes available before 240 unpunctuated characters", () => {
  const api = harness();
  const turn = conversation();
  turn.bufferedText = "A useful spoken answer without any punctuation ".repeat(4);
  api.voiceChunks(turn);
  assert.equal(turn.textQueue.length, 1);
  assert.ok(turn.textQueue[0].length <= 120);
});

test("speech chunks preserve text and bound punctuation-free replies", () => {
  const api = harness();
  const turn = conversation();
  const text = "Dr. Smith can help. " + "a long explanation with no punctuation ".repeat(40);
  for (const token of text.match(/.{1,7}/g)) {
    turn.bufferedText += token;
    api.voiceChunks(turn);
  }
  api.voiceChunks(turn, true);
  assert.ok(turn.textQueue.every((chunk) => chunk.length <= 240));
  assert.equal(turn.textQueue[0], "Dr. Smith can help.");
  assert.equal(turn.textQueue.join(" "), text.trim());
});

test("interruption clears queued audio and rejects a late synthesis response", async () => {
  let finishRequest;
  let cancellation;
  const api = harness(async (path, options) => {
    if (path.endsWith("/cancel")) cancellation = JSON.parse(options.body).request_id;
    const response = { ok: true, status: 200, headers: new Headers({ "content-type": "application/json" }), json: async () => ({ url: "/late.wav" }) };
    if (path.endsWith("/synthesize")) return new Promise((resolve) => { finishRequest = () => resolve(response); });
    return response;
  });
  const turn = conversation();
  turn.textQueue.push("Hello there.", "This must not be spoken.");
  api.state.voiceConversation = turn;
  const pending = api.synthesizeVoiceQueue(turn);
  const requestId = turn.requestId;
  api.stopVoiceConversation();
  finishRequest();
  await pending;
  assert.equal(cancellation, requestId);
  assert.equal(turn.cancelled, true);
  assert.equal(turn.textQueue.length, 0);
  assert.equal(turn.audioQueue.length, 0);
  assert.equal(api.els.voicePlayer.src, undefined);
});

test("playback cancellation during a pending play promise cannot hang or resume", async () => {
  const api = harness();
  const turn = conversation();
  api.state.voiceConversation = turn;
  let started;
  api.els.voicePlayer.play = () => new Promise((resolve) => { started = resolve; });
  const playing = api.playVoiceSegment(turn, "/speech.wav");
  api.stopVoiceConversation();
  started();
  assert.equal(await playing, false);
  assert.equal(turn.finishPlayback, null);
});

test("synthesis stops buffering when two clips are ready", async () => {
  let requests = 0;
  const api = harness(async () => { requests += 1; throw new Error("Unexpected request"); });
  const turn = conversation();
  turn.textQueue.push("Wait until playback consumes a clip.");
  turn.audioQueue.push("/one.wav", "/two.wav");
  await api.synthesizeVoiceQueue(turn);
  assert.equal(requests, 0);
  assert.equal(turn.textQueue.length, 1);
});

test("audio worklet emits little-endian bounded PCM packets", () => {
  let Processor;
  const packets = [];
  const context = vm.createContext({
    AudioWorkletProcessor: class { constructor() { this.port = { postMessage: (packet) => packets.push(packet.slice(0)) }; } },
    registerProcessor: (_, value) => { Processor = value; },
  });
  vm.runInContext(readFileSync(resolve(__dirname, "../web/voice-capture.js"), "utf8"), context);
  const processor = new Processor();
  const samples = new Float32Array(960);
  samples[0] = -2; samples[1] = 2; samples[2] = 0.5;
  processor.process([[samples]]);
  assert.equal(packets.length, 1);
  assert.equal(packets[0].byteLength, 1920);
  const view = new DataView(packets[0]);
  assert.equal(view.getInt16(0, true), -32768);
  assert.equal(view.getInt16(2, true), 32767);
  assert.equal(view.getInt16(4, true), 16384);
});

function dispatch(target, type, properties = {}) {
  const event = new Event(type);
  Object.assign(event, properties);
  target.dispatchEvent(event);
}

function browserVoiceHarness() {
  const recognizers = [];
  class Recognition extends EventTarget {
    constructor() { super(); recognizers.push(this); this.starts = 0; }
    start() { this.starts += 1; dispatch(this, "start"); }
    stop() {}
    abort() { dispatch(this, "end"); }
  }
  const api = harness(null, { fakeTimers: true, window: { SpeechRecognition: Recognition } });
  api.els.composerInput.value = "";
  api.state.selectedProviderId = "local";
  api.state.selectedModel = "test-model";
  api.configureSpeechRecognition();
  return Object.assign(api, { recognizers });
}

function speech(recognition, text, final = true) {
  const result = [{ transcript: text }];
  result.isFinal = final;
  dispatch(recognition, "result", { resultIndex: 0, results: [result] });
}

test("wake recognition restarts after a natural end and stops after denial", () => {
  const api = browserVoiceHarness();
  const wake = api.recognizers[0];
  assert.equal(wake.starts, 0, "never activate a saved microphone preference on page load");
  api.els.voiceWakeWord.checked = true;
  dispatch(api.els.voiceWakeWord, "change");
  assert.equal(wake.starts, 1);
  dispatch(wake, "end");
  const scheduled = [...api.timers.values()][0];
  assert.equal(scheduled.delay, 350);
  scheduled.fn();
  assert.equal(wake.starts, 2);
  dispatch(wake, "error", { error: "not-allowed" });
  assert.equal(api.els.voiceWakeWord.checked, false);
  assert.equal(api.timers.size, 0);
  assert.match(api.els.voiceInputStatus.textContent, /denied/);
  api.state.speechController.dispose();
});

test("wake commands require the selected phrase and never submit approvals", () => {
  const api = browserVoiceHarness();
  api.els.voiceWakePhrase.value = "hey jarvis";
  api.els.voiceWakeWord.checked = true;
  dispatch(api.els.voiceWakeWord, "change");
  speech(api.recognizers[0], "Hey Alice open settings");
  assert.equal(api.els.openSettings.clicks, 0);
  speech(api.recognizers[0], "Hey Jarvis open settings");
  assert.equal(api.els.openSettings.clicks, 1);
  api.state.speechController.start({ text: "approve all tools", autoSend: false });
  assert.equal(api.els.composerInput.value, "approve all tools");
  assert.equal(api.els.composerForm.submissions, 0);
  api.state.speechController.dispose();
});

test("wake requests remain drafts by default and auto-send never includes an existing draft", () => {
  const api = browserVoiceHarness();
  api.els.voiceWakeWord.checked = true;
  dispatch(api.els.voiceWakeWord, "change");
  speech(api.recognizers[0], "Hey Alice Explain orbital mechanics");
  assert.equal(api.els.composerInput.value, "Explain orbital mechanics");
  assert.equal(api.els.composerForm.submissions, 0);
  api.state.speechController.start({ text: "Add this detail", autoSend: true });
  assert.equal(api.els.composerForm.submissions, 0);
  api.els.composerInput.value = "";
  api.state.speechController.start({ text: "A fresh question", autoSend: true });
  assert.equal(api.els.composerForm.submissions, 1);
  api.state.speechController.dispose();
});

test("chat wake toggle enables the saved phrase and releases listening on disable", () => {
  const api = browserVoiceHarness();
  assert.equal(api.els.voiceWakeWord.checked, false);
  dispatch(api.els.voiceWakeToggle, "click");
  assert.equal(api.els.voiceWakeWord.checked, true);
  assert.equal(api.els.voiceWakeToggle.textContent, "Wake on");
  assert.equal(api.recognizers[0].starts, 1);
  dispatch(api.els.voiceWakeToggle, "click");
  assert.equal(api.els.voiceWakeWord.checked, false);
  assert.equal(api.els.voiceWakeToggle.textContent, "Wake off");
  assert.equal(api.timers.size, 0);
  api.state.speechController.dispose();
});

test("a draft edited during browser dictation is preserved without submission", () => {
  const api = browserVoiceHarness();
  api.state.speechController.start({ autoSend: true });
  const recognition = api.recognizers[1];
  speech(recognition, "initial", false);
  api.els.composerInput.value = "My edited draft";
  speech(recognition, "final transcript");
  dispatch(recognition, "end");
  assert.equal(api.els.composerInput.value, "My edited draft");
  assert.equal(api.els.composerForm.submissions, 0);
  assert.match(api.els.voiceInputStatus.textContent, /preserved/);
  api.state.speechController.dispose();
});

function localVoiceHarness(fetch, getUserMedia) {
  const recordings = [];
  const track = Object.assign(new EventTarget(), { stops: 0, stop() { this.stops += 1; } });
  const stream = { getTracks: () => [track] };
  class Recorder extends EventTarget {
    constructor() { super(); this.state = "inactive"; this.mimeType = "audio/webm"; recordings.push(this); }
    start() { this.state = "recording"; dispatch(this, "start"); }
    stop() { this.state = "inactive"; dispatch(this, "dataavailable", { data: new Blob(["audio"]) }); dispatch(this, "stop"); }
  }
  const api = harness(fetch, { fakeTimers: true, window: { MediaRecorder: Recorder }, navigator: { mediaDevices: { getUserMedia: getUserMedia || (async () => stream) } } });
  api.els.composerInput.value = "";
  api.state.localTranscriptionReady = true;
  api.configureSpeechRecognition();
  return Object.assign(api, { recordings, stream, track });
}

const flush = async () => { for (let i = 0; i < 8; i += 1) await Promise.resolve(); };
const jsonResponse = (data) => ({ ok: true, headers: new Headers({ "content-type": "application/json" }), json: async () => data });

test("local transcription works without browser SpeechRecognition", async () => {
  const api = localVoiceHarness(async () => jsonResponse({ text: "Locally transcribed message" }));
  assert.equal(api.els.voiceButton.disabled, false);
  assert.equal(api.els.voiceWakeWord.disabled, true);
  api.state.speechController.start();
  await flush();
  assert.equal(api.recordings.length, 1);
  api.state.speechController.stop();
  await flush();
  assert.equal(api.els.composerInput.value, "Locally transcribed message");
  assert.equal(api.state.listening, false);
  assert.ok(api.track.stops > 0);
  api.state.speechController.dispose();
});

test("releasing before microphone permission resolves cannot leave recording active", async () => {
  let grant;
  const api = localVoiceHarness(null, () => new Promise((resolve) => { grant = resolve; }));
  api.state.speechController.start();
  api.state.speechController.stop();
  assert.equal(api.state.listening, false);
  grant(api.stream);
  await flush();
  assert.equal(api.track.stops, 1);
  assert.equal(api.recordings.length, 0);
  api.state.speechController.dispose();
});

test("cancelled local transcription cannot overwrite a later draft", async () => {
  let complete;
  let signal;
  const api = localVoiceHarness((_, options) => { signal = options.signal; return new Promise((resolve) => { complete = resolve; }); });
  api.state.speechController.start();
  await flush();
  api.state.speechController.stop();
  await flush();
  api.state.speechController.cancel();
  api.els.composerInput.value = "Keep this new draft";
  complete(jsonResponse({ text: "Old transcription" }));
  await flush();
  assert.equal(signal.aborted, true);
  assert.equal(api.els.composerInput.value, "Keep this new draft");
  assert.equal(api.state.listening, false);
  api.state.speechController.dispose();
});

test("cancellation while a run is starting is queued", async () => {
  const api = harness();
  api.state.activeRun = { id: "", pending: true };
  await api.cancelRun();
  assert.equal(api.state.activeRun.cancelRequested, true);
  assert.equal(api.els.stopButton.disabled, true);
});
