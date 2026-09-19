const { test } = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const { readFileSync } = require("node:fs");
const voice = require("../web/voice-commands.js");
const commands = require("../web/command-center.js");

for (const scenario of ["remote", "forbidden", "unauthenticated"]) {
  test(`${scenario} access disables globe controls and stops repeated polling`, async () => {
    const nodes = new Map();
    const get = id => {
      if (!nodes.has(id)) nodes.set(id, { addEventListener() {} });
      return nodes.get(id);
    };
    let polls = 0;
    const context = vm.createContext({
      document: { getElementById: get, hidden: false, addEventListener() {} },
      window: { addEventListener() {} }, clearTimeout() {},
      setTimeout() { polls++; },
      fetch: async () => ({
        ok: scenario === "remote", status: scenario === "unauthenticated" ? 401 : 403,
        json: async () => ({ can_control: false, ready: true, access_message: "Use the host PC", detail: "Sign in on the host PC" }),
      }),
    });
    vm.runInContext(readFileSync(require.resolve("../web/world.js"), "utf8"), context);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(polls, 0);
    assert.equal(get("world-start").disabled, true);
    assert.equal(get("world-stop").disabled, true);
    assert.equal(get("world-open").hidden, true);
    assert.equal(get("world-refresh").disabled, false);
  });
}

test("voice and command palette expose World View and block leaving an active task", () => {
  assert.equal(voice.parse("Open World View"), "world");
  assert.equal(voice.parse("Open God's Eye"), "world");
  assert.equal(voice.parse("Open the globe"), "world");
  assert.ok(commands.searchCommands("globe").some(c => c.id === "world"));
  assert.ok(commands.commandBlockReason("world", true));
});

test("launch page uses authenticated actions and never opens an arbitrary status URL", async () => {
  const nodes = new Map(), calls = [];
  const get = id => {
    if (!nodes.has(id)) nodes.set(id, { events: {}, addEventListener(name, fn) { this.events[name] = fn; } });
    return nodes.get(id);
  };
  let ready = false;
  const context = vm.createContext({
    document: { getElementById: get, hidden: false, addEventListener() {} }, window: { addEventListener() {} },
    setTimeout() { return 1; }, clearTimeout() {},
    fetch: async (url, options) => {
      calls.push({ url, options });
      return { ok: true, json: async () => ({ installed: true, running: ready, ready, url: "https://untrusted.example" }) };
    },
  });
  vm.runInContext(readFileSync(require.resolve("../web/world.js"), "utf8"), context);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(get("world-start").disabled, false);
  assert.equal(get("world-open").hidden, true);
  ready = true;
  await get("world-start").events.click();
  assert.equal(calls.at(-1).options.method, "POST");
  assert.equal(calls.at(-1).options.credentials, "same-origin");
  assert.equal(get("world-open").href, "http://127.0.0.1:4173/");
  assert.equal(get("world-stop").disabled, false);
});
