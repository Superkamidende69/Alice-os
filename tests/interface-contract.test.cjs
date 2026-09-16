const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");

const html = readFileSync(resolve(__dirname, "../web/index.html"), "utf8");
const source = readFileSync(resolve(__dirname, "../web/app.js"), "utf8");
test("every named app element exists in the real markup, with unique IDs", () => {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length, "Duplicate DOM IDs");
  const required = [...source.matchAll(/\w+:\s*\$\("#([^"]+)"\)/g)].map(match => match[1]);
  assert.deepEqual(required.filter(id => !ids.includes(id)), []);
});
test("chat has exactly one navigation entry for each settings destination", () => {
  const shell = html.slice(html.indexOf('id="app-shell"'), html.indexOf('<dialog class="command-center-dialog"'));
  for (const path of ["/models", "/voice"]) {
    assert.equal(shell.split('href="' + path + '"').length - 1, 1);
  }
  assert.ok(html.includes('id="startup-status"'));
  assert.ok(html.includes('/static/interface.js?'));
});
