import { log } from '../common/logger';
import { events, EventsChannel } from 'aws-amplify/data';
import { ModelStreamErrorException } from '@aws-sdk/client-bedrock-runtime';
import { DispatchEventParams, SpeechToSpeechEvent, SpeechToSpeechEventSchema } from '../common/schemas';
import { NovaStream } from './nova-stream';
import './amplify';
import { AudioEventSequencer } from '../common/events';
import { appendVoiceTranscriptionEntry, closeDbConnection } from '../common/database';

const MIN_AUDIO_OUTPUT_QUEUE_SIZE = 10;
const MAX_AUDIO_OUTPUT_PER_BATCH = 20;
let audioOutputQueue: string[] = [];
let unprocessedClientEvents: SpeechToSpeechEvent[] = [];
let audioOutputSequence = 0;

export const dispatchEvent = async (channel: EventsChannel, params: DispatchEventParams) => {
  try {
    await channel.publish({
      direction: 'btoc',
      ...params,
    });
  } catch (e) {
    log.info('Failed to publish the event via channel. The channel might be closed', { event: params.event, data: params.data });
    log.error('Event publish error:', e);
  }
};

// Send Nova's audio output to frontend in batches
// Without batching, playback tends to be choppy on the frontend
const enqueueAudioOutput = async (channel: EventsChannel, audioOutput: string) => {
  audioOutputQueue.push(audioOutput);

  if (audioOutputQueue.length > MIN_AUDIO_OUTPUT_QUEUE_SIZE) {
    const chunksToProcess: string[] = [];

    let processedChunks = 0;

    while (audioOutputQueue.length > 0 && processedChunks < MAX_AUDIO_OUTPUT_PER_BATCH) {
      const chunk = audioOutputQueue.shift();

      if (chunk) {
        chunksToProcess.push(chunk);
        processedChunks += 1;
      }
    }

    await dispatchEvent(channel, {
      event: 'audioOutput',
      data: { blobs: chunksToProcess, sequence: audioOutputSequence },
    });
    audioOutputSequence++;
  }
};

const forcePublishAudioOutput = async (channel: EventsChannel) => {
  const chunksToProcess = [];

  while (audioOutputQueue.length > 0) {
    const chunk = audioOutputQueue.shift();
    if (chunk) {
      chunksToProcess.push(chunk);
    }
  }

  await dispatchEvent(channel, {
    event: 'audioOutput',
    data: { blobs: chunksToProcess, sequence: audioOutputSequence },
  });
  audioOutputSequence++;
};

export const initializeSubscription = async (channelPath: string, context: { stream?: NovaStream }) => {
  audioOutputQueue = [];
  unprocessedClientEvents = [];
  audioOutputSequence = 0;
  const channel = await events.connect(channelPath);
  let clientInitialized = false;
  log.info(`Connected to the event channel ${channelPath}`);
  const sequencer = new AudioEventSequencer((chunks) => {
    context.stream!.enqueueAudioInput(chunks);
  });

  const processEventsFromClient = (event: SpeechToSpeechEvent) => {
    const stream = context.stream;
    // Queue items during session reconnection
    if (!stream?.isProcessing) {
      unprocessedClientEvents.push(event);
      return;
    }
    const events = [...unprocessedClientEvents, event];
    for (const event of events) {
      if (event.direction !== 'ctob') {
        continue;
      }
      clientInitialized = true;
      if (event.event === 'audioInput') {
        sequencer.next(event.data.blobs, event.data.sequence);
      } else if (event.event === 'terminateSession') {
        stream.close();
      }
    }
    unprocessedClientEvents = [];
  };

  channel.subscribe({
    next: async (data: { event: unknown }) => {
      const { data: event, error } = SpeechToSpeechEventSchema.safeParse(data.event);
      if (error) {
        log.error('Schema validation error:', error);
        return;
      }
      if (!['audioInput'].includes(event.event)) {
        log.info(JSON.stringify(event));
      }
      processEventsFromClient(event);
    },
    error: (err: any) => log.error('Channel subscription error:', err),
  });

  // Periodically send ready event until client is also ready
  const readyAt = Date.now();
  const readyInterval = setInterval(async () => {
    if (Date.now() - readyAt > 60 * 1000) {
      clearInterval(readyInterval);
      log.info('client did not respond. stopping ready events.');
      return;
    }
    if (clientInitialized) {
      clearInterval(readyInterval);
      log.info('ctob event received, stopping ready event dispatcher');
      return;
    }

    try {
      await dispatchEvent(channel!, { event: 'ready', data: {} });
      log.info("I'm ready");
    } catch (error) {
      log.error('Failed to dispatch ready event:', error);
    }
  }, 1000);

  return channel;
};

export const processResponseStream = async (
  channel: EventsChannel,
  stream: NovaStream,
  sessionId: string,
  invokedAt: number,
  interviewId?: string
): Promise<{ state: 'success' | 'error' | 'resume' }> => {
  log.info(`[VOICE DEBUG] Starting processResponseStream for session ${sessionId}`);
  log.info(`[VOICE DEBUG] Interview ID: ${interviewId || 'NOT PROVIDED'}`);

  const startedAt = Date.now();
  const willResumeIn = Math.floor(Math.random() * 330 + 120); // 120 to 450 seconds

  const contents: { [key: string]: { role: string; content: string; isFinal: boolean } } = {};
  const toolUses: { [key: string]: { toolUseId: string; content: string; toolName: string } } = {};

  // Track conversation for database storage
  let currentQuestion = '';
  let pendingAssistantContent = '';
  let pendingUserContent = '';
  let lastRole = '';
  let isFirstUserMessage = true;
  let conversationCount = 0;

  log.info(`[VOICE DEBUG] Initialized conversation tracking variables`);

  for await (const event of stream.iterator) {
    try {
      if (event.chunk?.bytes) {
        const textResponse = new TextDecoder().decode(event.chunk.bytes);
        const jsonResponse = JSON.parse(textResponse);
        if (!['audioOutput'].some((type) => type in jsonResponse.event)) {
          log.info(textResponse);
        }

        if (jsonResponse.event?.audioOutput) {
          await enqueueAudioOutput(channel, jsonResponse.event.audioOutput.content);
        } else if (jsonResponse.event?.contentEnd && jsonResponse.event?.contentEnd?.type === 'AUDIO') {
          await forcePublishAudioOutput(channel);
        } else if (jsonResponse.event?.contentStart && jsonResponse.event?.contentStart?.type === 'TEXT') {
          let generationStage = null;

          if (jsonResponse.event?.contentStart?.additionalModelFields) {
            generationStage = JSON.parse(jsonResponse.event?.contentStart?.additionalModelFields).generationStage;
          }
          contents[jsonResponse.event?.contentStart?.contentId as string] = {
            role: jsonResponse.event?.contentStart?.role?.toLowerCase(),
            content: '',
            isFinal: generationStage == 'FINAL',
          };

          log.info(`[VOICE DEBUG] Content start - Role: ${jsonResponse.event?.contentStart?.role?.toLowerCase()}, Stage: ${generationStage}, Final: ${generationStage == 'FINAL'}`);

          await dispatchEvent(channel, {
            event: 'textStart',
            data: {
              id: jsonResponse.event?.contentStart?.contentId,
              role: jsonResponse.event?.contentStart?.role?.toLowerCase(),
              generationStage,
            },
          });
        } else if (jsonResponse.event?.textOutput) {
          const role = jsonResponse.event?.textOutput?.role?.toLowerCase();
          const content = jsonResponse.event?.textOutput?.content || '';

          const existingContent = contents[jsonResponse.event?.textOutput?.contentId as string];
          if (content != '{ "interrupted" : true }') {
            existingContent.content += content;
          }

          await dispatchEvent(channel, {
            event: 'textOutput',
            data: {
              id: jsonResponse.event?.textOutput?.contentId,
              role: role,
              content: jsonResponse.event?.textOutput?.content,
            },
          });
        } else if (jsonResponse.event?.contentEnd && jsonResponse.event?.contentEnd?.type === 'TEXT') {
          const existingContent = contents[jsonResponse.event?.contentEnd?.contentId as string];

          await dispatchEvent(channel, {
            event: 'textStop',
            data: {
              id: jsonResponse.event?.contentEnd?.contentId,
              stopReason: jsonResponse.event?.contentEnd?.stopReason,
            },
          });

          try {
            log.info(`[VOICE DEBUG] Content end - Role: ${existingContent.role}, Stop reason: ${jsonResponse.event?.contentEnd?.stopReason}, Is final: ${existingContent.isFinal}`);

            // Only process FINAL content (not speculative)
            if (existingContent.isFinal && existingContent.content) {
              const cleanContent = existingContent.content.replace(/  /g, ' ').trim();
              log.info(`[VOICE DEBUG] Processing FINAL message - Role: ${existingContent.role}, Content: "${cleanContent}"`);

              // Check if role changed - if so, save previous accumulated content
              if (lastRole && lastRole !== existingContent.role) {
                log.info(`[VOICE DEBUG] Role change detected: ${lastRole} -> ${existingContent.role}`);

                if (lastRole === 'user' && pendingUserContent) {
                  if (isFirstUserMessage) {
                    log.info(`[VOICE DEBUG] Ignoring initial user greeting: "${pendingUserContent}"`);
                    isFirstUserMessage = false;
                  } else if (currentQuestion && interviewId) {
                    log.info(`[VOICE DEBUG] Saving complete user response: "${pendingUserContent}"`);
                    try {
                      await appendVoiceTranscriptionEntry(interviewId, currentQuestion, pendingUserContent);
                      conversationCount++;
                      log.info(`[VOICE DEBUG] ✅ Successfully saved Q&A pair #${conversationCount}`);
                      log.info(`[VOICE DEBUG] ✅ Q: "${currentQuestion}"`);
                      log.info(`[VOICE DEBUG] ✅ A: "${pendingUserContent}"`);
                      currentQuestion = '';
                    } catch (error) {
                      log.error(`[VOICE DEBUG] ❌ Failed to save Q&A to database:`, error);
                    }
                  }
                  pendingUserContent = '';
                } else if (lastRole === 'assistant' && pendingAssistantContent) {
                  currentQuestion = pendingAssistantContent;
                  log.info(`[VOICE DEBUG] Set complete question: "${currentQuestion}"`);
                  pendingAssistantContent = '';
                }
              }

              // Accumulate content for current role
              if (existingContent.role === 'user') {
                pendingUserContent += (pendingUserContent ? ' ' : '') + cleanContent;
                log.info(`[VOICE DEBUG] Accumulated user content: "${pendingUserContent}"`);
              } else if (existingContent.role === 'assistant') {
                pendingAssistantContent += (pendingAssistantContent ? ' ' : '') + cleanContent;
                log.info(`[VOICE DEBUG] Accumulated assistant content: "${pendingAssistantContent}"`);

                // Check for END_TURN to manage session
                if (jsonResponse.event?.contentEnd?.stopReason === 'END_TURN') {
                  log.info(`[VOICE DEBUG] Assistant END_TURN detected`);

                  if (Date.now() - invokedAt > 1000 * 60 * 10) {
                    log.info(`[VOICE DEBUG] Session timeout reached (10 minutes), ending session`);
                    return { state: 'success' };
                  }
                  if (Date.now() - startedAt > 1000 * willResumeIn) {
                    log.info(`[VOICE DEBUG] Resume timeout reached (${willResumeIn}s), resuming session`);
                    return { state: 'resume' };
                  }
                }
              }

              lastRole = existingContent.role;
            } else {
              log.info(`[VOICE DEBUG] Skipping non-final or empty content - Role: ${existingContent.role}, Final: ${existingContent.isFinal}, Content length: ${existingContent.content?.length || 0}`);
            }
          } catch (error) {
            log.error(`[VOICE DEBUG] ❌ Error processing message:`, error);
          }
        } else if (jsonResponse.event?.toolUse) {
          // Store tool use information for later
          toolUses[jsonResponse.event.toolUse.contentId] = {
            toolUseId: jsonResponse.event.toolUse.toolUseId,
            toolName: jsonResponse.event.toolUse.toolName,
            content: jsonResponse.event.toolUse.content,
          };
        } else if (jsonResponse.event?.contentEnd && jsonResponse.event?.contentEnd?.type === 'TOOL') {
          const toolUse = toolUses[jsonResponse.event.contentEnd.contentId];
          const result = await stream.executeToolAndSendResult(toolUse.toolUseId, toolUse.toolName, toolUse.content);
        }
      }
    } catch (e) {
      log.error(`[VOICE DEBUG] ❌ Error in processResponseStream:`, e);

      if (e instanceof ModelStreamErrorException) {
        log.info(`[VOICE DEBUG] Model stream error, retrying...`);
      } else {
        log.error(`[VOICE DEBUG] ❌ Non-recoverable error, returning error state`);
        return { state: 'error' };
      }
    }
  }

  // Clean up database connection when stream ends
  log.info(`[VOICE DEBUG] Stream ended, cleaning up database connection`);
  log.info(`[VOICE DEBUG] Total conversation pairs saved: ${conversationCount}`);

  try {
    await closeDbConnection();
    log.info(`[VOICE DEBUG] ✅ Database connection closed successfully`);
  } catch (error) {
    log.error(`[VOICE DEBUG] ❌ Error closing database connection:`, error);
  }

  log.info(`[VOICE DEBUG] processResponseStream completed successfully`);
  return { state: 'success' };
};
