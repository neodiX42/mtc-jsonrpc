#!/bin/bash

if [ "$(id -u)" != "0" ]; then
	echo "Please run script as root"
	exit 1
fi
# Install nginx proxy_pass

# Checking package

if [ $(dpkg-query -W -f='${Status}' nginx 2>/dev/null | grep -c "ok installed") -eq 0 ];
then
  apt-get install nginx;
fi

ip=$1
port=$2
localport=$(($port-1))
workdir=$3
if [[ "$OSTYPE" =~ darwin.* ]]; then
  root="/usr/local/src/mtc-jsonrpc"
else
  root="/usr/src/mtc-jsonrpc"
fi
block="/etc/nginx/sites-available/mtc-jsonrpc"

[ -f block ] && rm block

# Create the Nginx server block file:
tee $block > /dev/null <<EOF
server {
        listen $port ssl;
        listen [::]:$port ssl;

        ssl_certificate $workdir/ssl.crt;
        ssl_certificate_key $workdir/ssl.key;

        allow 127.0.0.1;
        allow $ip;
        deny all;
        server_name 0.0.0.0;

        location / {
            proxy_set_header        Host \$http_host;
            proxy_set_header        X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_pass              http://127.0.0.1:$localport;
            proxy_set_header        X-NginX-Proxy true;
            proxy_set_header        X-Real-IP \$remote_addr;
            proxy_connect_timeout   5;
            proxy_read_timeout      240;
            proxy_intercept_errors  on;
            proxy_set_header        X-Scheme \$scheme;
            proxy_redirect          default;
        }
}
EOF

# Link to make it available
[ ! -L "/etc/nginx/sites-enabled/mtc-jsonrpc" ] && ln -s $block /etc/nginx/sites-enabled/

# Test configuration and reload if successful
nginx -t && service nginx restart
