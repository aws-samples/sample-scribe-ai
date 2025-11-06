import { z } from 'zod';

export interface ToolDefinition<T> {
  name: string;
  schema: z.ZodSchema<T>;
  handler: (input: T, context: any) => Promise<string>;
  toolSpec: () => any;
}

export const createTool = <T>(
  name: string,
  description: string,
  schema: z.ZodSchema<T>,
  handler: (input: T, context: any) => Promise<string>
): ToolDefinition<T> => ({
  name,
  schema,
  handler,
  toolSpec: () => ({
    name,
    description,
    inputSchema: {
      json: schema,
    },
  }),
});
