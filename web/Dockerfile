FROM ai-chatbot.base:0.1.0

WORKDIR /app
RUN mkdir -p ./tmp && chmod 777 ./tmp
ENV TMPDIR=/app/tmp
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0

COPY ./shared/ ./shared/
COPY ./web/ ./web/

WORKDIR /app/web
EXPOSE 8080
CMD ["python", "-u", "main.py"]
