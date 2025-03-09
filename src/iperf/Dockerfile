FROM debian:12-slim

WORKDIR /wg

RUN apt-get update \
    && apt-get install -y sudo locales apt-utils debconf-utils dialog \
    && rm -rf /var/lib/apt/lists/* \
    && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
RUN echo "resolvconf resolvconf/linkify-resolvconf boolean false" | debconf-set-selections
RUN apt-get update
RUN apt-get install -y resolvconf


ENV LANG en_US.utf8

RUN apt update \
    && apt install wireguard procps iperf3 wireguard-tools iproute2 jq -y \
    && echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

COPY wg0.conf /etc/wireguard/wg0.conf

RUN sudo chown root:root /etc/wireguard/wg0.conf \
    && sudo chmod 644 /etc/wireguard/wg0.conf

CMD ["/bin/bash"]