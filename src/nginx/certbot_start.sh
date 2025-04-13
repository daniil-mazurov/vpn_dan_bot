#!/bin/sh
set -e

# Проверяем, существуют ли уже сертификаты
if [ ! -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem ]; then
    echo "Сертификаты не найдены. Получаем новые..."
    # certbot --nginx -d $DOMAIN -m $EMAIL --agree-tos --non-interactive --deploy-hook "nginx -s reload && true"
    certbot certonly --webroot -w /var/www/certbot -d "$DOMAIN" -m "$EMAIL" --agree-tos --no-eff-email --force-renewal -v
else
    echo "Сертификаты найдены. Пропускаем получение."
fi
