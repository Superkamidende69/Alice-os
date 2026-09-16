/* Local audio preferences and a microphone test that never records or uploads. */
((root) => {
  "use strict";
  const read = (key, fallback) => { try { return root.localStorage.getItem(`alice-audio-${key}`) ?? fallback; } catch { return fallback; } };
  const save = (key, value) => { try { root.localStorage.setItem(`alice-audio-${key}`, String(value)); } catch {} };
  function audioConstraints() {
    const device = read("device", "");
    return { channelCount: 1, echoCancellation: true, noiseSuppression: read("noise", "true") !== "false",
      autoGainControl: true, ...(device ? { deviceId: { exact: device } } : {}) };
  }
  function volume() {
    const value = Number(read("volume", "0.85"));
    return Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0.85;
  }
  function speechText(text, state = {}) {
    // Fenced code remains in the transcript; its content is not useful spoken aloud.
    let spoken = "";
    for (const part of String(text).split(/(```|~~~)/)) {
      if (part === "```" || part === "~~~") {
        if (!state.fence) { state.fence = part; spoken += " Code is shown in the conversation. "; }
        else if (state.fence === part) state.fence = null;
      } else if (!state.fence) spoken += part;
    }
    return spoken.replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/https?:\/\/\S+/g, "link")
      .replace(/^\s{0,3}(?:#{1,6}\s+|>\s*|[-*+]\s+)/gm, "")
      .replace(/[*_`~]/g, "").replace(/\s+/g, " ").trim();
  }
  const api = { audioConstraints, volume, speechText };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.AliceVoiceExperience = api;
  if (!root.document) return;
  root.document.addEventListener("DOMContentLoaded", () => {
    const $ = id => root.document.getElementById(id);
    const select = $("voice-input-device"), button = $("voice-test-mic"), status = $("voice-mic-test-status");
    if (!select || !button) return;
    const level = $("voice-input-level"), noise = $("voice-noise-filter"), slider = $("voice-volume");
    let generation = 0, stream = null, context = null, source = null, timer = null, frame = null;
    let testing = false, listing = 0;
    const message = text => { status.textContent = text; };
    const stop = (text = "Microphone test stopped.") => {
      generation += 1; testing = false;
      clearTimeout(timer); root.cancelAnimationFrame(frame);
      source?.disconnect(); source = null;
      stream?.getTracks().forEach(track => track.stop()); stream = null;
      if (context) { void context.close().catch(() => {}); context = null; }
      level.value = 0; button.textContent = "Test microphone"; button.setAttribute("aria-pressed", "false");
      message(text);
    };
    api.stopTest = () => { if (testing) stop(); };
    async function devices() {
      const request = ++listing;
      try {
        const items = await root.navigator.mediaDevices.enumerateDevices();
        if (request !== listing) return;
        const saved = read("device", "");
        select.replaceChildren(new Option("System default microphone", ""));
        items.filter(item => item.kind === "audioinput" && item.deviceId && item.deviceId !== "default").forEach((item, index) => {
          select.add(new Option(item.label || `Microphone ${index + 1}`, item.deviceId));
        });
        if (saved && ![...select.options].some(option => option.value === saved)) select.add(new Option("Saved microphone unavailable — choose another", saved));
        select.value = saved;
      } catch { message("Device list unavailable. Use a secure browser connection and allow microphone access."); }
    }
    noise.checked = read("noise", "true") !== "false";
    slider.value = String(Math.round(volume() * 100));
    function applyVolume() {
      $("voice-volume-label").textContent = `${Math.round(volume() * 100)}%`;
      [$("voice-player"), $("voice-studio-player")].forEach(player => { if (player) player.volume = volume(); });
    }
    slider.addEventListener("input", () => { save("volume", Number(slider.value) / 100); applyVolume(); });
    applyVolume();
    for (const control of [select, noise]) control.addEventListener("change", () => {
      save("device", select.value); save("noise", noise.checked);
      stop("Input settings saved. Start listening again to use them.");
      root.dispatchEvent(new Event("alice:audio-input-change"));
    });
    button.addEventListener("click", async () => {
      if (testing) { stop(); return; }
      root.dispatchEvent(new Event("alice:audio-input-change"));
      testing = true;
      const ticket = ++generation;
      button.textContent = "Stop test"; button.setAttribute("aria-pressed", "true");
      message("Allow microphone access, then speak normally. No audio is recorded or sent.");
      timer = setTimeout(() => { if (ticket === generation) stop("Microphone test finished. Adjust your input device if the meter stayed low."); }, 15000);
      try {
        const acquired = await root.navigator.mediaDevices.getUserMedia({audio: audioConstraints()});
        if (ticket !== generation) { acquired.getTracks().forEach(track => track.stop()); return; }
        stream = acquired;
        const Context = root.AudioContext || root.webkitAudioContext;
        context = new Context();
        const activeContext = context;
        await activeContext.resume();
        if (ticket !== generation) return;
        source = activeContext.createMediaStreamSource(stream);
        const analyser = activeContext.createAnalyser(); analyser.fftSize = 512;
        source.connect(analyser); // Deliberately no connection to speakers.
        const samples = new Float32Array(analyser.fftSize);
        let lastLabel = "";
        const sample = () => {
          if (ticket !== generation) return;
          analyser.getFloatTimeDomainData(samples);
          const rms = Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / samples.length);
          level.value = Math.min(1, rms * 5);
          const label = rms > 0.5 ? "Input is very loud — lower microphone gain." : rms > 0.015 ? "Voice level detected. Your microphone is working." : "Speak normally to check your input level.";
          if (label !== lastLabel) { message(label); lastLabel = label; }
          frame = root.requestAnimationFrame(sample);
        };
        stream.getTracks().forEach(track => track.addEventListener("ended", () => { if (ticket === generation) stop("Microphone disconnected."); }));
        sample(); void devices();
      } catch (error) {
        if (ticket === generation) stop(root.AliceVoiceCommands?.microphoneError(error) || error.message);
      }
    });
    $("voice-refresh-devices").addEventListener("click", () => void devices());
    root.navigator.mediaDevices?.addEventListener?.("devicechange", () => void devices());
    root.document.addEventListener("visibilitychange", () => { if (root.document.hidden && testing) stop("Microphone test stopped while Alice is hidden."); });
    root.addEventListener("pagehide", () => stop());
    void devices();
  });
})(typeof window !== "undefined" ? window : globalThis);
