# Фингерпринт к WG серверу
chmod 600 .ssh/id_rsa_wg

# Установка postgresql
sudo apt-get update
sudo apt-get install postgresql-client
sudo apt -y install postgresql
sudo service postgresql start

sudo nano /etc/postgresql/12/main/postgresql.conf # listen_addresses = '*'
sudo nano /etc/postgresql/12/main/pg_hba.conf # host    all             all             0.0.0.0/0               md5
sudo service postgresql restart

sudo -u postgres psql
CREATE USER bot WITH PASSWORD 'OmegaUltraSTO500!';
CREATE DATABASE devbotbase;
GRANT ALL PRIVILEGES ON DATABASE devbotbase to bot;

# Настройка redis
sudo nano /etc/redis/redis.conf
# bind 0.0.0.0
# requirepass ChornayaTarelochka15

# Создание пользователя
sudo adduser bot
sudo usermod -aG sudo bot
groups bot
ssh-keygen -t rsa -b 4096

sudo nano /etc/ssh/sshd_config
# Match User bot
#       PasswordAuthentication no
#       PubkeyAuthentication yes
sudo systemctl restart ssh
scp root@185.229.66.187:/home/bot/.ssh/id_rsa ./id_rsa

chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
cat /path/to/your/id_rsa.pub >>~/.ssh/authorized_keys

# Установка pgadmin4
curl https://www.pgadmin.org/static/packages_pgadmin_org.pub | sudo apt-key add
sudo sh -c 'echo "deb https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" > /etc/apt/sources.list.d/pgadmin4.list && apt update'
sudo apt install pgadmin4
sudo /usr/pgadmin4/bin/setup-web.sh
sudo ufw allow 'Apache'
sudo ufw enable
sudo ufw status

#DOCKER
docker build -t danvpn vpn_dan_bot/
docker run -dit \
    --restart always \
    --name danvpn \
    --network="host" \
    -e TZ='Europe/Moscow' \
    -v /home/bot/vpn_dan_bot_docker/logs/:/vpn_dan_bot/logs \
    -v /home/bot/vpn_dan_bot_docker/bugs/:/vpn_dan_bot/bugs \
    -v /home/bot/vpn_dan_bot_docker/dumps/:/vpn_dan_bot/src/db/dumps \
    -v /home/bot/vpn_dan_bot_docker/backups/:/vpn_dan_bot/src/db/backups \
    -v /home/bot/vpn_dan_bot_docker/timepoint/:/vpn_dan_bot/src/scheduler/timepoint \
    danvpn ./_main.py

docker run -it \
    --name danvpn-db-create \
    --network="host" \
    -e TZ='Europe/Moscow' \
    -v /home/bot/vpn_dan_bot_docker/logs/:/vpn_dan_bot/logs \
    -v /home/bot/vpn_dan_bot_docker/bugs/:/vpn_dan_bot/bugs \
    -v /home/bot/vpn_dan_bot_docker/dumps/:/vpn_dan_bot/src/db/dumps \
    -v /home/bot/vpn_dan_bot_docker/backups/:/vpn_dan_bot/src/db/backups \
    -v /home/bot/vpn_dan_bot_docker/timepoint/:/vpn_dan_bot/src/scheduler/timepoint \
    danvpn poetry run python ./src/scripts/db_recreate.py

docker run -d \
    --restart always \
    --name danvpn-redis \
    -p 6379:6379 \
    -v /home/bot/vpn_dan_bot_docker/redis/dаta:/data \
    -e REDIS_PASSWORD=ChornayaTarelochka15 \
    redis redis-server \
    --appendonly yes \
    --requirepass "ChornayaTarelochka15"

docker run -d \
    --name danvpn-postgres \
    -p 5432:5432 \
    -e POSTGRES_USER=bot \
    -e POSTGRES_PASSWORD=OmegaUltraSTO500! \
    -e POSTGRES_DB=devbotbase \
    -e PGDATA=/var/lib/postgresql/data/pgdata \
    -v /home/bot/vpn_dan_bot_docker/postgresql/data:/var/lib/postgresql/data \
    postgres:15
# -v /var/lib/postgresql/init:/docker-entrypoint-initdb.d
