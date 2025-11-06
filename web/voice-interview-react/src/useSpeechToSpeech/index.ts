import { useCallback, useRef, useState } from 'react';
import { events, EventsChannel } from 'aws-amplify/data';
import { AudioPlayer } from './lib/AudioPlayer';
import { AudioRecorder } from './lib/AudioRecorder';
import useChatHistory from './useChatHistory';
import { DispatchEventParams, SpeechToSpeechEventSchema } from '../common/schemas';
import { Amplify } from 'aws-amplify';
import { decodeJWT } from 'aws-amplify/auth';
import { AudioEventSequencer } from '../common/events';

const NAMESPACE = 'nova-sonic-voice';
let audioInputSequence = 0;
let tokenCache: { updatedAt: number; token: string } = { updatedAt: 0, token: '' };

const arrayBufferToBase64 = (buffer: ArrayBufferLike) => {
  const binary = [];
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary.push(String.fromCharCode(bytes[i]));
  }
  return btoa(binary.join(''));
};

const base64ToFloat32Array = (base64String: string) => {
  try {
    const binaryString = atob(base64String);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    return float32Array;
  } catch (error) {
    console.error('Error in base64ToFloat32Array:', error);
    throw error;
  }
};

export const useSpeechToSpeech = (userId: string, onSessionEnd?: (reason?: string) => void) => {
  const { messages, addMessage, clearMessages } = useChatHistory();
  const [isActive, setIsActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isAssistantSpeaking, setIsAssistantSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [errorMessages, setErrorMessages] = useState<string[]>([]);

  const channelRef = useRef<EventsChannel | null>(null);
  const audioPlayerRef = useRef<AudioPlayer | null>(null);
  const audioRecorderRef = useRef<AudioRecorder | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const audioInputQueue = useRef<string[]>([]);

  const dispatchEvent = useCallback(async (params: DispatchEventParams) => {
    if (!channelRef.current) return;
    try {
      await channelRef.current.publish({
        direction: 'ctob',
        ...params,
      });
    } catch (e) {
      console.error('Failed to publish event:', e);
    }
  }, []);

  const processAudioInputRef = useRef<boolean>(false);

  const processAudioInput = useCallback(() => {
    if (!processAudioInputRef.current) return;

    if (audioInputQueue.current.length > 5) {
      const chunksToProcess: string[] = [];
      let processedChunks = 0;

      while (audioInputQueue.current.length > 0 && processedChunks < 10) {
        const chunk = audioInputQueue.current.shift();
        if (chunk) {
          chunksToProcess.push(chunk);
          processedChunks += 1;
        }
      }

      // console.log('Sending audio chunks:', chunksToProcess.length, 'sequence:', audioInputSequence);
      dispatchEvent({
        event: 'audioInput',
        data: { blobs: chunksToProcess, sequence: audioInputSequence++ },
      });
    }

    // Continue processing
    setTimeout(processAudioInput, 100);
  }, [dispatchEvent]);

  const startSession = useCallback(
    async () => {
      if (isActive) return;

      try {
        setIsLoading(true);
        setErrorMessages([]);
        clearMessages();

        // Get interview ID from global data
        const interviewId = (window as any).interviewData?.id;
        if (!interviewId) {
          throw new Error('Interview ID not found');
        }

        // Start the voice interview using the correct endpoint
        const response = await fetch(`/api/interviews/${interviewId}/voice/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Failed to start voice session: ${errorText}`);
        }

        const { session_id, appsync_channel, appsync_endpoint } = await response.json();
        sessionIdRef.current = session_id;

        // Configure Amplify with the AppSync Events endpoint
        Amplify.configure(
          {
            API: {
              Events: {
                endpoint: `https://${appsync_endpoint}/event`,
                region: 'us-east-1',
                defaultAuthMode: 'userPool',
              },
            },
          },
          {
            Auth: {
              tokenProvider: {
                getTokens: async () => {
                  // Cache access token to prevent too frequent fetch calls
                  if (tokenCache.updatedAt > Date.now() - 1000 * 10) {
                    return {
                      accessToken: decodeJWT(tokenCache.token),
                    };
                  }
                  const res = await fetch('/api/cognito-token');
                  const { accessToken } = await res.json();
                  tokenCache.updatedAt = Date.now();
                  tokenCache.token = accessToken;
                  return {
                    accessToken: decodeJWT(accessToken),
                  };
                },
              },
            },
          }
        );

        // Connect to AppSync Events using the provided channel
        const channel = await events.connect(appsync_channel);
        channelRef.current = channel;

        // Initialize audio components
        audioPlayerRef.current = new AudioPlayer();
        audioRecorderRef.current = new AudioRecorder();
        audioInputQueue.current = [];

        const sequencer = new AudioEventSequencer((chunks) => {
          while (chunks.length > 0) {
            const chunk = chunks.shift();
            if (chunk && audioPlayerRef.current) {
              const audioData = base64ToFloat32Array(chunk);
              audioPlayerRef.current.playAudio(audioData);
            }
          }
        });

        // Set up audio recorder
        audioRecorderRef.current.addEventListener('onAudioRecorded', (audioData: Int16Array) => {
          // console.log('Audio recorded, length:', audioData.length, 'muted:', isMuted);
          if (!isMuted) {
            const base64Data = arrayBufferToBase64(audioData.buffer);
            audioInputQueue.current.push(base64Data);
            // console.log('Audio queue length:', audioInputQueue.current.length);
          }
        });

        audioRecorderRef.current.addEventListener('onError', (error: { type: string; message: string }) => {
          console.error('Audio recorder error:', error);
          setErrorMessages(prev => [...prev, `Microphone error: ${error.message}`]);
        });

        // Set up event handlers
        channel.subscribe({
          next: async (data: { event: unknown }) => {
            const { data: event, error } = SpeechToSpeechEventSchema.safeParse(data.event);
            if (error) {
              console.error('Invalid event:', error);
              return;
            }

            if (event.direction !== 'btoc') return;

            switch (event.event) {
              case 'ready':
                // console.log('Server is ready, starting recording...');
                try {
                  await audioPlayerRef.current?.start();
                  // console.log('AudioPlayer started');

                  const success = await audioRecorderRef.current?.start();
                  // console.log('AudioRecorder start result:', success);

                  if (success) {
                    setIsActive(true);
                    setIsLoading(false);
                    // console.log('Starting audio input processing...');
                    // Start the processing loop
                    processAudioInputRef.current = true;
                    processAudioInput();
                  } else {
                    throw new Error('Failed to start audio recording');
                  }
                } catch (error) {
                  console.error('Error starting audio:', error);
                  setErrorMessages(prev => [...prev, `Audio setup failed: ${error}`]);
                  setIsLoading(false);
                }
                break;
              case 'audioOutput':
                if (audioPlayerRef.current) {
                  sequencer.next(event.data.blobs, event.data.sequence);
                }
                setIsAssistantSpeaking(true);
                break;
              case 'textStart':
                addMessage({
                  id: event.data.id,
                  role: event.data.role as 'user' | 'assistant',
                  content: '',
                  isComplete: false,
                });
                break;
              case 'textOutput':
                addMessage({
                  id: event.data.id,
                  role: event.data.role as 'user' | 'assistant',
                  content: event.data.content,
                  isComplete: false,
                });
                break;
              case 'textStop':
                addMessage({
                  id: event.data.id,
                  role: 'assistant',
                  content: '',
                  isComplete: true,
                });
                setIsAssistantSpeaking(false);

                // Handle interruption - stop audio playback immediately
                if (event.data.stopReason === 'INTERRUPTED') {
                  // console.log('Assistant was interrupted, stopping audio playback');
                  audioPlayerRef.current?.bargeIn();
                }
                break;
              case 'end':
                setIsActive(false);
                onSessionEnd?.(event.data.reason);
                break;
            }
          },
          error: (error) => {
            console.error('Channel error:', error);
            setErrorMessages(prev => [...prev, 'Connection error occurred']);
          },
        });

      } catch (error) {
        console.error('Failed to start session:', error);
        setErrorMessages(prev => [...prev, `Failed to start voice session: ${error}`]);
        setIsLoading(false);
      }
    },
    [isActive, userId, dispatchEvent, addMessage, clearMessages, isMuted, onSessionEnd, processAudioInput]
  );

  const closeSession = useCallback(async () => {
    // console.log('Closing session, isActive:', isActive);

    // Stop processing first
    processAudioInputRef.current = false;

    // Set inactive to stop other processes
    setIsActive(false);
    setIsAssistantSpeaking(false);

    try {
      const interviewId = (window as any).interviewData?.id;
      if (interviewId) {
        const response = await fetch(`/api/interviews/${interviewId}/voice/end`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
        });

        if (response.ok) {
          // Redirect to interviews list like text interviews
          window.location.href = '/interviews';
          return;
        }
      }

      // Clean up audio components
      if (audioRecorderRef.current) {
        // console.log('Stopping audio recorder');
        audioRecorderRef.current.stop();
        audioRecorderRef.current = null;
      }

      if (audioPlayerRef.current) {
        // console.log('Stopping audio player');
        audioPlayerRef.current.stop();
        audioPlayerRef.current = null;
      }

      if (channelRef.current) {
        // console.log('Closing AppSync channel');
        channelRef.current.close();
        channelRef.current = null;
      }

      // Clear audio queue
      audioInputQueue.current = [];

    } catch (error) {
      console.error('Failed to close session:', error);
    }
  }, [isActive]);

  const toggleMute = useCallback(() => {
    if (audioRecorderRef.current) {
      const newMuteState = audioRecorderRef.current.toggleMute();
      setIsMuted(newMuteState);
      return newMuteState;
    }
    setIsMuted(prev => !prev);
  }, []);

  return {
    messages,
    isActive,
    isLoading,
    isAssistantSpeaking,
    isMuted,
    startSession,
    closeSession,
    toggleMute,
    errorMessages,
  };
};
