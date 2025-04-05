#!/bin/bash
set -e # Выход при первой же ошибке

# Поднимаем WireGuard интерфейс
wg-quick up wg0

# Проверяем, что WG интерфейс поднялся
ip addr show wg0

# Запускаем iperf3 и обрабатываем вывод
iperf3 -O 1 -t 5 -J -c 172.31.0.1 | jq '.end.sum_sent.bits_per_second, .end.sum_received.bits_per_second'