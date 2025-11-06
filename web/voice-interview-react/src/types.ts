export interface VoiceSessionData {
	session_id: string;
	interview_id: string;
	status: string;
	appsync_channel: string;
	appsync_endpoint: string;
	message: string;
}

export interface AudioEvent {
	type: 'audio-input' | 'audio-output' | 'transcription' | 'session-status' | 'error';
	data: any;
	timestamp: number;
}

export interface AudioProcessorConfig {
	sampleRate: number;
	channelCount: number;
	bufferSize: number;
	echoCancellation: boolean;
	noiseSuppression: boolean;
}

export interface VoiceInterfaceProps {
	interviewId: string;
	onStatusChange?: (status: string, message: string) => void;
	onError?: (error: string) => void;
	onTranscription?: (transcription: string, isUser: boolean) => void;
}

export interface ConnectionStatus {
	appsync: 'disconnected' | 'connecting' | 'connected' | 'error';
	audio: 'inactive' | 'recording' | 'playing' | 'error';
	session: 'inactive' | 'initializing' | 'active' | 'ending' | 'error';
}

export interface AudioLevelData {
	level: number;
	peak: number;
	timestamp: number;
}

export interface AudioQualityMetrics {
	signalLevel: number;
	noiseLevel: number;
	snr: number; // Signal-to-Noise Ratio in dB
	clipping: boolean;
	silenceDetected: boolean;
	qualityScore: number; // 0-100 overall quality score
}