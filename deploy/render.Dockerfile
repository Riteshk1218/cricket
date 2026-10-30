# One container for Render: builds the website, then runs Django (API +
# WebSockets) which also serves the website from the same address.
FROM node:22-alpine AS website
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
# The website calls the API on its own address (no separate API URL needed).
ENV VITE_SAME_ORIGIN=true
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FRONTEND_DIST=/app/website
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=website /web/dist /app/website
RUN python manage.py collectstatic --noinput && chmod +x render-start.sh
CMD ["./render-start.sh"]
