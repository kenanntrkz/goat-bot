FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p data/config data/leads/raw data/leads/qualified \
    data/campaigns data/proposals data/classroom \
    outputs/reports outputs/creatives
EXPOSE 7778
CMD ["python", "app.py"]
