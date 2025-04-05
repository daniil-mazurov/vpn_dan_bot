FROM nginx:1.27.4-alpine3.21

RUN apk update && apk add --no-cache certbot certbot-nginx shadow

RUN addgroup -g 33 www && adduser -D -u 33 -G www www-data

COPY certbot_start.sh /usr/local/bin/certbot_start.sh

RUN chmod +x /usr/local/bin/certbot_start.sh

CMD ["nginx", "-g", "daemon off;"]