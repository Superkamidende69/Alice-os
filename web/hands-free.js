/* Explicit, local hands-free microphone session. The server owns wake and turn detection. */
(() => {
  "use strict";
  const SAMPLE_RATE = 16000;
  const MAX_BUFFERED_BYTES = 32000;
  const CONNECT_TIMEOUT_MS = 30000;
  const SERVER_STATES = new Set(["idle", "listening", "capturing", "transcribing", "busy", "speaking", "approval"]);

  class HandsFree {
    constructor({ onState = () => {}, onWake = () => {}, onSpeechStart = () => {}, onPartial = () => {}, onTranscript = () => {}, onError = () => {} } = {}) {
      this.callbacks = { onState, onWake, onSpeechStart, onPartial, onTranscript, onError };
      this.generation = 0;
      this.contextRevision = 0;
      this.status = { busy: false, playback: false, awaiting_approval: false, followup: false };
      this.active = false;
      this.connecting = false;
      this.state = "off";
      this.turns = new Map();
    }

    emit(name, value) {
      try { this.callbacks[name](value); }
      catch (error) { console.error("Hands-free callback failed:", error); }
    }

    publish(state, details = {}) {
      this.state = state;
      this.emit("onState", { ...details, state, active: this.active, connecting: this.connecting, context_revision: this.contextRevision });
    }

    async start(options = {}) {
      window.AliceVoiceExperience?.stopTest?.();
      this.stop("restart");
      const generation = this.generation;
      const current = () => generation === this.generation;
      this.contextRevision += 1;
      this.status = { busy: false, playback: false, awaiting_approval: false, followup: false };
      this.connecting = true;
      this.publish("connecting");
      // A pending permission prompt cannot hold start() open after Stop. A late
      // stream is still reclaimed by connect() when getUserMedia resolves.
      const cancelled = new Promise((resolve) => { this.cancelStart = () => resolve(false); });
      this.startTimer = setTimeout(() => {
        if (current()) this.fail(new Error("Hands-free voice did not start in time. Check microphone permission and try again."));
      }, CONNECT_TIMEOUT_MS);
      this.onHidden = () => { if (document.hidden && current()) this.stop("page_hidden"); };
      this.onPageHide = () => { if (current()) this.stop("page_closed"); };
      this.onOffline = () => { if (current()) this.fail(new Error("Hands-free voice disconnected. Enable it again to reconnect.")); };
      document.addEventListener("visibilitychange", this.onHidden);
      window.addEventListener("pagehide", this.onPageHide);
      window.addEventListener("offline", this.onOffline);
      try {
        return await Promise.race([this.connect(options, current), cancelled]);
      } catch (error) {
        if (current()) this.fail(error);
        return false;
      } finally {
        if (current()) {
          clearTimeout(this.startTimer);
          this.startTimer = null;
          this.cancelStart = null;
        }
      }
    }

    async connect(options, current) {
      if (document.hidden) throw new Error("Keep Alice visible to enable hands-free voice.");
      const Context = window.AudioContext || window.webkitAudioContext;
      if (!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode || !Context || !window.WebSocket) {
        throw new Error("This browser does not support local hands-free microphone processing.");
      }
      const configuration = {
        type: "configure",
        wake_phrase: options.wake_phrase ?? "hey jarvis",
        end_silence_ms: options.end_silence_ms ?? 700,
        followup_seconds: options.followup_seconds ?? 12,
      };
      if (!["hey alice", "hey jarvis"].includes(configuration.wake_phrase)) throw new Error("Choose Hey Alice or Hey Jarvis as the wake phrase.");
      if (!Number.isInteger(configuration.end_silence_ms) || configuration.end_silence_ms < 500 || configuration.end_silence_ms > 2000) throw new Error("The speech pause must be between 500 and 2000 milliseconds.");
      if (!Number.isFinite(configuration.followup_seconds) || configuration.followup_seconds < 0 || configuration.followup_seconds > 30) throw new Error("The follow-up window must be between 0 and 30 seconds.");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: {
        channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true,
        ...window.AliceVoiceExperience?.audioConstraints(),
      } });
      if (!current()) {
        stream.getTracks().forEach((track) => track.stop());
        return false;
      }
      this.stream = stream;
      this.trackListeners = stream.getTracks().map((track) => {
        const ended = () => { if (current()) this.fail(new Error("The microphone was disconnected. Enable hands-free voice again after reconnecting it.")); };
        track.addEventListener("ended", ended);
        return [track, ended];
      });
      const context = new Context({ sampleRate: SAMPLE_RATE, latencyHint: "interactive" });
      this.audioContext = context;
      if (context.sampleRate !== SAMPLE_RATE) throw new Error("16 kHz microphone audio is unavailable in this browser.");
      await context.resume();
      if (!current()) return false;
      await context.audioWorklet.addModule("/static/voice-capture.js");
      if (!current()) return false;
      const url = new URL("/api/voice/conversation", location.href);
      url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
      const socket = new window.WebSocket(url);
      this.socket = socket;
      socket.binaryType = "arraybuffer";
      await new Promise((resolve, reject) => {
        let settled = false;
        const finish = (error) => {
          if (settled) return;
          settled = true;
          this.cancelReady = null;
          error ? reject(error) : resolve();
        };
        this.cancelReady = () => finish(new Error("Hands-free voice was stopped."));
        socket.onmessage = ({ data }) => {
          if (!current()) return;
          let message;
          try {
            message = JSON.parse(data);
            if (!message || typeof message !== "object" || typeof message.event !== "string") throw new Error();
          } catch {
            const error = new Error("Hands-free voice received an invalid server response.");
            finish(error);
            this.fail(error);
            return;
          }
          if (message.event === "ready") {
            if (settled) return;
            if (message.sample_rate !== SAMPLE_RATE) {
              const error = new Error("The hands-free service requested an unsupported audio format.");
              finish(error);
              this.fail(error);
              return;
            }
            this.ready = true;
            if (this.send(configuration) && this.sendContext()) finish();
          } else if (this.ready || message.event === "error") this.receive(message);
        };
        socket.onerror = () => {
          if (!current()) return;
          const error = new Error("The local hands-free service could not connect. Check Alice's voice settings and try again.");
          finish(error);
          this.fail(error);
        };
        socket.onclose = () => {
          if (!current()) return;
          const error = new Error("Hands-free voice disconnected. Enable it again to reconnect.");
          finish(error);
          this.fail(error);
        };
      });
      if (!current()) return false;
      const source = context.createMediaStreamSource(stream);
      this.source = source;
      const capture = new window.AudioWorkletNode(context, "alice-voice-capture");
      this.capture = capture;
      // Keep the worklet processing without routing microphone samples to speakers.
      const silence = context.createGain();
      silence.gain.value = 0;
      this.silence = silence;
      capture.onprocessorerror = () => { if (current()) this.fail(new Error("Microphone processing stopped. Enable hands-free voice again to retry.")); };
      capture.port.onmessageerror = capture.onprocessorerror;
      capture.port.onmessage = ({ data }) => {
        if (!current() || !this.active) return;
        if (!(data instanceof ArrayBuffer) && !ArrayBuffer.isView(data)) {
          this.fail(new Error("Microphone processing returned invalid audio."));
          return;
        }
        if (!data.byteLength || data.byteLength % 2 || data.byteLength > MAX_BUFFERED_BYTES) {
          this.fail(new Error("Microphone processing returned an invalid audio packet."));
          return;
        }
        if (socket.bufferedAmount + data.byteLength > MAX_BUFFERED_BYTES) {
          this.fail(new Error("Hands-free voice is falling behind. Enable it again to reconnect."));
          return;
        }
        this.send(data, true);
      };
      source.connect(capture);
      capture.connect(silence);
      silence.connect(context.destination);
      this.active = true;
      this.connecting = false;
      this.onAudioState = () => {
        if (current() && this.active && context.state !== "running") this.fail(new Error("Microphone audio was suspended. Enable hands-free voice again to resume."));
      };
      context.addEventListener("statechange", this.onAudioState);
      this.publish(this.state === "connecting" ? "idle" : this.state);
      return true;
    }

    send(message, binary = false) {
      if (!this.socket || this.socket.readyState !== window.WebSocket.OPEN) {
        this.fail(new Error("Hands-free voice disconnected. Enable it again to reconnect."));
        return false;
      }
      try { this.socket.send(binary ? message : JSON.stringify(message)); return true; }
      catch { this.fail(new Error("The hands-free service could not receive microphone data.")); return false; }
    }

    sendContext() {
      const sent = this.send({ type: "context", revision: this.contextRevision, ...this.status });
      this.status.followup = false;
      return sent;
    }

    // Busy/playback updates retain the revision, so an interruption can finish
    // transcribing while playback stops. Explicit revision changes invalidate it.
    setContext(update = {}) {
      if (update.revision !== undefined) {
        if (!Number.isSafeInteger(update.revision) || update.revision < this.contextRevision) throw new Error("Voice context revisions must increase.");
        if (update.revision !== this.contextRevision) this.turns.clear();
        this.contextRevision = update.revision;
      }
      for (const field of ["busy", "playback", "awaiting_approval", "followup"]) {
        if (update[field] !== undefined) this.status[field] = Boolean(update[field]);
      }
      if (this.ready) this.sendContext();
      return this.contextRevision;
    }

    invalidate() {
      this.status.followup = false;
      this.setContext({ revision: this.contextRevision + 1 });
      if (this.ready) this.send({ type: "reset" });
      return this.contextRevision;
    }

    receive(message) {
      if (message.context_revision !== undefined && message.context_revision !== this.contextRevision) return;
      if (message.event === "state") {
        if (SERVER_STATES.has(message.state)) this.publish(message.state, message);
      } else if (message.event === "wake") {
        this.emit("onWake", message);
      } else if (message.event === "transcript_partial") {
        if (message.context_revision !== this.contextRevision || typeof message.turn_id !== "string" || !message.turn_id || typeof message.text !== "string") return;
        const turn = this.turns.get(message.turn_id);
        if (!turn || turn.delivered) return;
        this.emit("onPartial", message);
      } else if (message.event === "speech_start" || message.event === "transcript") {
        if (message.context_revision !== this.contextRevision || typeof message.turn_id !== "string" || !message.turn_id) return;
        const previous = this.turns.get(message.turn_id);
        if (message.event === "speech_start") {
          if (previous) return;
          this.turns.set(message.turn_id, { delivered: false, acknowledged: false });
          this.trimTurns();
          this.emit("onSpeechStart", message);
        } else {
          if (previous?.delivered || typeof message.text !== "string" || !message.text.trim()) return;
          this.turns.set(message.turn_id, { delivered: true, acknowledged: false });
          this.trimTurns();
          this.emit("onTranscript", message);
        }
      } else if (message.event === "error") {
        const error = new Error(message.message || "Local hands-free recognition failed.");
        error.code = message.code;
        error.recoverable = message.recoverable === true;
        if (error.recoverable) this.emit("onError", error);
        else this.fail(error);
      }
    }

    trimTurns() {
      while (this.turns.size > 128) this.turns.delete(this.turns.keys().next().value);
    }

    acknowledge(turnId, { accepted = false } = {}) {
      const turn = this.turns.get(turnId);
      if (!this.ready || !turn?.delivered || turn.acknowledged) return false;
      turn.acknowledged = true;
      return this.send({ type: "ack", turn_id: turnId, accepted: Boolean(accepted), context_revision: this.contextRevision });
    }

    fail(error) {
      this.stop("error");
      const message = window.AliceVoiceCommands?.microphoneError(error);
      if (message) error = Object.assign(new Error(message), { code: error.code, recoverable: error.recoverable });
      this.emit("onError", error);
    }

    stop(reason = "stopped") {
      this.generation += 1;
      this.active = false;
      this.connecting = false;
      this.ready = false;
      clearTimeout(this.startTimer);
      this.startTimer = null;
      this.cancelStart?.();
      this.cancelReady?.();
      this.cancelStart = this.cancelReady = null;
      document.removeEventListener("visibilitychange", this.onHidden);
      window.removeEventListener("pagehide", this.onPageHide);
      window.removeEventListener("offline", this.onOffline);
      this.onHidden = this.onPageHide = this.onOffline = null;
      if (this.capture) {
        this.capture.port.onmessage = this.capture.port.onmessageerror = null;
        this.capture.onprocessorerror = null;
      }
      for (const node of [this.source, this.capture, this.silence]) {
        try { node?.disconnect(); } catch {}
      }
      for (const [track, ended] of this.trackListeners || []) track.removeEventListener("ended", ended);
      this.trackListeners = [];
      this.stream?.getTracks().forEach((track) => track.stop());
      if (this.socket) {
        this.socket.onmessage = this.socket.onerror = this.socket.onclose = null;
        try { this.socket.close(); } catch {}
      }
      if (this.audioContext) {
        this.audioContext.removeEventListener("statechange", this.onAudioState);
        try { this.audioContext.close().catch(() => {}); } catch {}
      }
      this.onAudioState = null;
      this.source = this.capture = this.silence = this.stream = this.socket = this.audioContext = null;
      this.turns.clear();
      this.publish("off", { reason });
    }
  }

  window.AliceHandsFree = HandsFree;
})();
