import { log } from '../common/logger';
import type { EventsChannel } from 'aws-amplify/data';
import { NovaStream } from './nova-stream';
import './amplify';
import { dispatchEvent, processResponseStream, initializeSubscription } from './events';

export const main = async (sessionId: string, userId: string, systemPrompt: string, voiceId: string, interviewId?: string) => {
  log.info(`[AGENT DEBUG] Starting main() function`);
  log.info(`[AGENT DEBUG] - sessionId: ${sessionId}`);
  log.info(`[AGENT DEBUG] - userId: ${userId}`);
  log.info(`[AGENT DEBUG] - voiceId: ${voiceId}`);
  log.info(`[AGENT DEBUG] - interviewId: ${interviewId || 'NOT PROVIDED'}`);
  log.info(`[AGENT DEBUG] - systemPrompt length: ${systemPrompt?.length || 0} characters`);

  let channel: EventsChannel | undefined = undefined;
  const context: { stream?: NovaStream } = {};
  const startedAt = Date.now();
  let endReason = '';

  try {
    log.info(`[AGENT DEBUG] ✅ Voice configuration found for ${voiceId}`);
    log.info(`[AGENT DEBUG] Session ${sessionId} initialized`);

    const channelPath = `/nova-sonic-voice/user/${userId}/${sessionId}`;
    log.info(`[AGENT DEBUG] Initializing subscription to channel: ${channelPath}`);
    channel = await initializeSubscription(channelPath, context);

    log.info('[AGENT DEBUG] ✅ Subscribed to the channel');

    // Without this sleep, the error below is sometimes thrown
    // "Subscription has not been initialized"
    await new Promise((s) => setTimeout(s, 1000));

    const tools: any[] = [];

    // Start response stream
    while (true) {
      log.info('[AGENT DEBUG] Starting/resuming a session');
      const chatHistory: { content: string; role: string }[] = []; // No persistence for now
      const stream = new NovaStream(voiceId, systemPrompt, tools);
      context.stream = stream;
      await stream.open(chatHistory);

      log.info(`[AGENT DEBUG] Calling processResponseStream with interviewId: ${interviewId}`);
      const res = await processResponseStream(channel, stream, sessionId, startedAt, interviewId);

      stream.close();
      if (res.state == 'success') {
        log.info(`[AGENT DEBUG] ✅ Session finished with state ${res.state}`);
        break;
      }
      log.info(`[AGENT DEBUG] Session state: ${res.state}, resuming in next loop`);
      // resume the session in the next loop
    }
  } catch (e) {
    log.error('[AGENT DEBUG] ❌ Error in main process:', e);
    log.error('[AGENT DEBUG] ❌ Error stack:', e instanceof Error ? e.stack : 'No stack trace');
    endReason = (e as any).message ?? 'Internal Server Error';
  } finally {
    try {
      if (channel) {
        log.info('[AGENT DEBUG] Sending "end" event...');
        await dispatchEvent(channel, { event: 'end', data: { reason: endReason } });

        log.info('[AGENT DEBUG] Closing the channel');
        channel.close();
      }

      log.info('[AGENT DEBUG] ✅ Session ended successfully');
    } catch (e) {
      log.error('[AGENT DEBUG] ❌ Error during finalization:', e);
    }
  }
};
