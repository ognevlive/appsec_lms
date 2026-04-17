FROM python:3.12-alpine

RUN pip install --no-cache-dir flask markupsafe

WORKDIR /app
COPY app.py .

ENV CTF_FLAG="FLAG{stored_xss_cookie_theft}"

EXPOSE 80

CMD ["python", "app.py"]
