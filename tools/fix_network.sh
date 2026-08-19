#!/bin/sh
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 1.1.1.1" >> /etc/resolv.conf
/etc/init.d/networking restart
echo "Network & DNS Fixed Successfully!"
exit 0