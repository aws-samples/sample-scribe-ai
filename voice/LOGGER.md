# Logger Configuration

This project uses Winston for structured logging with configurable log levels.

## Usage

```typescript
import { log } from './common/logger';

// Log levels (in order of severity)
log.debug('Detailed debug information', { userId: '123', action: 'login' });
log.info('General information', { status: 'success' });
log.warn('Warning message', { retryCount: 3 });
log.error('Error occurred', { error: error.message, stack: error.stack });
```

## Configuration

Set the `LOG_LEVEL` environment variable to control logging output:

- `debug` - Shows all logs (debug, info, warn, error)
- `info` - Shows info, warn, error (default)
- `warn` - Shows warn, error only
- `error` - Shows error only

## Lambda Environment

In AWS Lambda, set the environment variable:
```
LOG_LEVEL=debug  # For debugging
LOG_LEVEL=info   # For production
```

## Output Format

Logs are output in JSON format for CloudWatch compatibility:
```json
{
  "timestamp": "2025-09-03T15:05:57.634Z",
  "level": "info",
  "message": "Successfully appended Q&A to interview abc123",
  "interviewId": "abc123",
  "questionCount": 5
}
```
