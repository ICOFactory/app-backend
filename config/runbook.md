# Ubuntu 18 LTS
Set up ssh keying
https://debian-administration.org/article/530/SSH_with_authentication_key_instead_of_password

Add the master mysql server instance
as mysql-master in /etc/hosts
### Install MySQL 5.7

`# apt-get install mysql-server`

### For Master database, use the following settings in my.conf:

datadir=/var/lib/mysql

bind-address=<private_ip>

symbolic-links=0

log-bin=mysql-bin

server-id=1

innodb_flush_log_at_trx_commit=1

sync_binlog=1

### For a slave database, use unique server id greater than 1

server_id=2, or 3, etc.


## nginx for microservices

`# apt-get install nginx`

configure nginx to connect to uwsgi through sockets instead of TCP/IP
see config/nginx.config for an example

## python3 stack

Incomplete dependencies:

`# apt-get install python3-venv gcc python3-dev libmysqlclient-dev`

## Service user
`# createuser service`

`# su service`


`~ $ git clone https://github.com/ICOFactory/app-backend.git`

Change config settings to reflect master and slave database settings in
config.json as well as config/charting.json

`cd app-backend`

`~/app-backend/ $ python3 -m venv venv`

`~/app-backend/ $ . venv/bin/activate`

`(venv) ~/app-backend/ $ pip install -r config/requirements.txt`

`(venv) ~/app-backend/ $ uwsgi --ini config/uwsgi.ini`

