const { test } = require("node:test");
const assert = require("node:assert/strict");
const memory = require("../web/memory.js");
const voice = require("../web/voice-commands.js");

test("explicit memory commands support dictation without capturing quoted text", () => {
  for (const text of ["Remember that I prefer short answers.", "Hey Alice, remember project: build Alice", "Forget my preferred editor.", "What were we working on?", "What do you remember about me?", "Recall my projects"]) {
    assert.equal(memory.isCommand(text), true, text);
  }
  for (const text of ['She said remember this', '"Forget my name"', 'Do you remember that film?', 'Write a remember function']) {
    assert.equal(memory.isCommand(text), false, text);
  }
  assert.equal(voice.parse("Open memory"), "memory");
});

test("review filtering preserves pending status and searches safely", () => {
  const entries = [{ content: "Voice project", category: "project", approved: 1 }, { content: "Short answers", category: "preference", approved: 0 }];
  assert.deepEqual(memory.filter(entries, "VOICE", "project"), [entries[0]]);
  assert.deepEqual(memory.filter(entries, "", "pending"), [entries[1]]);
  assert.deepEqual(memory.filter(entries, "<script>", ""), []);
});
