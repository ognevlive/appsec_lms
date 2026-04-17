FROM python:3.12-alpine

RUN pip install --no-cache-dir flask

WORKDIR /app
COPY app.py .

ENV CTF_FLAG="FLAG{sast_found_6_vulnerabilities}"

EXPOSE 80

CMD ["python", "app.py"]
