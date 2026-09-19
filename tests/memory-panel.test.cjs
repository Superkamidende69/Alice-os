const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const vm = require("node:vm");

function panel() {
  const nodes = new Map(), requests = [];
  class Element {
    constructor() { this.value = ""; this.children = []; this.events = {}; this.style = {}; this.dataset = {}; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(name, handler) { this.events[name] = handler; }
    querySelector(selector) { return get(selector); }
    reset() { get("#memory-input").value = ""; get("#memory-category").value = "fact"; }
    focus() { this.focused = true; }
  }
  const get = selector => { if (!nodes.has(selector)) nodes.set(selector, new Element()); return nodes.get(selector); };
  const document = { querySelector: get, querySelectorAll: () => [], createElement: () => new Element() };
  const context = vm.createContext({ document, window: { AliceMemory: require("../web/memory.js") }, navigator: {}, console });
  const source = readFileSync(require.resolve("../web/app.js"), "utf8");
  vm.runInContext(source.replace("  bootstrap();", `globalThis.panel = { renderMemories, saveMemory, setApi(fn) { api = fn; } };`), context);
  context.panel.setApi(async (path, options) => {
    requests.push({ path, options });
    return { memories: [] };
  });
  return { ...context.panel, get, requests };
}

test("memory review renders text safely and edits a pending entry without approving it", async () => {
  const p = panel();
  p.renderMemories([{ id: "pending-1", content: "<img onerror=alert(1)>", category: "project", approved: 0, created_at: "2026-09-15" }]);
  const card = p.get("#memory-list").children[0];
  assert.equal(card.children[0].children[0].textContent, "<img onerror=alert(1)>");
  const actions = card.children[1].children;
  assert.deepEqual(actions.map(b => b.textContent), ["Approve", "Edit", "Dismiss"]);
  actions[1].events.click();
  assert.equal(p.get("#memory-input").value, "<img onerror=alert(1)>");
  p.get("#memory-input").value = "Finish voice tests";
  await p.saveMemory({ preventDefault() {} });
  assert.equal(p.requests[0].options.method, "PATCH");
  assert.equal(p.requests[0].options.body.category, "project");
  assert.equal(p.requests.some(r => r.path.endsWith("/approve")), false);
});

test("approval is explicit and failed writes preserve the user's draft", async () => {
  const p = panel();
  p.renderMemories([{ id: "pending-2", content: "Short answers", category: "preference", approved: 0, created_at: "2026-09-15" }]);
  await p.get("#memory-list").children[0].children[1].children[0].events.click();
  assert.equal(p.requests[0].path, "/api/memories/pending-2/approve");
  p.setApi(async () => { throw new Error("Offline"); });
  p.get("#memory-input").value = "Keep this draft";
  await p.saveMemory({ preventDefault() {} });
  assert.equal(p.get("#memory-input").value, "Keep this draft");
  assert.equal(p.get("#memory-message").textContent, "Offline");
  assert.equal(p.get('[type="submit"]').disabled, false);
});
