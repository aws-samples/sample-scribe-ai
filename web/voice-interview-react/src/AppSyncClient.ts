import { AudioEvent } from './types';
import { Amplify } from 'aws-amplify';
import { events } from 'aws-amplify/data';

export class AppSyncEventsClient {
	private endpoint: string;
	private channel: string;
	private authToken: string;
	private isConnected = false;
	private onEvent?: (event: AudioEvent) => void;
	private onConnectionChange?: (connected: boolean) => void;
	private onError?: (error: string) => void;
	private eventsChannel: any = null;

	constructor(endpoint: string, channel: string, authToken: string) {
		this.endpoint = endpoint;
		this.channel = channel;
		this.authToken = authToken;
		this.configureAmplify();
	}

	private configureAmplify() {
		Amplify.configure({
			API: {
				Events: {
					endpoint: `https://${this.endpoint}/event`,
					region: 'us-east-1',
					defaultAuthMode: 'userPool',
				},
			},
		}, {
			Auth: {
				tokenProvider: {
					getTokens: async () => {
						const response = await fetch('/api/cognito-token');
						const { accessToken } = await response.json();
						
						// Parse JWT manually since we don't have full Amplify auth
						const payload = JSON.parse(atob(accessToken.split('.')[1]));
						
						return {
							accessToken: {
								payload,
								toString: () => accessToken
							}
						};
					},
				},
			},
		});
	}

	async connect(
		onEvent: (event: AudioEvent) => void,
		onConnectionChange?: (connected: boolean) => void,
		onError?: (error: string) => void
	): Promise<void> {
		this.onEvent = onEvent;
		this.onConnectionChange = onConnectionChange;
		this.onError = onError;

		try {
			console.log(`Connecting to AppSync Events channel: ${this.channel}`);
			
			// Connect to AppSync Events using Amplify
			this.eventsChannel = await events.connect(this.channel);
			
			// Subscribe to events
			this.eventsChannel.subscribe({
				next: (data: any) => {
					console.log('Received AppSync event:', data);
					if (this.onEvent) {
						this.onEvent(data.event);
					}
				},
				error: (error: any) => {
					console.error('AppSync Events subscription error:', error);
					this.isConnected = false;
					this.onConnectionChange?.(false);
					this.onError?.(`AppSync Events error: ${error}`);
				}
			});

			this.isConnected = true;
			this.onConnectionChange?.(true);
			console.log('Connected to AppSync Events successfully');

		} catch (error) {
			console.error('Failed to connect to AppSync Events:', error);
			this.onError?.(`Failed to connect to AppSync Events: ${error}`);
			throw error;
		}
	}

	async publishAudioInput(audioChunk: ArrayBuffer, sequenceNumber: number): Promise<void> {
		if (!this.isConnected || !this.eventsChannel) {
			throw new Error('Not connected to AppSync Events');
		}

		try {
			const base64Audio = this.arrayBufferToBase64(audioChunk);
			
			// Send individual audio chunks in the correct format expected by Lambda
			await this.eventsChannel.publish({
				eventType: 'audio-input',
				sessionId: this.extractSessionIdFromChannel(),
				userId: this.extractUserIdFromChannel(),
				timestamp: new Date().toISOString(),
				audioInput: {
					chunk: base64Audio,
					sequenceNumber: sequenceNumber,
					format: 'lpcm'
				}
			});
			
			console.log(`Published audio chunk ${sequenceNumber}`);

		} catch (error) {
			console.error('Error publishing audio to AppSync Events:', error);
		}
	}

	private extractUserIdFromChannel(): string {
		// Channel format: /nova-sonic-voice/user/{userId}/{sessionId}
		const parts = this.channel.split('/');
		return parts[3] || '';
	}

	private extractSessionIdFromChannel(): string {
		// Channel format: /nova-sonic-voice/user/{userId}/{sessionId}
		const parts = this.channel.split('/');
		return parts[4] || '';
	}

	private arrayBufferToBase64(buffer: ArrayBuffer): string {
		const bytes = new Uint8Array(buffer);
		let binary = '';
		for (let i = 0; i < bytes.byteLength; i++) {
			binary += String.fromCharCode(bytes[i]);
		}
		return btoa(binary);
	}

	disconnect(): void {
		if (this.eventsChannel) {
			this.eventsChannel.close();
			this.eventsChannel = null;
		}
		this.isConnected = false;
		this.audioInputQueue = [];
		this.audioInputSequence = 0;
		this.processingAudio = false;
		this.onConnectionChange?.(false);
		console.log('Disconnected from AppSync Events');
	}

	isConnectionActive(): boolean {
		return this.isConnected;
	}
}
