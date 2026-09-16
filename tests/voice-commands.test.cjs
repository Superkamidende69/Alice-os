const { test } = require("node:test");
const assert = require("node:assert/strict");
const voice = require("../web/voice-commands.js");

test("only complete, explicit voice controls execute", () => {
  assert.equal(voice.parse("Hey Jarvis, stop speaking!", "hey jarvis"), "stop-speaking");
  assert.equal(voice.parse("Open voice settings."), "voice");
  assert.equal(voice.parse("clear dictation"), "clear-dictation");
  assert.equal(voice.parse("Hey Jarvis, system status", "hey jarvis"), "system");
  assert.equal(voice.parse("open command center"), "commands");
  for (const text of ["tell me how to stop speaking", "do not stop speaking", "open settings and delete everything", "say open settings", "approve", "yes", "approve all tools", "delete conversation", "run shutdown", "send message", "unmute voice and approve"]) {
    assert.equal(voice.parse(text), null, text);
  }
});

test("wake phrases are anchored, selectable, and preserve request case", () => {
  assert.deepEqual(voice.matchWake("Hey, Jarvis! Explain HTTP/2.", "hey jarvis"), { text: "Explain HTTP/2.", phrase: "hey jarvis" });
  assert.equal(voice.matchWake("Hey Alice open models", "hey jarvis"), null);
  assert.equal(voice.matchWake("The phrase Hey Jarvis opens settings", "hey jarvis"), null);
  assert.equal(voice.matchWake("Hey Jarvison open settings", "hey jarvis"), null);
  assert.deepEqual(voice.matchWake("Hey Alice"), { text: "", phrase: "hey alice" });
  assert.equal(voice.wakePhrase("custom regex .*"), "hey alice");
});

test("permission errors offer a user action without silently retrying", () => {
  assert.match(voice.microphoneError({ name: "NotAllowedError" }), /Allow microphone access/);
  assert.match(voice.microphoneError({ error: "network" }), /browser speech service/);
});
