const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const vm = require("node:vm");

function harness(info) {
  const nodes = new Map();
  class Element {
    constructor() { this.value = ""; this.options = []; this.children = []; this.dataset = {}; this.style = {}; }
    add(option) { option.parent = this; this.options.push(option); }
    append(...items) { this.children.push(...items); }
    replaceChildren(...items) { this.children = items; }
    addEventListener() {}
    setAttribute() {}
  }
  class Option {
    constructor(text, value) { this.text = text; this.value = value; }
    remove() { this.parent.options = this.parent.options.filter(option => option !== this); }
  }
  const get = id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
  const requests = [];
  const context = vm.createContext({
    document: {querySelector: get, querySelectorAll: () => [], createElement: () => new Element()},
    window: {}, navigator: {}, console, Headers, FormData, Option,
    fetch: async path => { requests.push(path); return {ok: true, status: 200, headers: new Headers({"content-type":"application/json"}), json: async () => info}; }
  });
  const source = readFileSync(require.resolve("../web/app.js"), "utf8");
  vm.runInContext(source.replace("  bootstrap();", "globalThis.test = { loadVoicebox, updateVoiceControlAvailability, voiceSynthesisBody, warmVoiceEngine, voiceChunks, els, state };"), context);
  get("#voice-speaker").add(new Option("OpenVoice", "OPENVOICE-FEMALE"));
  return {...context.test, get, requests};
}

test("Voicebox discovery uses text labels and preserves the current voice", async () => {
  const p = harness({ready:true, installed:true, can_start:true, message:"Connected", profiles:[{id:"test-profile",name:"<img onerror=bad()>",engine:"kokoro"}]});
  p.els.voiceSpeaker.value = "OPENVOICE-FEMALE";
  await p.loadVoicebox();
  assert.equal(p.els.voiceSpeaker.value, "OPENVOICE-FEMALE");
  assert.equal(p.els.voiceSpeaker.options[1].text, "Voicebox · <img onerror=bad()> · kokoro");
  assert.equal(p.els.voiceboxStart.disabled, true);
});

test("an offline Voicebox profile remains selected without falling back or leaking a clone reference", async () => {
  const p = harness({ready:false, installed:true, can_start:false, profiles:[], message:"Offline"});
  p.els.voiceSpeaker.value = "VOICEBOX:saved-profile";
  p.els.voiceReferenceSelect.value = "old-openvoice-reference.wav";
  await p.loadVoicebox();
  assert.equal(p.els.voiceSpeaker.value, "VOICEBOX:saved-profile");
  assert.match(p.els.voiceSpeaker.options[1].text, /unavailable/);
  assert.equal(p.voiceSynthesisBody("Hello").reference, "");
  assert.equal(p.els.voiceSpeed.disabled, true);
  assert.equal(p.els.voiceStyle.disabled, true);
  assert.equal(p.els.voiceboxStudio.disabled, true);
  p.els.voiceSpeaker.value = "OPENVOICE-FEMALE";
  p.updateVoiceControlAvailability();
  assert.equal(p.els.voiceSpeed.disabled, false);
  assert.equal(p.els.voiceStyle.disabled, false);
});

test("Voicebox keeps complete phrases and does not warm OpenVoice", async () => {
  const p = harness({});
  p.els.voiceSpeaker.value = "VOICEBOX:profile";
  p.state.backendOnline = true;
  await p.warmVoiceEngine();
  assert.equal(p.requests.length, 0);
  const sentence = "Here is a longer thought, with a natural pause in the middle, and enough context to keep the sentence flowing right through to its conclusion.";
  const turn = {bufferedText: sentence + " Next", textQueue:[], audioQueue:[], cancelled:false};
  p.voiceChunks(turn);
  assert.equal(turn.textQueue[0], sentence);
});
