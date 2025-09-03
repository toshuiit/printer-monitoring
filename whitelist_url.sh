#!/bin/bash

set -e  # Exit on any error

WHITELIST_DOMAINS=(
  X.cse.iitk.ac.in
  Y.cse.iitk.ac.in
  Z.cse.iitk.ac.in
)

WHITELIST_SSH_IPS=(
  172.27.x.x
  172.27.x.x
  172.20.x.x
  172.27.x.x
)

case "$1" in
  start)
    echo "[+] Applying whitelist rules..."

    # Reset policies to ACCEPT to avoid lockout during setup
    sudo iptables -P INPUT ACCEPT
    sudo iptables -P OUTPUT ACCEPT

    # Flush existing rules
    sudo iptables -F INPUT
    sudo iptables -F OUTPUT

    # Destroy and recreate IP set
    sudo ipset destroy whitelist 2>/dev/null || true
    sudo ipset create whitelist hash:ip

    echo "[+] Resolving domain IPs and populating IPSet..."
    for domain in "${WHITELIST_DOMAINS[@]}"; do
      for ip in $(dig +short "$domain" | grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}'); do
        echo "Adding $domain -> $ip"
        sudo ipset add whitelist "$ip"
      done
    done

    # Setup OUTPUT rules
    echo "[+] Configuring OUTPUT rules..."
    sudo iptables -A OUTPUT -o lo -j ACCEPT
    sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
    sudo iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
    sudo iptables -A OUTPUT -m set --match-set whitelist dst -j ACCEPT
    sudo iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
    sudo iptables -A OUTPUT -j DROP

    # Setup INPUT rules
    echo "[+] Configuring INPUT rules..."
    sudo iptables -A INPUT -i lo -j ACCEPT
    sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    for ip in "${WHITELIST_SSH_IPS[@]}"; do
      sudo iptables -A INPUT -p tcp -s "$ip" --dport 22 -m state --state NEW -j ACCEPT
    done

    sudo iptables -A INPUT -j DROP

    # Set default policies to DROP for safety
    sudo iptables -P INPUT DROP
    sudo iptables -P OUTPUT DROP
    ;;

  stop)
    echo "[+] Removing whitelist rules and restoring default access..."

    # Set default policy to ACCEPT
    sudo iptables -P INPUT ACCEPT
    sudo iptables -P OUTPUT ACCEPT

    # Flush rules
    sudo iptables -F INPUT
    sudo iptables -F OUTPUT

    # Destroy whitelist IP set
    sudo ipset destroy whitelist 2>/dev/null || true
    ;;

  *)
    echo "Usage: $0 {start|stop}"
    exit 1
    ;;
esac

