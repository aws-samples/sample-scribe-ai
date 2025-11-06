import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  VoiceInterfaceProps,
  ConnectionStatus,
  AudioLevelData,
  VoiceSessionData,
  AudioEvent,
  AudioQualityMetrics,
} from "./types";
import { AudioProcessor } from "./AudioProcessor";
import { AppSyncEventsClient } from "./AppSyncClient";

const VoiceInterface: React.FC<VoiceInterfaceProps> = ({
  interviewId,
  onStatusChange,
  onError,
  onTranscription,
}) => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    appsync: "disconnected",
    audio: "inactive",
    session: "inactive",
  });

  const [audioLevel, setAudioLevel] = useState<AudioLevelData>({
    level: 0,
    peak: 0,
    timestamp: 0,
  });

  const [audioQuality, setAudioQuality] = useState<AudioQualityMetrics>({
    signalLevel: 0,
    noiseLevel: 0,
    snr: 0,
    clipping: false,
    silenceDetected: false,
    qualityScore: 0,
  });

  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [sessionData, setSessionData] = useState<VoiceSessionData | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [qualityFeedback, setQualityFeedback] = useState<string>("");
  const [audioChunkCount, setAudioChunkCount] = useState(0);

  const audioProcessorRef = useRef<AudioProcessor | null>(null);
  const appSyncClientRef = useRef<AppSyncEventsClient | null>(null);
  const audioLevelIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize audio processor
  const initializeAudioProcessor = useCallback(async () => {
    try {
      audioProcessorRef.current = new AudioProcessor({
        sampleRate: 16000,
        channelCount: 1,
        bufferSize: 4096,
        echoCancellation: true,
        noiseSuppression: true,
      });

      await audioProcessorRef.current.initialize();

      setConnectionStatus((prev) => ({ ...prev, audio: "inactive" }));
    } catch (error) {
      const errorMsg = `Failed to initialize audio: ${
        error instanceof Error ? error.message : String(error)
      }`;
      setErrorMessage(errorMsg);
      setConnectionStatus((prev) => ({ ...prev, audio: "error" }));
      if (onError) onError(errorMsg);
    }
  }, [onError]);

  // Start voice session
  const startVoiceSession = useCallback(async () => {
    try {
      setErrorMessage("");
      setConnectionStatus((prev) => ({ ...prev, session: "initializing" }));

      if (onStatusChange)
        onStatusChange("connecting", "Starting voice session...");

      // Update template status elements
      if (typeof window !== "undefined" && (window as any).updateVoiceStatus) {
        (window as any).updateVoiceStatus(
          "connecting",
          "Starting voice session..."
        );
      }

      // Initialize audio processor if not already done
      if (!audioProcessorRef.current) {
        await initializeAudioProcessor();
      }

      // Start voice session via API
      const response = await fetch(
        `/api/interviews/${interviewId}/voice/start`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_metadata: {
              audio_quality: "high",
              browser: navigator.userAgent,
              timestamp: new Date().toISOString(),
            },
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to start voice session");
      }

      const voiceSessionData: VoiceSessionData = await response.json();
      setSessionData(voiceSessionData);

      // Initialize AppSync Events client
      await initializeAppSyncConnection(voiceSessionData);

      setConnectionStatus((prev) => ({ ...prev, session: "active" }));
      if (onStatusChange) onStatusChange("active", "Voice session active");

      // Update template status elements
      if (typeof window !== "undefined" && (window as any).updateVoiceStatus) {
        (window as any).updateVoiceStatus("active", "Voice session active");
        (window as any).updateConnectionInfo(
          "Voice session is active. You can now speak with the AI interviewer."
        );
        (window as any).hideVoiceError();
      }
    } catch (error) {
      const errorMsg =
        error instanceof Error
          ? error.message
          : "Failed to start voice session";
      setErrorMessage(errorMsg);
      setConnectionStatus((prev) => ({ ...prev, session: "error" }));
      if (onError) onError(errorMsg);
      if (onStatusChange) onStatusChange("error", errorMsg);

      // Update template status elements
      if (typeof window !== "undefined" && (window as any).showVoiceError) {
        (window as any).showVoiceError(errorMsg);
      }
    }
  }, [interviewId, onStatusChange, onError, initializeAudioProcessor]);

  // Initialize AppSync connection
  const initializeAppSyncConnection = useCallback(
    async (voiceSessionData: VoiceSessionData) => {
      try {
        setConnectionStatus((prev) => ({ ...prev, appsync: "connecting" }));

        // Get auth token (this would typically come from Cognito)
        const authToken = await getAuthToken();

        appSyncClientRef.current = new AppSyncEventsClient(
          voiceSessionData.appsync_endpoint,
          voiceSessionData.appsync_channel,
          authToken
        );

        await appSyncClientRef.current.connect(
          handleAppSyncEvent,
          (connected) => {
            setConnectionStatus((prev) => ({
              ...prev,
              appsync: connected ? "connected" : "disconnected",
            }));
          },
          (error) => {
            setErrorMessage(`AppSync connection error: ${error}`);
            setConnectionStatus((prev) => ({ ...prev, appsync: "error" }));
            if (onError) onError(error);
          }
        );
      } catch (error) {
        const errorMsg = `Failed to connect to AppSync: ${
          error instanceof Error ? error.message : String(error)
        }`;
        setErrorMessage(errorMsg);
        setConnectionStatus((prev) => ({ ...prev, appsync: "error" }));
        if (onError) onError(errorMsg);
      }
    },
    [onError]
  );

  // Handle AppSync events
  const handleAppSyncEvent = useCallback(
    (event: AudioEvent) => {
      switch (event.type) {
        case "audio-output":
          handleAudioOutput(event.data);
          break;
        case "transcription":
          if (onTranscription) {
            onTranscription(event.data.text, event.data.isUser);
          }
          break;
        case "session-status":
          handleSessionStatus(event.data);
          break;
        case "error":
          setErrorMessage(event.data.message);
          if (onError) onError(event.data.message);
          break;
      }
    },
    [onTranscription, onError]
  );

  // Handle audio output from Nova Sonic
  const handleAudioOutput = useCallback(async (audioData: any) => {
    if (!audioProcessorRef.current) return;

    try {
      setIsPlaying(true);
      setConnectionStatus((prev) => ({ ...prev, audio: "playing" }));

      // Handle batched audio blobs from Nova Sonic (like reference implementation)
      if (audioData.blobs && Array.isArray(audioData.blobs)) {
        for (const blob of audioData.blobs) {
          const audioBuffer = base64ToArrayBuffer(blob);
          await audioProcessorRef.current.playAudio(audioBuffer);
        }
      }

      setIsPlaying(false);
      setConnectionStatus((prev) => ({ ...prev, audio: "inactive" }));
    } catch (error) {
      console.error("Error playing audio:", error);
      setIsPlaying(false);
      setConnectionStatus((prev) => ({ ...prev, audio: "error" }));
    }
  }, []);

  // Handle session status updates
  const handleSessionStatus = useCallback((statusData: any) => {
    if (statusData.status === "ended") {
      stopVoiceSession();
    }
  }, []);

  // Start recording
  const startRecording = useCallback(() => {
    if (!audioProcessorRef.current || !appSyncClientRef.current) return;

    try {
      setIsRecording(true);
      setConnectionStatus((prev) => ({ ...prev, audio: "recording" }));

      audioProcessorRef.current.startRecording(
        async (audioChunk) => {
          // Send audio chunk to AppSync Events with sequence number
          if (appSyncClientRef.current) {
            try {
              const sequenceNumber = audioChunkCount + 1;
              setAudioChunkCount(sequenceNumber);
              await appSyncClientRef.current.publishAudioInput(
                audioChunk,
                sequenceNumber
              );
            } catch (error) {
              console.error("Error sending audio chunk:", error);
            }
          }
        },
        (levelData) => {
          setAudioLevel(levelData);
        },
        (qualityMetrics) => {
          setAudioQuality(qualityMetrics);
          if (audioProcessorRef.current) {
            setQualityFeedback(audioProcessorRef.current.getQualityFeedback());
          }
        }
      );

      // Start audio level monitoring
      audioLevelIntervalRef.current = setInterval(() => {
        if (audioProcessorRef.current) {
          const level = audioProcessorRef.current.getAudioLevel();
          setAudioLevel((prev) => ({ ...prev, level, timestamp: Date.now() }));
        }
      }, 100);
    } catch (error) {
      console.error("Error starting recording:", error);
      setIsRecording(false);
      setConnectionStatus((prev) => ({ ...prev, audio: "error" }));
    }
  }, []);

  // Stop recording
  const stopRecording = useCallback(() => {
    if (!audioProcessorRef.current) return;

    setIsRecording(false);
    audioProcessorRef.current.stopRecording();
    setConnectionStatus((prev) => ({ ...prev, audio: "inactive" }));

    if (audioLevelIntervalRef.current) {
      clearInterval(audioLevelIntervalRef.current);
      audioLevelIntervalRef.current = null;
    }

    setAudioLevel({ level: 0, peak: 0, timestamp: Date.now() });
  }, []);

  // Stop voice session
  const stopVoiceSession = useCallback(async () => {
    try {
      setConnectionStatus((prev) => ({ ...prev, session: "ending" }));
      if (onStatusChange)
        onStatusChange("connecting", "Stopping voice session...");

      // Stop recording if active
      if (isRecording) {
        stopRecording();
      }

      // Stop voice session via API
      if (sessionData) {
        const response = await fetch(
          `/api/interviews/${interviewId}/voice/stop`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          console.error("Error stopping voice session:", errorData.error);
        }
      }

      // Disconnect AppSync
      if (appSyncClientRef.current) {
        appSyncClientRef.current.disconnect();
        appSyncClientRef.current = null;
      }

      // Cleanup audio processor
      if (audioProcessorRef.current) {
        audioProcessorRef.current.cleanup();
        audioProcessorRef.current = null;
      }

      setSessionData(null);
      setConnectionStatus({
        appsync: "disconnected",
        audio: "inactive",
        session: "inactive",
      });

      if (onStatusChange) onStatusChange("", "Voice session ended");

      // Update template status elements
      if (typeof window !== "undefined" && (window as any).updateVoiceStatus) {
        (window as any).updateVoiceStatus("", "Voice session ended");
        (window as any).updateConnectionInfo(
          "Voice session has ended. You can start a new session or switch to text mode."
        );
      }
    } catch (error) {
      console.error("Error stopping voice session:", error);
      const errorMsg = `Failed to stop voice session: ${
        error instanceof Error ? error.message : String(error)
      }`;
      setErrorMessage(errorMsg);
      if (onError) onError(errorMsg);
    }
  }, [
    interviewId,
    sessionData,
    isRecording,
    stopRecording,
    onStatusChange,
    onError,
  ]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioLevelIntervalRef.current) {
        clearInterval(audioLevelIntervalRef.current);
      }
      if (appSyncClientRef.current) {
        appSyncClientRef.current.disconnect();
      }
      if (audioProcessorRef.current) {
        audioProcessorRef.current.cleanup();
      }
    };
  }, []);

  // Helper function to get auth token
  const getAuthToken = async (): Promise<string> => {
    // This would typically get the token from Cognito or session storage
    // For now, we'll use a placeholder
    return "placeholder-auth-token";
  };

  // Helper function to convert base64 to ArrayBuffer
  const base64ToArrayBuffer = (base64: string): ArrayBuffer => {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  };

  // Render enhanced connection status indicator
  const renderConnectionStatus = () => {
    const getStatusColor = (status: string) => {
      switch (status) {
        case "connected":
        case "active":
          return "#4caf50";
        case "connecting":
        case "initializing":
        case "recording":
        case "playing":
          return "#ff9800";
        case "error":
          return "#f44336";
        default:
          return "#9e9e9e";
      }
    };

    const getStatusText = (type: string, status: string) => {
      if (type === "audio") {
        switch (status) {
          case "recording":
            return "Recording";
          case "playing":
            return "Playing";
          case "inactive":
            return "Ready";
          case "error":
            return "Error";
          default:
            return status;
        }
      }
      return status.charAt(0).toUpperCase() + status.slice(1);
    };

    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          marginBottom: "15px",
          padding: "10px",
          backgroundColor: "#f5f5f5",
          borderRadius: "8px",
        }}
      >
        <div style={{ display: "flex", gap: "15px", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <div
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                backgroundColor: getStatusColor(connectionStatus.session),
                boxShadow:
                  connectionStatus.session === "active"
                    ? "0 0 4px rgba(76, 175, 80, 0.6)"
                    : "none",
              }}
            />
            <span
              style={{ fontSize: "12px", color: "#333", fontWeight: "500" }}
            >
              Session: {getStatusText("session", connectionStatus.session)}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <div
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                backgroundColor: getStatusColor(connectionStatus.appsync),
                boxShadow:
                  connectionStatus.appsync === "connected"
                    ? "0 0 4px rgba(76, 175, 80, 0.6)"
                    : "none",
              }}
            />
            <span
              style={{ fontSize: "12px", color: "#333", fontWeight: "500" }}
            >
              Connection:{" "}
              {getStatusText("connection", connectionStatus.appsync)}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
            <div
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                backgroundColor: getStatusColor(connectionStatus.audio),
                boxShadow:
                  connectionStatus.audio === "recording" ||
                  connectionStatus.audio === "playing"
                    ? "0 0 4px rgba(255, 152, 0, 0.6)"
                    : "none",
              }}
            />
            <span
              style={{ fontSize: "12px", color: "#333", fontWeight: "500" }}
            >
              Audio: {getStatusText("audio", connectionStatus.audio)}
            </span>
          </div>
        </div>

        {/* Audio streaming info */}
        {isRecording && (
          <div
            style={{
              fontSize: "11px",
              color: "#666",
              display: "flex",
              gap: "15px",
            }}
          >
            <span>Chunks sent: {audioChunkCount}</span>
            <span>Format: 16kHz LPCM</span>
            <span>Quality: {audioQuality.qualityScore}%</span>
          </div>
        )}
      </div>
    );
  };

  // Render enhanced audio level and quality indicator
  const renderAudioLevel = () => {
    if (!isRecording && !isPlaying) return null;

    const getQualityColor = (score: number) => {
      if (score >= 80) return "#4caf50";
      if (score >= 60) return "#8bc34a";
      if (score >= 40) return "#ff9800";
      return "#f44336";
    };

    return (
      <div style={{ width: "100%", marginBottom: "15px" }}>
        {/* Audio Level */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: "5px",
          }}
        >
          <span style={{ fontSize: "12px", color: "#666" }}>
            {isRecording ? "Recording Level" : "Playback Level"}
          </span>
          <span style={{ fontSize: "12px", color: "#666" }}>
            {Math.round(audioLevel.level)}% (Peak: {Math.round(audioLevel.peak)}
            %)
          </span>
        </div>
        <div
          style={{
            width: "100%",
            height: "8px",
            backgroundColor: "#e0e0e0",
            borderRadius: "4px",
            overflow: "hidden",
            marginBottom: "8px",
          }}
        >
          <div
            style={{
              height: "100%",
              backgroundColor: isRecording ? "#4caf50" : "#2196f3",
              width: `${Math.min(audioLevel.level, 100)}%`,
              transition: "width 0.1s ease",
              borderRadius: "4px",
            }}
          />
        </div>

        {/* Audio Quality Indicator (only when recording) */}
        {isRecording && (
          <>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "5px",
              }}
            >
              <span style={{ fontSize: "12px", color: "#666" }}>
                Audio Quality
              </span>
              <span
                style={{
                  fontSize: "12px",
                  color: getQualityColor(audioQuality.qualityScore),
                }}
              >
                {Math.round(audioQuality.qualityScore)}%
              </span>
            </div>
            <div
              style={{
                width: "100%",
                height: "6px",
                backgroundColor: "#e0e0e0",
                borderRadius: "3px",
                overflow: "hidden",
                marginBottom: "8px",
              }}
            >
              <div
                style={{
                  height: "100%",
                  backgroundColor: getQualityColor(audioQuality.qualityScore),
                  width: `${Math.min(audioQuality.qualityScore, 100)}%`,
                  transition: "width 0.3s ease",
                  borderRadius: "3px",
                }}
              />
            </div>

            {/* Quality Details */}
            <div
              style={{
                fontSize: "10px",
                color: "#666",
                display: "flex",
                gap: "10px",
                marginBottom: "5px",
              }}
            >
              <span>SNR: {Math.round(audioQuality.snr)}dB</span>
              {audioQuality.clipping && (
                <span style={{ color: "#f44336" }}>⚠ Clipping</span>
              )}
              {audioQuality.silenceDetected && (
                <span style={{ color: "#ff9800" }}>🔇 Silence</span>
              )}
            </div>
          </>
        )}

        {/* Quality Feedback */}
        {qualityFeedback && isRecording && (
          <div
            style={{
              fontSize: "11px",
              color: audioQuality.qualityScore > 60 ? "#4caf50" : "#ff9800",
              marginTop: "5px",
              padding: "5px 8px",
              backgroundColor:
                audioQuality.qualityScore > 60 ? "#e8f5e8" : "#fff3e0",
              borderRadius: "4px",
              border: `1px solid ${
                audioQuality.qualityScore > 60 ? "#c8e6c9" : "#ffcc02"
              }`,
            }}
          >
            {qualityFeedback}
          </div>
        )}

        {/* Peak level warning */}
        {audioLevel.peak > 90 && (
          <div style={{ fontSize: "11px", color: "#f44336", marginTop: "5px" }}>
            ⚠ Audio level is too high - risk of distortion
          </div>
        )}
      </div>
    );
  };

  // Render control buttons
  const renderControls = () => {
    const isSessionActive = connectionStatus.session === "active";
    const isConnected = connectionStatus.appsync === "connected";
    const canRecord = isSessionActive && isConnected && !isPlaying;
    const canStartSession = connectionStatus.session === "inactive";

    return (
      <div
        style={{
          display: "flex",
          gap: "10px",
          justifyContent: "center",
          marginBottom: "15px",
        }}
      >
        {!isSessionActive ? (
          <button
            onClick={startVoiceSession}
            disabled={connectionStatus.session === "initializing"}
            className={`btn ${canStartSession ? "btn-primary" : "btn-secondary"}`}
          >
            {connectionStatus.session === "initializing"
              ? "Starting..."
              : "Start Interview"}
          </button>
        ) : (
          <>
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={!canRecord && !isRecording}
              style={{
                padding: "12px 24px",
                fontSize: "16px",
                border: "none",
                borderRadius: "25px",
                backgroundColor: isRecording
                  ? "#f44336"
                  : canRecord
                  ? "#4caf50"
                  : "#cccccc",
                color: "white",
                cursor: canRecord || isRecording ? "pointer" : "not-allowed",
                minWidth: "120px",
              }}
            >
              {isRecording ? "Stop Recording" : "Start Recording"}
            </button>
            <button
              onClick={stopVoiceSession}
              disabled={connectionStatus.session === "ending"}
              style={{
                padding: "12px 24px",
                fontSize: "16px",
                border: "none",
                borderRadius: "25px",
                backgroundColor: "#ff9800",
                color: "white",
                cursor: "pointer",
                minWidth: "120px",
              }}
            >
              {connectionStatus.session === "ending"
                ? "Ending..."
                : "End Session"}
            </button>
          </>
        )}
      </div>
    );
  };

  return (
    <div
      style={{
        padding: "20px",
        border: "2px solid #e0e0e0",
        borderRadius: "10px",
        backgroundColor: "#f9f9f9",
        maxWidth: "600px",
        margin: "0 auto",
      }}
    >
      <h3 style={{ textAlign: "center", marginBottom: "20px", color: "#333" }}>
        Voice Interview Interface
      </h3>

      {renderAudioLevel()}
      {renderControls()}

      {errorMessage && (
        <div
          style={{
            backgroundColor: "#ffebee",
            color: "#f44336",
            padding: "10px",
            borderRadius: "5px",
            marginTop: "15px",
            textAlign: "center",
            fontSize: "14px",
          }}
        >
          {errorMessage}
        </div>
      )}

      <div
        style={{
          fontSize: "12px",
          color: "#666",
          textAlign: "center",
          marginTop: "15px",
          lineHeight: "1.4",
        }}
      >
        {connectionStatus.session === "inactive" && (
          <>
            Click "Start Interview" to begin. Make sure your microphone is
            enabled and you're in a quiet environment.
          </>
        )}
        {connectionStatus.session === "active" && !isRecording && (
          <>
            Session is active. Click "Start Recording" to begin speaking with
            the AI interviewer.
          </>
        )}
        {isRecording && (
          <>
            Recording in progress. Speak clearly into your microphone. The AI
            will respond when you stop recording.
          </>
        )}
        {isPlaying && (
          <>
            AI is responding. Please wait for the response to complete before
            recording again.
          </>
        )}
      </div>
    </div>
  );
};

export default VoiceInterface;
