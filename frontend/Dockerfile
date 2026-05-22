FROM nginx:1.29-alpine

COPY --chown=root:root --chmod=644 nginx.conf /etc/nginx/conf.d/default.conf
COPY --chown=root:root --chmod=644 index.html /usr/share/nginx/html/index.html
COPY --chown=root:root --chmod=644 assets /usr/share/nginx/html/assets

RUN chmod 755 /usr/share/nginx /usr/share/nginx/html