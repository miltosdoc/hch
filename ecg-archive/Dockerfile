FROM python:3.12-slim

WORKDIR /app
COPY ecg-archive/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ecg-archive/ /app/
COPY shared/ /app/shared/

RUN mkdir -p /app/ecgs /app/static

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
