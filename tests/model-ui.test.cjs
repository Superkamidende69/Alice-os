const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const vm = require("node:vm");

function harness() {
  class Element {
    constructor() { this.children = []; this.dataset = {}; this.value = ""; }
    append(...items) { this.children.push(...items); }
    add(item) { this.append(item); }
    replaceChildren(...items) { this.children = items; }
    setAttribute(name, value) { this[name] = value; }
    addEventListener() {}
  }
  const elements = new Map();
  const context = vm.createContext({
    document: {
      querySelector(selector) {
        if (!elements.has(selector)) elements.set(selector, new Element());
        return elements.get(selector);
      },
      querySelectorAll: () => [],
      createElement: () => new Element(),
      createDocumentFragment: () => new Element(),
    },
    Option: class extends Element {
      constructor(text, value) { super(); this.textContent = text; this.value = value; }
    },
    window: {}, console,
  });
  const source = readFileSync(resolve(__dirname, "../web/app.js"), "utf8");
  vm.runInContext(source.replace("  bootstrap();", "  globalThis.modelTest = { state, els, hydrateState, renderModelLibraryList };"), context);
  return { ...context.modelTest, Element };
}

test("startup renders nonempty provider profiles without a model variable", () => {
  const { hydrateState, state, els } = harness();
  hydrateState({ providers: [
    { id: "ollama", name: "Ollama", kind: "ollama", base_url: "http://localhost:11434" },
    { id: "worker", name: "Worker", kind: "cluster", base_url: "https://worker.local" },
  ], sessions: [], active_provider_id: "ollama" });
  assert.equal(state.selectedProviderId, "ollama");
  assert.equal(els.providerSelect.children.length, 2);
  const cards = els.profileList.children[0].children;
  assert.equal(cards.length, 2);
  assert.equal(cards[0].children[2].children.length, 1);
  assert.equal(cards[0].children[2].children[0]["aria-label"], "Delete Ollama");
});

test("downloaded model cards own load/use and file deletion controls", () => {
  const { renderModelLibraryList, Element } = harness();
  const container = new Element();
  renderModelLibraryList(container, [
    { name: "Ready", model_path: "ready.gguf", ready: true },
    { name: "Stored", model_path: "stored.gguf", ready: false },
    { name: "Legacy model" },
  ], "Empty", "LocalAI");
  const actions = container.children.map(card => card.children[3].children);
  assert.equal(actions[0][0].textContent, "Use model");
  assert.equal(actions[0][1].textContent, "Delete file");
  assert.equal(actions[0][1].disabled, true);
  assert.equal(actions[1][0].textContent, "Load model");
  assert.equal(actions[1][1].disabled, false);
  assert.equal(actions[2][0].textContent, "Delete model");
});
