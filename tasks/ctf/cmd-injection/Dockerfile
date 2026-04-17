FROM python:3.12-alpine

RUN apk add --no-cache iputils && \
    pip install --no-cache-dir flask

WORKDIR /app
COPY app.py .

# Place the flag in a file on the filesystem
RUN echo "FLAG{command_injection_rce_achieved}" > /flag.txt && \
    chmod 444 /flag.txt

EXPOSE 80

CMD ["python", "app.py"]
