import { ObjectExt } from './ObjectsExt.js';

export class AudioPlayer {
  constructor() {
    this.onAudioPlayedListeners = [];
    this.initialized = false;
  }

  addEventListener(event, callback) {
    switch (event) {
      case 'onAudioPlayed':
        this.onAudioPlayedListeners.push(callback);
        break;
      default:
        console.error('Listener registered for event type: ' + JSON.stringify(event) + ' which is not supported');
    }
  }

  async start() {
    if (this.initialized) return;
    
    try {
      this.audioContext = new AudioContext({ sampleRate: 24000 });
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 512;

      const AudioPlayerWorkletUrl = '/static/js/AudioPlayerProcessor.worklet.js';
      await this.audioContext.audioWorklet.addModule(AudioPlayerWorkletUrl);
      
      this.workletNode = new AudioWorkletNode(this.audioContext, 'audio-player-processor');
      this.workletNode.connect(this.analyser);
      this.analyser.connect(this.audioContext.destination);
      
      this.recorderNode = this.audioContext.createScriptProcessor(512, 1, 1);
      this.recorderNode.onaudioprocess = (event) => {
        // Pass the input along as-is
        const inputData = event.inputBuffer.getChannelData(0);
        const outputData = event.outputBuffer.getChannelData(0);
        outputData.set(inputData);
        // Notify listeners that the audio was played
        const samples = new Float32Array(outputData.length);
        samples.set(outputData);
        this.onAudioPlayedListeners.map((listener) => listener(samples));
      };
      
      this.initialized = true;
      // console.log('AudioPlayer started with worklet');
    } catch (error) {
      console.error('Failed to start AudioPlayer:', error);
      throw error;
    }
  }

  playAudio(audioData) {
    if (!this.initialized) {
      console.warn('AudioPlayer not initialized');
      return;
    }

    this.workletNode.port.postMessage({
      type: 'audio',
      audioData: audioData,
    });
  }

  bargeIn() {
    // console.log('AudioPlayer: Barge-in triggered, clearing worklet buffer');
    if (this.workletNode) {
      this.workletNode.port.postMessage({
        type: 'barge-in',
      });
    }
  }

  stop() {
    if (ObjectExt.exists(this.audioContext)) {
      this.audioContext.close();
    }

    if (ObjectExt.exists(this.analyser)) {
      this.analyser.disconnect();
    }

    if (ObjectExt.exists(this.workletNode)) {
      this.workletNode.disconnect();
    }

    if (ObjectExt.exists(this.recorderNode)) {
      this.recorderNode.disconnect();
    }

    this.initialized = false;
    this.audioContext = null;
    this.analyser = null;
    this.workletNode = null;
    this.recorderNode = null;
    // console.log('AudioPlayer stopped');
  }

  enqueue(audioChunks) {
    // For compatibility with existing code
    if (Array.isArray(audioChunks)) {
      audioChunks.forEach(chunk => {
        this.playAudio(chunk);
      });
    }
  }
}
