/**
 * Voice Lambda Function Entry Point
 * Uses reference implementation directly
 */

import { main } from './src/agent';

export const handler = async (event: any, context: any) => {
	console.log('[LAMBDA DEBUG] Voice Lambda invoked:', JSON.stringify(event, null, 2));

	try {
		// Only handle session-start events with the continuous session pattern
		if (event.eventType === 'session-start') {
			const { userId, sessionId, systemPrompt, voiceId, interviewId } = event;

			console.log(`[LAMBDA DEBUG] Extracted parameters:`);
			console.log(`[LAMBDA DEBUG] - userId: ${userId}`);
			console.log(`[LAMBDA DEBUG] - sessionId: ${sessionId}`);
			console.log(`[LAMBDA DEBUG] - voiceId: ${voiceId}`);
			console.log(`[LAMBDA DEBUG] - interviewId: ${interviewId || 'NOT PROVIDED'}`);
			console.log(`[LAMBDA DEBUG] - systemPrompt length: ${systemPrompt?.length || 0} characters`);

			if (!interviewId) {
				console.warn(`[LAMBDA DEBUG] ⚠️ WARNING: No interviewId provided - database updates will be skipped`);
			}

			// Use reference implementation main function - this runs continuously
			console.log(`[LAMBDA DEBUG] Calling main() with interviewId: ${interviewId}`);
			await main(sessionId, userId, systemPrompt, voiceId, interviewId);

			console.log(`[LAMBDA DEBUG] ✅ Voice session completed successfully`);
			return {
				statusCode: 200,
				body: JSON.stringify({
					success: true,
					sessionId,
					message: 'Voice session completed'
				})
			};
		}

		// Ignore other events - they're handled by the continuous session
		console.log(`[LAMBDA DEBUG] Ignoring event type: ${event.eventType}`);
		return {
			statusCode: 200,
			body: JSON.stringify({
				message: 'Event ignored - handled by active session'
			})
		};

	} catch (error) {
		console.error('[LAMBDA DEBUG] ❌ Voice Lambda error:', error);
		console.error('[LAMBDA DEBUG] ❌ Error stack:', error instanceof Error ? error.stack : 'No stack trace');

		return {
			statusCode: 500,
			body: JSON.stringify({
				error: 'Voice processing failed',
				message: error instanceof Error ? error.message : 'Unknown error'
			})
		};
	}
};
