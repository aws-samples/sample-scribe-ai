import { AudioProcessorConfig, AudioLevelData, AudioQualityMetrics } from './types';

export class AudioProcessor {
	private audioContext: AudioContext | null = null;
	private mediaStream: MediaStream | null = null;
	private sourceNode: MediaStreamAudioSourceNode | null = null;
	private analyserNode: AnalyserNode | null = null;
	private processorNode: ScriptProcessorNode | null = null;
	private isRecording = false;
	private config: AudioProcessorConfig;
	private onAudioData?: (audioChunk: ArrayBuffer) => void;
	private onAudioLevel?: (levelData: AudioLevelData) => void;
	private onQualityUpdate?: (metrics: AudioQualityMetrics) => void;

	// Audio quality monitoring
	private qualityMetrics: AudioQualityMetrics = {
		signalLevel: 0,
		noiseLevel: 0,
		snr: 0,
		clipping: false,
		silenceDetected: false,
		qualityScore: 0
	};
	private qualityUpdateInterval: NodeJS.Timeout | null = null;
	private audioBuffer: Float32Array[] = [];
	private bufferSize = 0;

	constructor(config: AudioProcessorConfig) {
		this.config = {
			...config,
			sampleRate: config.sampleRate || 16000,
			channelCount: config.channelCount || 1,
			bufferSize: config.bufferSize || 4096,
			echoCancellation: config.echoCancellation ?? true,
			noiseSuppression: config.noiseSuppression ?? true
		};

		// Initialize audio buffer for quality analysis
		this.bufferSize = this.config.bufferSize;
		this.audioBuffer = [];
	}

	async initialize(): Promise<void> {
		try {
			// Request microphone access with enhanced constraints for 16kHz LPCM
			this.mediaStream = await navigator.mediaDevices.getUserMedia({
				audio: {
					sampleRate: { ideal: this.config.sampleRate, min: 16000, max: 48000 },
					channelCount: { exact: this.config.channelCount },
					echoCancellation: this.config.echoCancellation,
					noiseSuppression: this.config.noiseSuppression,
					autoGainControl: true,
					latency: { ideal: 0.01 }, // Low latency for real-time processing
					volume: { ideal: 1.0 }
				}
			});

			// Create audio context with default sample rate (let browser choose)
			this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
				latencyHint: 'interactive'
			});

			// Log actual sample rate for debugging
			console.log(`Audio context initialized with sample rate: ${this.audioContext.sampleRate}Hz`);

			// Create audio nodes
			this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
			this.analyserNode = this.audioContext.createAnalyser();
			this.processorNode = this.audioContext.createScriptProcessor(this.config.bufferSize, 1, 1);

			// Configure analyser for enhanced audio monitoring
			this.analyserNode.fftSize = 2048; // Higher resolution for quality analysis
			this.analyserNode.smoothingTimeConstant = 0.3; // More responsive
			this.analyserNode.minDecibels = -90;
			this.analyserNode.maxDecibels = -10;

			// Connect nodes
			this.sourceNode.connect(this.analyserNode);
			this.analyserNode.connect(this.processorNode);
			this.processorNode.connect(this.audioContext.destination);

			// Set up enhanced audio processing
			this.processorNode.onaudioprocess = (event) => {
				if (!this.isRecording) return;

				const inputBuffer = event.inputBuffer;
				const inputData = inputBuffer.getChannelData(0);

				// Store audio data for quality analysis
				this.audioBuffer.push(new Float32Array(inputData));
				if (this.audioBuffer.length > 10) { // Keep last 10 buffers for analysis
					this.audioBuffer.shift();
				}

				// Convert to 16-bit PCM with proper 16kHz LPCM encoding
				const pcmData = this.convertTo16kHzLPCM(inputData);

				if (this.onAudioData) {
					this.onAudioData(pcmData.buffer as ArrayBuffer);
				}

				// Update audio level and quality metrics
				this.updateAudioLevel();
				this.updateQualityMetrics(inputData);
			};

		} catch (error) {
			throw new Error(`Failed to initialize audio processor: ${error instanceof Error ? error.message : String(error)}`);
		}
	}

	startRecording(
		onAudioData: (audioChunk: ArrayBuffer) => void,
		onAudioLevel?: (levelData: AudioLevelData) => void,
		onQualityUpdate?: (metrics: AudioQualityMetrics) => void
	): void {
		if (!this.audioContext || !this.processorNode) {
			throw new Error('Audio processor not initialized');
		}

		this.onAudioData = onAudioData;
		this.onAudioLevel = onAudioLevel;
		this.onQualityUpdate = onQualityUpdate;
		this.isRecording = true;

		// Resume audio context if suspended
		if (this.audioContext.state === 'suspended') {
			this.audioContext.resume();
		}

		// Start quality monitoring
		this.startQualityMonitoring();
	}

	stopRecording(): void {
		this.isRecording = false;
		this.onAudioData = undefined;
		this.onAudioLevel = undefined;
		this.onQualityUpdate = undefined;

		// Stop quality monitoring
		this.stopQualityMonitoring();
	}

	async playAudio(audioData: ArrayBuffer): Promise<void> {
		if (!this.audioContext) {
			throw new Error('Audio context not initialized');
		}

		try {
			// Decode 24kHz LPCM audio data from Nova Sonic
			const audioBuffer = await this.decode24kHzLPCM(audioData);

			// Create buffer source with enhanced playback settings
			const source = this.audioContext.createBufferSource();
			const gainNode = this.audioContext.createGain();

			source.buffer = audioBuffer;

			// Connect through gain node for volume control
			source.connect(gainNode);
			gainNode.connect(this.audioContext.destination);

			// Set optimal gain for speech playback
			gainNode.gain.value = 0.8;

			// Play audio with fade-in to prevent clicks
			const now = this.audioContext.currentTime;
			gainNode.gain.setValueAtTime(0, now);
			gainNode.gain.linearRampToValueAtTime(0.8, now + 0.01);

			source.start();

			return new Promise((resolve, reject) => {
				source.onended = () => {
					// Fade out to prevent clicks
					const endTime = this.audioContext!.currentTime;
					gainNode.gain.setValueAtTime(0.8, endTime);
					gainNode.gain.linearRampToValueAtTime(0, endTime + 0.01);
					setTimeout(() => resolve(), 20);
				};

				source.onerror = (error) => {
					reject(new Error(`Audio playback error: ${error}`));
				};
			});
		} catch (error) {
			throw new Error(`Failed to play audio: ${error instanceof Error ? error.message : String(error)}`);
		}
	}

	getAudioLevel(): number {
		if (!this.analyserNode) return 0;

		const dataArray = new Uint8Array(this.analyserNode.frequencyBinCount);
		this.analyserNode.getByteFrequencyData(dataArray);

		// Calculate RMS level
		let sum = 0;
		for (let i = 0; i < dataArray.length; i++) {
			sum += dataArray[i] * dataArray[i];
		}
		const rms = Math.sqrt(sum / dataArray.length);
		return (rms / 255) * 100;
	}

	cleanup(): void {
		this.stopRecording();

		if (this.processorNode) {
			this.processorNode.disconnect();
			this.processorNode = null;
		}

		if (this.analyserNode) {
			this.analyserNode.disconnect();
			this.analyserNode = null;
		}

		if (this.sourceNode) {
			this.sourceNode.disconnect();
			this.sourceNode = null;
		}

		if (this.mediaStream) {
			this.mediaStream.getTracks().forEach(track => track.stop());
			this.mediaStream = null;
		}

		if (this.audioContext && this.audioContext.state !== 'closed') {
			this.audioContext.close();
			this.audioContext = null;
		}
	}

	/**
	 * Convert Float32 audio to 16kHz LPCM format for Nova Sonic
	 */
	private convertTo16kHzLPCM(float32Array: Float32Array): Int16Array {
		// Resample to 16kHz if needed
		const targetSampleRate = 16000;
		const currentSampleRate = this.audioContext?.sampleRate || 48000;

		let resampledData = float32Array;
		if (currentSampleRate !== targetSampleRate) {
			resampledData = this.resampleAudio(float32Array, currentSampleRate, targetSampleRate);
		}

		// Convert to 16-bit PCM with proper scaling and dithering
		const pcm16 = new Int16Array(resampledData.length);
		for (let i = 0; i < resampledData.length; i++) {
			// Apply soft clipping to prevent harsh distortion
			let sample = resampledData[i];
			sample = Math.tanh(sample * 0.9); // Soft clipping

			// Convert from [-1, 1] to [-32768, 32767] with dithering
			const dither = (Math.random() - 0.5) * (1 / 32768); // Add small amount of dither
			sample = Math.max(-1, Math.min(1, sample + dither));

			pcm16[i] = sample < 0 ? Math.floor(sample * 0x8000) : Math.floor(sample * 0x7FFF);
		}
		return pcm16;
	}

	/**
	 * Simple linear resampling for audio data
	 */
	private resampleAudio(inputData: Float32Array, inputSampleRate: number, outputSampleRate: number): Float32Array {
		if (inputSampleRate === outputSampleRate) {
			return inputData;
		}

		const ratio = inputSampleRate / outputSampleRate;
		const outputLength = Math.floor(inputData.length / ratio);
		const outputData = new Float32Array(outputLength);

		for (let i = 0; i < outputLength; i++) {
			const sourceIndex = i * ratio;
			const index = Math.floor(sourceIndex);
			const fraction = sourceIndex - index;

			if (index + 1 < inputData.length) {
				// Linear interpolation
				outputData[i] = inputData[index] * (1 - fraction) + inputData[index + 1] * fraction;
			} else {
				outputData[i] = inputData[index] || 0;
			}
		}

		return outputData;
	}

	/**
	 * Decode 24kHz LPCM audio data from Nova Sonic for playback
	 */
	private async decode24kHzLPCM(audioData: ArrayBuffer): Promise<AudioBuffer> {
		if (!this.audioContext) {
			throw new Error('Audio context not available');
		}

		// Nova Sonic returns 24kHz, 16-bit, mono LPCM data
		const pcmData = new Int16Array(audioData);
		const sampleRate = 24000;
		const channels = 1;

		// Create audio buffer with proper sample rate
		const audioBuffer = this.audioContext.createBuffer(channels, pcmData.length, sampleRate);
		const channelData = audioBuffer.getChannelData(0);

		// Convert from 16-bit PCM to float32 with proper scaling
		for (let i = 0; i < pcmData.length; i++) {
			// Proper conversion from signed 16-bit to float32
			channelData[i] = pcmData[i] / (pcmData[i] < 0 ? 0x8000 : 0x7FFF);
		}

		return audioBuffer;
	}

	private updateAudioLevel(): void {
		if (!this.analyserNode || !this.onAudioLevel) return;

		const dataArray = new Uint8Array(this.analyserNode.frequencyBinCount);
		this.analyserNode.getByteFrequencyData(dataArray);

		// Calculate RMS and peak levels
		let sum = 0;
		let peak = 0;
		for (let i = 0; i < dataArray.length; i++) {
			const value = dataArray[i];
			sum += value * value;
			peak = Math.max(peak, value);
		}

		const rms = Math.sqrt(sum / dataArray.length);
		const level = (rms / 255) * 100;
		const peakLevel = (peak / 255) * 100;

		this.onAudioLevel({
			level,
			peak: peakLevel,
			timestamp: Date.now()
		});
	}

	/**
	 * Start quality monitoring with periodic updates
	 */
	private startQualityMonitoring(): void {
		this.qualityUpdateInterval = setInterval(() => {
			if (this.onQualityUpdate) {
				this.onQualityUpdate({ ...this.qualityMetrics });
			}
		}, 1000); // Update every second
	}

	/**
	 * Stop quality monitoring
	 */
	private stopQualityMonitoring(): void {
		if (this.qualityUpdateInterval) {
			clearInterval(this.qualityUpdateInterval);
			this.qualityUpdateInterval = null;
		}
	}

	/**
	 * Update audio quality metrics based on current audio data
	 */
	private updateQualityMetrics(audioData: Float32Array): void {
		if (!this.analyserNode) return;

		// Get frequency domain data for analysis
		const frequencyData = new Uint8Array(this.analyserNode.frequencyBinCount);
		const timeData = new Uint8Array(this.analyserNode.fftSize);

		this.analyserNode.getByteFrequencyData(frequencyData);
		this.analyserNode.getByteTimeDomainData(timeData);

		// Calculate signal level (RMS)
		let signalSum = 0;
		for (let i = 0; i < audioData.length; i++) {
			signalSum += audioData[i] * audioData[i];
		}
		this.qualityMetrics.signalLevel = Math.sqrt(signalSum / audioData.length);

		// Estimate noise level (high frequency content)
		let noiseSum = 0;
		const highFreqStart = Math.floor(frequencyData.length * 0.7);
		for (let i = highFreqStart; i < frequencyData.length; i++) {
			noiseSum += frequencyData[i];
		}
		this.qualityMetrics.noiseLevel = noiseSum / (frequencyData.length - highFreqStart) / 255;

		// Calculate SNR (Signal-to-Noise Ratio)
		if (this.qualityMetrics.noiseLevel > 0) {
			this.qualityMetrics.snr = 20 * Math.log10(this.qualityMetrics.signalLevel / this.qualityMetrics.noiseLevel);
		} else {
			this.qualityMetrics.snr = 60; // Very high SNR when no noise detected
		}

		// Detect clipping
		let clippingCount = 0;
		for (let i = 0; i < audioData.length; i++) {
			if (Math.abs(audioData[i]) > 0.95) {
				clippingCount++;
			}
		}
		this.qualityMetrics.clipping = (clippingCount / audioData.length) > 0.01; // More than 1% clipping

		// Detect silence (very low signal level)
		this.qualityMetrics.silenceDetected = this.qualityMetrics.signalLevel < 0.001;

		// Calculate overall quality score (0-100)
		let qualityScore = 100;

		// Penalize low signal level
		if (this.qualityMetrics.signalLevel < 0.01) {
			qualityScore -= 30;
		} else if (this.qualityMetrics.signalLevel < 0.05) {
			qualityScore -= 15;
		}

		// Penalize high noise
		if (this.qualityMetrics.noiseLevel > 0.1) {
			qualityScore -= 25;
		} else if (this.qualityMetrics.noiseLevel > 0.05) {
			qualityScore -= 10;
		}

		// Penalize low SNR
		if (this.qualityMetrics.snr < 10) {
			qualityScore -= 20;
		} else if (this.qualityMetrics.snr < 20) {
			qualityScore -= 10;
		}

		// Penalize clipping
		if (this.qualityMetrics.clipping) {
			qualityScore -= 15;
		}

		// Penalize silence
		if (this.qualityMetrics.silenceDetected) {
			qualityScore -= 40;
		}

		this.qualityMetrics.qualityScore = Math.max(0, qualityScore);
	}

	/**
	 * Get current audio quality metrics
	 */
	getQualityMetrics(): AudioQualityMetrics {
		return { ...this.qualityMetrics };
	}

	/**
	 * Get audio quality feedback message for user
	 */
	getQualityFeedback(): string {
		const metrics = this.qualityMetrics;

		if (metrics.silenceDetected) {
			return "No audio detected. Please check your microphone.";
		}

		if (metrics.clipping) {
			return "Audio is too loud and distorting. Please move away from the microphone or reduce input volume.";
		}

		if (metrics.signalLevel < 0.01) {
			return "Audio level is very low. Please speak louder or move closer to the microphone.";
		}

		if (metrics.noiseLevel > 0.1) {
			return "High background noise detected. Please find a quieter environment.";
		}

		if (metrics.snr < 10) {
			return "Poor audio quality due to noise. Consider using headphones or finding a quieter location.";
		}

		if (metrics.qualityScore > 80) {
			return "Excellent audio quality.";
		} else if (metrics.qualityScore > 60) {
			return "Good audio quality.";
		} else if (metrics.qualityScore > 40) {
			return "Fair audio quality. Consider improving your audio setup.";
		} else {
			return "Poor audio quality. Please check your microphone and environment.";
		}
	}
}