/* The AudioContext resamples input to 16 kHz. Send three 20 ms PCM16 frames. */
class AliceVoiceCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.packet = new ArrayBuffer(1920);
    this.view = new DataView(this.packet);
    this.offset = 0;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (!channel) return true;
    for (const sample of channel) {
      const value = Math.max(-1, Math.min(1, sample));
      this.view.setInt16(this.offset, Math.round(value * (value < 0 ? 32768 : 32767)), true);
      this.offset += 2;
      if (this.offset === this.packet.byteLength) {
        this.port.postMessage(this.packet, [this.packet]);
        this.packet = new ArrayBuffer(1920);
        this.view = new DataView(this.packet);
        this.offset = 0;
      }
    }
    return true;
  }
}
registerProcessor("alice-voice-capture", AliceVoiceCapture);
