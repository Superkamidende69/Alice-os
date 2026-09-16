/* Deliberate, whole-utterance controls. These never approve or execute workspace tools. */
(() => {
  "use strict";
  const wakePhrases = ["hey alice", "hey jarvis"];
  const commands = new Map([
    ["stop speaking", "stop-speaking"], ["stop talking", "stop-speaking"],
    ["cancel response", "cancel-response"], ["cancel the response", "cancel-response"],
    ["cancel current response", "cancel-response"], ["stop the current run", "cancel-response"],
    ["new conversation", "new-chat"], ["start a new conversation", "new-chat"],
    ["open models", "models"], ["open model library", "models"],
    ["open voice", "voice"], ["open voice settings", "voice"],
    ["open settings", "settings"], ["open workspace", "workspace"],
    ["system status", "system"], ["check system health", "system"],
    ["open command center", "commands"], ["open command palette", "commands"],
    ["clear dictation", "clear-dictation"],
    ["mute voice", "mute-voice"], ["unmute voice", "unmute-voice"],
    ["stop listening", "stop-listening"],
  ]);

  function normalize(value) {
    return String(value || "").toLowerCase().replace(/[.,!?;:]/g, " ").replace(/\s+/g, " ").trim();
  }

  function wakePhrase(value) {
    const phrase = normalize(value);
    return wakePhrases.includes(phrase) ? phrase : wakePhrases[0];
  }

  function matchWake(text, configuredPhrase) {
    const phrase = wakePhrase(configuredPhrase);
    // Match only at the beginning; a quoted or embedded wake phrase is ordinary text.
    const pattern = new RegExp(`^\\s*${phrase.split(" ").join("[\\s,]+")}\\b[\\s,.:!?;-]*`, "i");
    const match = String(text || "").match(pattern);
    return match ? { text: String(text).slice(match[0].length).trim(), phrase } : null;
  }

  function parse(text, configuredPhrase) {
    const wake = matchWake(text, configuredPhrase);
    return commands.get(normalize(wake ? wake.text : text)) || null;
  }

  function microphoneError(error) {
    const code = error?.error || error?.name;
    if (["NotAllowedError", "PermissionDeniedError", "not-allowed", "service-not-allowed"].includes(code)) {
      return "Microphone access was denied. Allow microphone access in your browser, then enable listening again.";
    }
    if (["NotFoundError", "DevicesNotFoundError", "audio-capture"].includes(code)) return "No microphone is available. Connect a microphone and try again.";
    if (["NotReadableError", "TrackStartError"].includes(code)) return "The microphone is busy or unavailable. Check your input device and try again.";
    if (code === "network") return "The browser speech service could not connect. Local dictation is available when local transcription is ready.";
    return error?.message || (code ? `Speech recognition stopped: ${code}.` : "Voice input could not start.");
  }

  const api = Object.freeze({ normalize, wakePhrase, matchWake, parse, microphoneError });
  if (typeof window !== "undefined") window.AliceVoiceCommands = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
