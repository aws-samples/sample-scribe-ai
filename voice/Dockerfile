# Voice Lambda Dockerfile for Nova Sonic Integration
FROM public.ecr.aws/lambda/nodejs:22

# Copy package.json and package-lock.json
COPY package*.json ${LAMBDA_TASK_ROOT}/
COPY tsconfig.json ${LAMBDA_TASK_ROOT}/

# Install all dependencies (including dev dependencies for build)
RUN npm ci

# Copy TypeScript source code
COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY index.ts ${LAMBDA_TASK_ROOT}/

# Build TypeScript to JavaScript
RUN npm run build

# Remove dev dependencies to reduce image size
RUN npm ci --only=production && npm cache clean --force

# Set the CMD to your handler (now pointing to compiled JS)
CMD [ "dist/index.handler" ]