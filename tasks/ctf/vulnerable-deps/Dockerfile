FROM python:3.12-alpine

RUN pip install --no-cache-dir flask

WORKDIR /app
COPY app.py .

ENV CTF_FLAG="FLAG{CVE-2021-44228}"

EXPOSE 80

CMD ["python", "app.py"]
