import { ObjectExt } from './ObjectsExt.js';

// Firefox doesn't support connecting AudioNodes from AudioContexts with different sample rates.
// Therefore, we use the default sample rate of AudioContext and downsample the audio manually.
const TARGET_SAMPLE_RATE = 16000;

export class AudioRecorder {
  constructor() {
    this.onAudioRecordedListeners = [];
    this.onErrorListeners = [];
    this.initialized = false;
    this.isMuted = false;
  }

  addEventListener(event, callback) {
    switch (event) {
      case 'onAudioRecorded':
        this.onAudioRecordedListeners.push(callback);
        break;
      case 'onError':
        this.onErrorListeners.push(callback);
        break;
      default:
        console.error('Listener registered for event type: ' + JSON.stringify(event) + ' which is not supported');
    }
  }

  async start() {
    try {
      const isFirefox = navigator.userAgent.toLowerCase().includes('firefox');
      this.audioContext = new AudioContext({
        // Set the sample rate if not Firefox, otherwise use the default
        sampleRate: !isFirefox ? TARGET_SAMPLE_RATE : undefined,
      });

      // Get user media stream
      try {
        this.audioStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
      } catch (error) {
        // Handle permission denied or device not available errors
        const errorType = error.name || 'UnknownError';
        const errorMessage = error.message || 'Failed to access microphone';

        // Notify error listeners
        this.onErrorListeners.forEach((listener) =>
          listener({
            type: errorType,
            message: errorMessage,
            originalError: error,
          })
        );

        // Don't throw, just return false to indicate failure
        console.error('Microphone access error:', errorType, errorMessage);
        return false;
      }

      this.sourceNode = this.audioContext.createMediaStreamSource(this.audioStream);

      // Add the audio worklet module
      try {
        const AudioRecorderWorkletUrl = '/static/js/AudioRecorderProcessor.worklet.js';
        await this.audioContext.audioWorklet.addModule(AudioRecorderWorkletUrl);
      } catch (error) {
        this.onErrorListeners.forEach((listener) =>
          listener({
            type: 'WorkletError',
            message: 'Failed to load audio worklet',
            originalError: error,
          })
        );
        this.cleanup();
        return false;
      }

      this.workletNode = new AudioWorkletNode(this.audioContext, 'audio-recorder-processor');

      // Connect the source to the worklet
      this.sourceNode.connect(this.workletNode);
      this.workletNode.connect(this.audioContext.destination);

      // Listen for audio data from the worklet
      this.workletNode.port.onmessage = (event) => {
        if (event.data.type === 'audio') {
          let audioData = event.data.audioData;
          // If muted, replace audio data with zeros (silence)
          if (this.isMuted) {
            audioData = new Int16Array(audioData.length).fill(0);
          }
          this.onAudioRecordedListeners.forEach((listener) => listener(audioData));
        }
      };

      // Start recording
      this.workletNode.port.postMessage({
        type: 'start',
        sourceSampleRate: this.audioContext.sampleRate,
        targetSampleRate: TARGET_SAMPLE_RATE,
      });

      this.initialized = true;
      return true;
    } catch (error) {
      // Catch any other unexpected errors
      this.onErrorListeners.forEach((listener) =>
        listener({
          type: 'InitializationError',
          message: 'Failed to initialize audio recorder',
          originalError: error,
        })
      );
      this.cleanup();
      return false;
    }
  }

  cleanup() {
    if (ObjectExt.exists(this.workletNode)) {
      try {
        this.workletNode.disconnect();
      } catch (e) {
        console.error('Error disconnecting worklet node:', e);
      }
    }

    if (ObjectExt.exists(this.sourceNode)) {
      try {
        this.sourceNode.disconnect();
      } catch (e) {
        console.error('Error disconnecting source node:', e);
      }
    }

    if (ObjectExt.exists(this.audioStream)) {
      try {
        this.audioStream.getTracks().forEach((track) => track.stop());
      } catch (e) {
        console.error('Error stopping audio tracks:', e);
      }
    }

    if (ObjectExt.exists(this.audioContext)) {
      try {
        this.audioContext.close();
      } catch (e) {
        console.error('Error closing audio context:', e);
      }
    }

    this.initialized = false;
    this.audioContext = null;
    this.audioStream = null;
    this.sourceNode = null;
    this.workletNode = null;
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    return this.isMuted;
  }

  stop() {
    if (this.initialized) {
      // Stop recording
      if (ObjectExt.exists(this.workletNode)) {
        this.workletNode.port.postMessage({
          type: 'stop',
        });
      }

      this.cleanup();
    }
  }
}
