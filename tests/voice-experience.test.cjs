const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const vm = require("node:vm");
const {speechText} = require("../web/voice-experience.js");

test("spoken text skips fenced code across phrases and cleans Markdown without changing prose", () => {
  const state = {};
  assert.equal(speechText("## Here is **the answer**. [Read more](https://example.com)", state), "Here is the answer. Read more");
  assert.equal(speechText("```python\nprint('private code')", state), "Code is shown in the conversation.");
  assert.equal(speechText("more code\n", state), "");
  assert.equal(speechText("```\nThis is the explanation.", state), "This is the explanation.");
  assert.equal(speechText("There are 3.14 units, not 5."), "There are 3.14 units, not 5.");
});

function harness() {
  const elements = new Map(), store = new Map(), timers = new Map();
  let resolveStream, timerId = 0;
  class Element extends EventTarget {
    constructor() { super(); this.value = ""; this.options = []; }
    setAttribute(name, value) { this[name] = value; }
    replaceChildren(...children) { this.options = children; }
    add(option) { this.options.push(option); }
  }
  const document = Object.assign(new EventTarget(), {hidden: false, getElementById(id) {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  }});
  const window = Object.assign(new EventTarget(), {document,
    localStorage: {getItem: key => store.get(key) ?? null, setItem: (key,value) => store.set(key,value)},
    navigator: {mediaDevices: {enumerateDevices: async () => [{kind:"audioinput",deviceId:"mic-1",label:"Desk microphone"}],
      getUserMedia: () => new Promise(resolve => { resolveStream = resolve; })}},
    cancelAnimationFrame() {}, requestAnimationFrame() {return 1;},
  });
  const context = vm.createContext({window, Event, console, Float32Array, Option: class {constructor(label,value){this.label=label;this.value=value;}},
    setTimeout(fn) {timers.set(++timerId,fn);return timerId;}, clearTimeout(id) {timers.delete(id);}});
  vm.runInContext(readFileSync(require.resolve("../web/voice-experience.js"), "utf8"),context);
  document.dispatchEvent(new Event("DOMContentLoaded"));
  return {api:window.AliceVoiceExperience, document, window, store, timers, get:id=>document.getElementById(id),
    resolve: value => resolveStream(value)};
}

test("device and volume preferences preserve deliberate zero and exact input choice", () => {
  const h = harness();
  h.get("voice-volume").value = "0";
  h.get("voice-volume").dispatchEvent(new Event("input"));
  assert.equal(h.api.volume(),0);
  assert.equal(h.get("voice-player").volume,0);
  h.get("voice-input-device").value="mic-1";
  h.get("voice-noise-filter").checked=false;
  h.get("voice-input-device").dispatchEvent(new Event("change"));
  assert.equal(h.api.audioConstraints().deviceId.exact,"mic-1");
  assert.equal(h.api.audioConstraints().noiseSuppression,false);
  assert.equal(h.api.audioConstraints().echoCancellation,true);
});

test("stopping a pending microphone test reclaims late permission results without opening audio", async () => {
  const h = harness();
  h.get("voice-test-mic").dispatchEvent(new Event("click"));
  h.get("voice-test-mic").dispatchEvent(new Event("click"));
  let stopped=0;
  h.resolve({getTracks:()=>[{stop(){stopped++;}}]});
  for (let index=0; index<12; index++) await Promise.resolve();
  assert.equal(stopped,1);
  assert.equal(h.timers.size,0);
  assert.equal(h.get("voice-test-mic")["aria-pressed"],"false");
});

test("hiding the page cancels the microphone test and its deadline", () => {
  const h=harness();
  h.get("voice-test-mic").dispatchEvent(new Event("click"));
  h.document.hidden=true;
  h.document.dispatchEvent(new Event("visibilitychange"));
  assert.equal(h.timers.size,0);
  assert.equal(h.get("voice-test-mic")["aria-pressed"],"false");
  assert.match(h.get("voice-mic-test-status").textContent,/hidden/);
});
