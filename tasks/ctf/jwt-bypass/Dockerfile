FROM python:3.12-alpine

RUN pip install --no-cache-dir flask

WORKDIR /app
COPY app.py .

ENV CTF_FLAG="FLAG{jwt_none_algorithm_bypass}"

EXPOSE 80

CMD ["python", "app.py"]
