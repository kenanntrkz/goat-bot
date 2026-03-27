#!/bin/bash
cd /root/goat-bot && git pull origin main && \
docker build -t goat-bot . && \
docker rm -f goat-bot && \
docker run -d --name goat-bot -p 7778:7778 \
  --env-file /root/goat-bot/.env \
  -v /root/goat-bot-data:/app/data \
  --restart unless-stopped goat-bot
