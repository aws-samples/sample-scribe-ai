import { Client } from 'pg';
import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';
import { log } from './logger';

interface DatabaseCredentials {
  username: string;
  password: string;
}

let dbClient: Client | null = null;
let credentials: DatabaseCredentials | null = null;

async function getCredentials(): Promise<DatabaseCredentials> {
  if (credentials) {
    return credentials;
  }

  const secretsClient = new SecretsManagerClient({ region: process.env.AWS_REGION });
  const command = new GetSecretValueCommand({
    SecretId: process.env.DB_SECRET_ARN
  });

  try {
    const response = await secretsClient.send(command);
    const secret = JSON.parse(response.SecretString || '{}');
    credentials = {
      username: secret.username,
      password: secret.password
    };
    return credentials;
  } catch (error) {
    log.error('Failed to get database credentials:', error);
    throw error;
  }
}

async function getDbClient(): Promise<Client> {
  if (dbClient) {
    return dbClient;
  }

  const creds = await getCredentials();

  dbClient = new Client({
    host: process.env.POSTGRES_HOST,
    database: process.env.POSTGRES_DB,
    user: creds.username,
    password: creds.password,
    port: 5432,
    ssl: { rejectUnauthorized: false }
  });

  await dbClient.connect();
  return dbClient;
}

export async function appendVoiceTranscriptionEntry(interviewId: string, question: string, answer: string): Promise<void> {
  log.debug(`Starting appendVoiceTranscriptionEntry for interview ${interviewId}`);
  log.debug(`Question: "${question}"`);
  log.debug(`Answer: "${answer}"`);

  const client = await getDbClient();
  log.debug(`Database client obtained successfully`);

  // First, get current data to see what we're working with
  const selectQuery = `SELECT data FROM interview WHERE id = $1`;
  log.debug(`Fetching current data with query: ${selectQuery}`);

  try {
    const currentResult = await client.query(selectQuery, [interviewId]);
    log.debug(`Current data query result:`, currentResult.rows);

    if (currentResult.rows.length === 0) {
      log.error(`No interview found with id ${interviewId}`);
      throw new Error(`Interview not found: ${interviewId}`);
    }

    const currentData = currentResult.rows[0].data || [];
    log.debug(`Current interview data:`, JSON.stringify(currentData, null, 2));

    // Create new Q&A entry
    const newEntry = { q: question, a: answer };
    log.debug(`New entry to append:`, JSON.stringify(newEntry, null, 2));

    // Append to existing data
    const updatedData = [...currentData, newEntry];
    log.debug(`Updated data array:`, JSON.stringify(updatedData, null, 2));

    // Update the database
    const updateQuery = `UPDATE interview SET data = $1::jsonb WHERE id = $2`;
    const values = [JSON.stringify(updatedData), interviewId];

    log.debug(`Update query: ${updateQuery}`);
    log.debug(`Update values:`, values);

    const updateResult = await client.query(updateQuery, values);
    log.debug(`Update result:`, updateResult);
    log.debug(`Rows affected: ${updateResult.rowCount}`);

    if (updateResult.rowCount === 0) {
      log.error(`No rows updated for interview ${interviewId}`);
      throw new Error(`Failed to update interview: ${interviewId}`);
    }

    log.info(`Successfully appended Q&A to interview ${interviewId}`);
    log.debug(`Total questions now: ${updatedData.length}`);

  } catch (error) {
    log.error(`Database operation failed:`, error);
    log.error(`Error details:`, {
      message: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined
    });
    throw error;
  }
}

export async function closeDbConnection(): Promise<void> {
  if (dbClient) {
    await dbClient.end();
    dbClient = null;
    credentials = null;
  }
}
