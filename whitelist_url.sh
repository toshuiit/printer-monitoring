#!/bin/bash

 

case "$1" in

  start)

    echo "[+] Applying whitelist rules..."

 

    # Create or flush whitelist

    sudo ipset destroy whitelist 2>/dev/null

    sudo ipset create whitelist hash:ip

 

    # Add allowed domains

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

 

    # Clear OUTPUT chain before applying new rules

    sudo iptables -F OUTPUT

 

    # Always allow loopback traffic

    sudo iptables -A OUTPUT -o lo -j ACCEPT

 

    # Always allow DNS (UDP & TCP port 53)

    sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT

    sudo iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

 

    # Allow traffic to whitelisted IPs

    sudo iptables -A OUTPUT -m set --match-set whitelist dst -j ACCEPT

 

    # Drop everything else

    sudo iptables -A OUTPUT -j DROP

    ;;

 

  stop)

    echo "[+] Removing whitelist rules, restoring full access..."

    sudo iptables -F OUTPUT

    sudo ipset destroy whitelist 2>/dev/null

    ;;

 

  *)

    echo "Usage: $0 {start|stop}"

    exit 1

    ;;

esac