/* Local microphone transport. Speech classification happens in Alice's backend. */
(() => {
  "use strict";
  class VoiceInput {
    constructor({ onSpeech, onError }) {
      this.onSpeech = onSpeech;
      this.onError = onError;
      this.generation = 0;
    }

    async start() {
      this.stop();
      const generation = this.generation;
      const current = () => generation === this.generation;
      try {
        if (!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode) {
          throw new Error("This browser does not support local microphone processing.");
        }
        const stream = await navigator.mediaDevices.getUserMedia({ audio: {
          channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true,
        } });
        if (!current()) {
          stream.getTracks().forEach((track) => track.stop());
          return false;
        }
        this.stream = stream;
        stream.getTracks().forEach((track) => track.addEventListener("ended", () => {
          if (current()) this.fail(new Error("The microphone was disconnected."));
        }));
        const context = new AudioContext({ sampleRate: 16000, latencyHint: "interactive" });
        this.context = context;
        if (context.sampleRate !== 16000) throw new Error("16 kHz microphone audio is unavailable.");
        await context.resume();
        await context.audioWorklet.addModule("/static/voice-capture.js");
        if (!current()) return false;
        const url = new URL("/api/voice/activity", location.href);
        url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
        const socket = new WebSocket(url);
        this.socket = socket;
        await new Promise((resolve, reject) => {
          const timeout = setTimeout(() => reject(new Error("Voice detection did not connect.")), 8000);
          const finish = (error) => {
            clearTimeout(timeout);
            error ? reject(error) : resolve();
          };
          socket.onmessage = (message) => {
            if (!current()) return;
            const event = JSON.parse(message.data).event;
            if (event === "ready") finish();
            else if (event === "speech_start") this.onSpeech();
          };
          socket.onerror = () => finish(new Error("Voice detection connection failed."));
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
        capture.port.onmessage = ({ data }) => {
          if (!current() || socket.readyState !== WebSocket.OPEN) return;
          if (socket.bufferedAmount > 6400) {
            this.fail(new Error("Voice detection is falling behind. Enable it again to reconnect."));
            return;
          }
          socket.send(data);
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
      this.onError(error);
    }

    stop() {
      this.generation += 1;
      this.capture?.disconnect();
      this.source?.disconnect();
      this.stream?.getTracks().forEach((track) => track.stop());
      this.socket?.close();
      this.context?.close().catch(() => {});
      this.capture = this.source = this.stream = this.socket = this.context = null;
    }
  }
  window.AliceVoiceInput = VoiceInput;
})();
