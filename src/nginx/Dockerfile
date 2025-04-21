FROM nginx:1.27.4-alpine3.21

COPY certbot_start.sh /usr/local/bin/certbot_start.sh

RUN apk update && \
    apk add --no-cache certbot certbot-nginx shadow && \
    addgroup -g 33 www && \
    adduser -D -u 33 -G www www-data && \    
    chmod +x /usr/local/bin/certbot_start.sh && \
    mkdir -p \
        /var/log/nginx \
        /var/cache/nginx \
        /run/nginx \
        /var/log/letsencrypt \
        /var/lib/letsencrypt \
        /etc/letsencrypt \
        /var/www/certbot \
    && chown -R www-data:www \
        /var/log/nginx \
        /var/cache/nginx \
        /run/nginx \
        /etc/nginx \
        /var/log/letsencrypt \
        /var/lib/letsencrypt \
        /etc/letsencrypt \
        /var/www/certbot

USER www-data

CMD ["nginx", "-g", "daemon off;"]