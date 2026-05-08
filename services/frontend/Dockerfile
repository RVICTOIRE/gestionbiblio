FROM nginx:1.25-alpine

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY index.html /usr/share/nginx/html/
COPY static/ /usr/share/nginx/html/static/
COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN chown -R appuser:appgroup /usr/share/nginx/html \
    && chown -R appuser:appgroup /var/cache/nginx \
    && touch /var/run/nginx.pid \
    && chown appuser:appgroup /var/run/nginx.pid

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
