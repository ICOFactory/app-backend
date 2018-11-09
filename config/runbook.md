# Ubuntu 18 LTS
`# apt-get install mysql-server`

For Master database, use the following settings in my.conf:

datadir=/var/lib/mysql
bind-address=<private_ip>
symbolic-links=0
log-bin=mysql-bin
server-id=1
innodb_flush_log_at_trx_commit=1
sync_binlog=1

