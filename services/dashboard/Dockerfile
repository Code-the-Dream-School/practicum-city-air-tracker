FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY services/dashboard/frontend/package.json ./package.json
COPY services/dashboard/frontend/vite.config.js ./vite.config.js
COPY services/dashboard/frontend/index.html ./index.html
COPY services/dashboard/frontend/src ./src
RUN npm install
RUN npm run build

FROM python:3.11-slim

WORKDIR /app
COPY services/dashboard/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/dashboard/server.py /app/server.py
COPY --from=frontend-builder /frontend/dist /app/static
EXPOSE 8501
CMD ["python", "server.py"]
