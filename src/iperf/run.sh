#!/bin/sh
# set -e # Выход при первой же ошибке

# Поднимаем WireGuard интерфейс
ip link add wg0 type wireguard
wg setconf wg0 /etc/wireguard/wg0.conf
ip address add 172.31.0.2/32 dev wg0
ip link set mtu 1420 up dev wg0
ip route add default dev wg0

# Проверяем, что WG интерфейс поднялся
ip addr show wg0

# Запускаем iperf3 и обрабатываем вывод
# iperf3 -O 1 -t 5 -J -c 172.31.0.1 | jq '.end.sum_sent.bits_per_second, .end.sum_received.bits_per_second'
# iperf3 -c 172.31.0.1