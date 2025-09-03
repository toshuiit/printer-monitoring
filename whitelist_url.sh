#!/bin/bash

case "$1" in
  start)
    echo "[+] Applying whitelist rules..."

    # --- OUTPUT WHITELIST SETUP ---
    sudo ipset destroy whitelist 2>/dev/null
    sudo ipset create whitelist hash:ip

    # Add allowed domains to whitelist
    for domain in \
      dummy.iitk.ac.in \
      dummy.cse.iitk.ac.in \
      fonts.googleapis.com \
      www.googletagmanager.com \
      cdnjs.cloudflare.com
    do
      for ip in $(dig +short $domain | grep '^[0-9]'); do
        echo "Adding $domain -> $ip"
        sudo ipset add whitelist $ip
      done
    done

    # --- OUTPUT RULES ---
    sudo iptables -F OUTPUT

    # Always allow loopback traffic
    sudo iptables -A OUTPUT -o lo -j ACCEPT

    # Always allow DNS (UDP & TCP port 53)
    sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
    sudo iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

    # Allow traffic to whitelisted IPs
    sudo iptables -A OUTPUT -m set --match-set whitelist dst -j ACCEPT

    # Drop all other outbound traffic
    sudo iptables -A OUTPUT -j DROP


    # --- INPUT RULES (SSH RESTRICTION) ---
    sudo iptables -F INPUT

    # Allow loopback
    sudo iptables -A INPUT -i lo -j ACCEPT

    # Allow established/related connections
    sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    # Allow SSH only from specific IPs
    sudo iptables -A INPUT -p tcp -s 172.27.15.17 --dport 22 -j ACCEPT
    sudo iptables -A INPUT -p tcp -s 172.27.15.95 --dport 22 -j ACCEPT

    # Drop everything else
    sudo iptables -A INPUT -j DROP
    ;;

  stop)
    echo "[+] Removing whitelist rules, restoring full access..."

    sudo iptables -F OUTPUT
    sudo iptables -F INPUT
    sudo ipset destroy whitelist 2>/dev/null
    ;;

  *)
    echo "Usage: $0 {start|stop}"
    exit 1
    ;;
esac
