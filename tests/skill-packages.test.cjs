const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const vm = require("node:vm");

function panel({ issues = [], enabled = false, installed = false, fail = false } = {}) {
  const nodes = new Map(), requests = [];
  class Element {
    constructor() { this.value = ""; this.children = []; this.events = {}; this.style = {}; this.dataset = {}; }
    append(...items) { this.children.push(...items); }
    add(item) { this.append(item); }
    replaceChildren(...items) { this.children = items; }
    get firstChild() { return this.children[0]; }
    addEventListener(name, fn) { this.events[name] = fn; }
    closest() { return get("details"); }
    focus() { this.focused = true; }
    setAttribute() {}
  }
  const get = name => { if (!nodes.has(name)) nodes.set(name, new Element()); return nodes.get(name); };
  const manifest = {schema_version: 1, id: "reader", name: "<img onerror=bad()>", version: "1.0.0", description: "Read files", instructions: "Inspect", tools: ["workspace_read"], requires: [], read_only: true};
  const entry = () => ({...manifest, issues, enabled, available: enabled && !issues.length, packaged: true});
  const context = vm.createContext({
    document: {querySelector: get, querySelectorAll: () => [], createElement: () => new Element()},
    window: {localStorage: {getItem: () => "reader"}, location: {pathname: "/"}}, navigator: {}, console,
    Headers, FormData, Option: function(text, value) { this.textContent = text; this.value = value; },
    fetch: async (path, init) => {
      requests.push({path, init});
      let body = {};
      if (init.method === "POST" || init.method === "PATCH") {
        assert.equal(init.headers.get("Content-Type"), "application/json");
        const data = JSON.parse(init.body);
        if (init.method === "POST") { installed = true; enabled = false; }
        else enabled = data.enabled;
      }
      if (init.method === "DELETE") installed = false;
      if (path === "/api/skill-packages") body = {packages: installed ? [entry()] : [], templates: [manifest]};
      if (path === "/api/skills") body = {skills: [{id: "general", name: "General", description: "General"}, ...(installed ? [entry()] : [])]};
      if (path.endsWith("/manifest")) body = manifest;
      return {status: fail ? 500 : 200, ok: !fail, headers: new Headers({"Content-Type": "application/json"}), json: async () => fail ? {detail: "Offline"} : body};
    }
  });
  const source = readFileSync(require.resolve("../web/app.js"), "utf8");
  vm.runInContext(source.replace("  bootstrap();", "globalThis.panel = { loadSkillPackages, loadSkills };"), context);
  return {...context.panel, get, requests};
}

test("package install, enable, export and remove use the real JSON request wrapper", async () => {
  const p = panel();
  await p.loadSkillPackages();
  const starter = p.get("#skill-package-templates").children[0];
  assert.equal(starter.children[0].children[0].textContent, "<img onerror=bad()> · 1.0.0");
  await starter.children[1].events.click();
  let row = p.get("#skill-package-list").children[0];
  assert.equal(row.children[1].children[0].textContent, "Enable");
  assert.equal(p.get("#skill-select").children[1].disabled, true);
  await row.children[1].children[0].events.click();
  row = p.get("#skill-package-list").children[0];
  assert.equal(row.children[1].children[0].textContent, "Disable");
  assert.equal(p.get("#skill-select").children[1].disabled, false);
  await row.children[1].children[1].events.click();
  assert.equal(JSON.parse(p.get("#skill-package-manifest").value).id, "reader");
  assert.equal(p.get("details").open, true);
  row = p.get("#skill-package-list").children[0];
  await row.children[1].children[2].events.click();
  assert.equal(p.get("#skill-select").children.length, 1);
});

test("missing dependencies prevent activation but allow an enabled package to be disabled", async () => {
  for (const enabled of [false, true]) {
    const p = panel({installed: true, issues: ["Missing git"], enabled});
    await p.loadSkillPackages();
    const row = p.get("#skill-package-list").children[0];
    assert.match(row.children[0].children[4].textContent, /Missing git/);
    assert.equal(row.children[1].children[0].disabled, !enabled);
  }
});
