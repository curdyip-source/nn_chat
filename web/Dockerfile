# --- build stage ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
RUN npm run build

# --- runtime stage (nginx) ---
FROM nginx:1.29-alpine
COPY --chown=root:root --chmod=644 nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build --chown=root:root /app/dist /usr/share/nginx/html
RUN chmod 755 /usr/share/nginx /usr/share/nginx/html \
	&& find /usr/share/nginx/html -type d -exec chmod 755 {} \; \
	&& find /usr/share/nginx/html -type f -exec chmod 644 {} \;
