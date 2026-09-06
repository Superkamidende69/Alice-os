const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const vm = require("node:vm");

function harness(fetch) {
  const elements = new Map();
  class Element extends EventTarget {
    constructor() { super(); this.checked = true; this.paused = true; this.value = "1"; }
    pause() { this.paused = true; this.dispatchEvent(new Event("pause")); }
    load() {}
    removeAttribute(name) { delete this[name]; }
    play() { this.paused = false; return Promise.resolve(); }
  }
  const element = (selector) => {
    if (!elements.has(selector)) elements.set(selector, new Element());
    return elements.get(selector);
  };
  const context = vm.createContext({
    document: { querySelector: element, querySelectorAll: () => [] },
    window: {}, crypto: globalThis.crypto, Headers, FormData, AbortController,
    fetch: fetch || (async () => ({ ok: true, status: 200, headers: new Headers({ "content-type": "application/json" }), json: async () => ({}) })),
    console, Event, setTimeout, clearTimeout,
  });
  const source = readFileSync(resolve(__dirname, "../web/app.js"), "utf8");
  vm.runInContext(source.replace("  bootstrap();", "  globalThis.voiceTest = { state, els, voiceChunks, stopVoiceConversation, synthesizeVoiceQueue, playVoiceSegment };"), context);
  return context.voiceTest;
}

function conversation() {
  return { bufferedText: "", textQueue: [], audioQueue: [], cancelled: false, synthesisActive: false, reportedError: false };
}

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
