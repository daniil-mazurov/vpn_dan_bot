#!/bin/sh
set -e

# Проверяем, существуют ли уже сертификаты
if [ ! -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem ]; then
    echo "Сертификаты не найдены. Получаем новые..."
    certbot --nginx -d $DOMAIN -m $EMAIL --agree-tos --non-interactive --deploy-hook "nginx -s reload && true"
else
    echo "Сертификаты найдены. Пропускаем получение."
fi
