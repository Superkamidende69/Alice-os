const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const vm = require("node:vm");

function harness(fetch) {
  const nodes = new Map(), sent = [], contexts = [], acknowledgements = [], commands = [];
  class Element extends EventTarget {
    constructor() { super(); this.value = ""; this.paused = true; this.checked = false; this.dataset = {}; this.style = {}; this.options = []; }
    setAttribute(name, value) { this[name] = value; }
    removeAttribute(name) { delete this[name]; }
    pause() { this.paused = true; this.dispatchEvent(new Event("pause")); }
    load() {}
    focus() {}
    querySelector(selector) { return get(selector); }
  }
  const get = (selector) => { if (!nodes.has(selector)) nodes.set(selector, new Element()); return nodes.get(selector); };
  class HandsFree {
    constructor(callbacks) { this.callbacks = callbacks; }
    setContext(context) { contexts.push(context); }
    acknowledge(turn, result) { acknowledgements.push({ turn, ...result }); }
    invalidate() { this.invalidations = (this.invalidations || 0) + 1; }
    stop(reason = "stopped") { this.callbacks.onState({ state: "off", reason }); }
    async start() {
      this.stop("restart");
      this.callbacks.onState({ state: "connecting", connecting: true });
      this.callbacks.onState({ state: "idle", active: true });
      return true;
    }
  }
  const document = Object.assign(new EventTarget(), { querySelector: get, querySelectorAll: () => [] });
  const window = Object.assign(new EventTarget(), { AliceHandsFree: HandsFree, AliceVoiceCommands: require("../web/voice-commands.js") });
  const context = vm.createContext({
    document, window, navigator: {}, Headers, FormData, Blob, AbortController,
    Event, console, setTimeout, clearTimeout,
    fetch: fetch || (async () => ({ ok: true, headers: new Headers({ "content-type": "application/json" }), json: async () => ({}) })),
  });
  const source = readFileSync(resolve(__dirname, "../web/app.js"), "utf8");
  vm.runInContext(source.replace("  bootstrap();", `
    globalThis.api = { state, els, configureHandsFree, captureHandsFreeSpeech, receiveHandsFreeTranscript,
      syncHandsFreeContext, drainHandsFreeTurn, resetHandsFreeConversation, stopHandsFree, cancelRun,
      setSubmit(fn) { submitMessage = fn; }, setToast(fn) { showToast = fn; } };
  `), context);
  const api = context.api;
  api.setToast(() => {});
  api.state.activeSessionId = "chat-1";
  api.state.backendOnline = true;
  api.state.localTranscriptionReady = true;
  api.state.selectedProviderId = "local";
  api.state.selectedModel = "test";
  api.state.speechController = { executeCommand: (command) => commands.push(command) };
  api.els.voiceWakePhrase.value = "hey jarvis";
  api.configureHandsFree();
  api.state.handsFreeEnabled = true;
  api.setSubmit(async () => {
    sent.push(api.els.composerInput.value);
    api.els.composerInput.value = "";
    api.state.activeRun = { id: "new-run", sessionId: "chat-1", agentMode: false };
  });
  return Object.assign(api, { sent, contexts, acknowledgements, commands });
}

function speech(api, text = "Tell me about the weather", interrupt = false) {
  api.captureHandsFreeSpeech({ turn_id: "turn-1", interrupt });
  return api.receiveHandsFreeTranscript({ turn_id: "turn-1", text });
}

test("recognized requests use the regular composer and continue listening only after the full reply drains", async () => {
  const api = harness();
  await speech(api);
  assert.deepEqual(api.sent, ["Tell me about the weather"]);
  assert.equal(api.acknowledgements[0].accepted, true);
  assert.equal(api.contexts.some((item) => item.awaiting_approval), false);
  assert.equal(api.contexts.some((item) => item.followup), false);
  api.state.activeRun = null;
  api.state.voiceConversation = { textQueue: [], audioQueue: [], synthesisActive: true };
  api.syncHandsFreeContext();
  assert.equal(api.contexts.at(-1).busy, true);
  api.state.voiceConversation.synthesisActive = false;
  api.state.voiceConversation.audioQueue.push({ url: "/next.wav" });
  api.syncHandsFreeContext();
  assert.equal(api.contexts.at(-1).busy, true);
  api.state.voiceConversation.audioQueue.length = 0;
  api.syncHandsFreeContext();
  assert.equal(api.contexts.at(-1).followup, true);
  api.syncHandsFreeContext();
  assert.equal(api.contexts.at(-1).followup, undefined);
});

test("typing during recognition preserves both texts and requires review", async () => {
  const api = harness();
  api.captureHandsFreeSpeech({ turn_id: "turn-1", interrupt: false });
  api.els.composerInput.value = "My carefully typed draft";
  await api.receiveHandsFreeTranscript({ turn_id: "turn-1", text: "My spoken message" });
  assert.equal(api.els.composerInput.value, "My carefully typed draft");
  assert.equal(api.state.handsFreePending.text, "My spoken message");
  assert.equal(api.sent.length, 0);
  api.els.handsFreeReview.dispatchEvent(new Event("click"));
  assert.equal(api.els.composerInput.value, "My carefully typed draft\nMy spoken message");
  assert.equal(api.state.handsFreePending, null);
});

test("new voice agent requests require transcript review even without a running task", async () => {
  const api = harness();
  api.els.agentMode.checked = true;
  await speech(api, "Delete my project");
  assert.equal(api.sent.length, 0);
  assert.equal(api.state.handsFreePending.autoSend, false);
  assert.equal(api.acknowledgements.at(-1).accepted, false);
});

test("workspace barge-in stops speech, preserves the run and holds the follow-up for review", async () => {
  const api = harness(() => { throw new Error("Must not cancel a workspace task"); });
  const run = { id: "work", agentMode: true };
  api.state.activeRun = run;
  api.els.voicePlayer.paused = false;
  await speech(api, "Here is an extra detail", true);
  assert.equal(api.els.voicePlayer.paused, true);
  assert.equal(api.state.activeRun, run);
  assert.equal(api.state.handsFreePending.autoSend, false);
  assert.equal(api.sent.length, 0);
});

test("chat interruptions queue until cancellation settles without a late cancel clearing the next run", async () => {
  let finishCancel;
  const api = harness(() => new Promise((resolve) => { finishCancel = () => resolve({ ok: true, headers: new Headers({ "content-type": "application/json" }), json: async () => ({}) }); }));
  api.state.activeRun = { id: "old", agentMode: false };
  await speech(api, "Let me rephrase that", true);
  assert.equal(api.state.handsFreePending.autoSend, true);
  assert.equal(api.sent.length, 0);
  api.state.activeRun = null; // cancelled SSE settles before the cancel HTTP response
  await api.drainHandsFreeTurn();
  assert.deepEqual(api.sent, ["Let me rephrase that"]);
  finishCancel();
  for (let index = 0; index < 12; index += 1) await Promise.resolve();
  assert.equal(api.state.activeRun.id, "new-run");
});

test("session switches and stopping listening discard stale recognized turns", async () => {
  const api = harness();
  api.captureHandsFreeSpeech({ turn_id: "turn-1" });
  api.resetHandsFreeConversation();
  api.state.activeSessionId = "chat-2";
  await api.receiveHandsFreeTranscript({ turn_id: "turn-1", text: "Old conversation" });
  assert.equal(api.sent.length, 0);
  api.captureHandsFreeSpeech({ turn_id: "turn-2" });
  api.stopHandsFree();
  await api.receiveHandsFreeTranscript({ turn_id: "turn-2", text: "Stopped session" });
  assert.equal(api.sent.length, 0);
  assert.equal(api.state.handsFreePending, null);
});

test("voice does not approve tools and capture pauses for an on-screen approval", async () => {
  const api = harness();
  api.state.activeRun = { id: "work", agentMode: true };
  api.state.toolCards.set("tool", { dataset: { runId: "work", state: "approval" } });
  api.syncHandsFreeContext();
  assert.equal(api.contexts.at(-1).awaiting_approval, true);
  await speech(api, "yes approve");
  assert.equal(api.sent.length, 0);
  assert.equal(api.commands.length, 0);
  assert.equal(api.state.handsFreePending, null);
});

test("starting remains enabled across transport cleanup and hidden-page stop requires a fresh click", async () => {
  const api = harness();
  api.state.handsFreeEnabled = false;
  api.els.handsFreeToggle.dispatchEvent(new Event("click"));
  for (let index = 0; index < 12; index += 1) await Promise.resolve();
  assert.equal(api.state.handsFreeEnabled, true);
  assert.equal(api.els.handsFreeToggle["aria-pressed"], "true");
  api.state.handsFree.stop("page_hidden");
  assert.equal(api.state.handsFreeEnabled, false);
  assert.match(api.els.handsFreeStatus.textContent, /hidden/);
});
