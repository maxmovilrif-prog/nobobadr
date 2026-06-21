# ---- Nubo Frontend (React + craco) ----
# Stage 1: build static assets
FROM node:20-alpine AS builder

WORKDIR /app/frontend

# CRA bakes REACT_APP_* vars at BUILD time -> pass them as build args
ARG REACT_APP_BACKEND_URL
ARG REACT_APP_GOOGLE_MAPS_API_KEY
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL \
    REACT_APP_GOOGLE_MAPS_API_KEY=$REACT_APP_GOOGLE_MAPS_API_KEY \
    REACT_APP_ENABLE_VISUAL_EDITS=false \
    WDS_SOCKET_PORT=0 \
    NODE_OPTIONS=--max-old-space-size=2048

COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile

COPY frontend/ ./
RUN yarn build

# Stage 2: serve with nginx
FROM nginx:1.27-alpine
# Built static site
COPY --from=builder /app/frontend/build /usr/share/nginx/html
# Our server config (serves SPA + proxies /api to backend)
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]
