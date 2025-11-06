# Build stage for React app
FROM node:22-alpine AS react-builder
WORKDIR /build/voice-interview-react
COPY ./web/voice-interview-react/package*.json ./
RUN npm ci
COPY ./web/voice-interview-react/ ./
RUN npm run build

# Final stage
FROM ai-chatbot.base:0.1.0

WORKDIR /app
RUN mkdir -p ./tmp && chmod 777 ./tmp
ENV TMPDIR=/app/tmp
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0

COPY ./shared/ ./shared/
COPY ./web/ ./web/

# Copy compiled React files from build stage (webpack outputs to ../static/js relative to voice-interview-react dir)
COPY --from=react-builder /build/static/js/voice-interface.js* ./web/static/js/

WORKDIR /app/web
EXPOSE 8080
CMD ["gunicorn", \
    "--bind", "0.0.0.0:8080", \
    "--workers", "1", \
    "--threads", "4", \
    "--worker-class", "gthread", \
    "main:app"]
