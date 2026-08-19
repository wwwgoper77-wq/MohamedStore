#!/bin/sh
wget -q "--no-check-certificate" "https://raw.githubusercontent.com/oe-alliance/oe-alliance-plugins/master/xml/satellites.xml" -O /etc/enigma2/satellites.xml
echo "Satellites.xml Updated Successfully!"
exit 0