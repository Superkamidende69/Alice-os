/* Local microphone transport. Speech classification happens in Alice's backend. */
(() => {
  "use strict";
  class VoiceInput {
    constructor({ onSpeech = () => {}, onError = () => {} } = {}) {
      this.onSpeech = onSpeech;
      this.onError = onError;
      this.generation = 0;
    }

    async start() {
      window.AliceVoiceExperience?.stopTest?.();
      this.stop();
      const generation = this.generation;
      const current = () => generation === this.generation;
      try {
        if (!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode) {
          throw new Error("This browser does not support local microphone processing.");
        }
        const stream = await navigator.mediaDevices.getUserMedia({ audio: {
          channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true,
          ...window.AliceVoiceExperience?.audioConstraints(),
        } });
        if (!current()) {
          stream.getTracks().forEach((track) => track.stop());
          return false;
        }
        this.stream = stream;
        stream.getTracks().forEach((track) => track.addEventListener("ended", () => {
          if (current()) this.fail(new Error("The microphone was disconnected."));
        }));
        const Context = window.AudioContext || window.webkitAudioContext;
        if (!Context) throw new Error("This browser does not support local audio processing.");
        const context = new Context({ sampleRate: 16000, latencyHint: "interactive" });
        this.context = context;
        if (context.sampleRate !== 16000) throw new Error("16 kHz microphone audio is unavailable.");
        await context.resume();
        if (!current()) return false;
        await context.audioWorklet.addModule("/static/voice-capture.js");
        if (!current()) return false;
        const url = new URL("/api/voice/activity", location.href);
        url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
        const socket = new WebSocket(url);
        this.socket = socket;
        await new Promise((resolve, reject) => {
          let settled = false;
          const timeout = setTimeout(() => finish(new Error("Voice detection did not connect.")), 8000);
          const finish = (error) => {
            if (settled) return;
            settled = true;
            clearTimeout(timeout);
            this.cancelConnect = null;
            error ? reject(error) : resolve();
          };
          this.cancelConnect = () => finish(new Error("Microphone connection cancelled."));
          socket.onmessage = (message) => {
            if (!current()) return;
            let event;
            try { event = JSON.parse(message.data).event; }
            catch {
              const error = new Error("Voice detection sent an invalid response.");
              finish(error);
              this.fail(error);
              return;
            }
            if (event === "ready") finish();
            else if (event === "speech_start") this.onSpeech();
          };
          socket.onerror = () => {
            if (!current()) return;
            const error = new Error("Voice detection connection failed.");
            finish(error);
            this.fail(error);
          };
          socket.onclose = () => {
            const error = new Error("Voice detection disconnected. Enable it again to reconnect.");
            finish(error);
            if (current()) this.fail(error);
          };
        });
        if (!current()) return false;
        const source = context.createMediaStreamSource(stream);
        const capture = new AudioWorkletNode(context, "alice-voice-capture");
        this.source = source;
        this.capture = capture;
        capture.onprocessorerror = () => { if (current()) this.fail(new Error("Microphone processing stopped. Enable it again to reconnect.")); };
        capture.port.onmessageerror = capture.onprocessorerror;
        capture.port.onmessage = ({ data }) => {
          if (!current() || socket.readyState !== WebSocket.OPEN) return;
          if (socket.bufferedAmount > 6400) {
            this.fail(new Error("Voice detection is falling behind. Enable it again to reconnect."));
            return;
          }
          try { socket.send(data); }
          catch { this.fail(new Error("Voice detection could not receive microphone audio.")); }
        };
        // The processor outputs silence; microphone audio is never played back.
        source.connect(capture);
        capture.connect(context.destination);
        return true;
      } catch (error) {
        if (current()) this.fail(error);
        return false;
      }
    }

    fail(error) {
      this.stop();
      const message = window.AliceVoiceCommands?.microphoneError(error);
      this.onError(message ? new Error(message) : error);
    }

    stop() {
      this.generation += 1;
      this.cancelConnect?.();
      this.cancelConnect = null;
      if (this.capture) {
        this.capture.port.onmessage = null;
        this.capture.port.onmessageerror = null;
        this.capture.onprocessorerror = null;
        try { this.capture.disconnect(); } catch {}
      }
      try { this.source?.disconnect(); } catch {}
      this.stream?.getTracks().forEach((track) => track.stop());
      if (this.socket) {
        this.socket.onmessage = this.socket.onerror = this.socket.onclose = null;
        try { this.socket.close(); } catch {}
      }
      this.context?.close().catch(() => {});
      this.capture = this.source = this.stream = this.socket = this.context = null;
    }
  }
  window.AliceVoiceInput = VoiceInput;
})();
