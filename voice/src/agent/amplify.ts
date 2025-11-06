import { fromNodeProviderChain } from '@aws-sdk/credential-providers';
import { Amplify } from 'aws-amplify';

// eslint-disable-next-line @typescript-eslint/no-require-imports
Object.assign(global, { WebSocket: require('ws') });

Amplify.configure(
  {
    API: {
      Events: {
        endpoint: `${process.env.APPSYNC_EVENTS_ENDPOINT!}/event`,
        region: process.env.AWS_REGION!,
        defaultAuthMode: 'iam',
      },
    },
  },
  {
    Auth: {
      credentialsProvider: {
        getCredentialsAndIdentityId: async () => {
          const provider = fromNodeProviderChain();
          const credentials = await provider();
          return {
            credentials,
          };
        },
        clearCredentialsAndIdentityId: async () => {},
      },
    },
  }
);
