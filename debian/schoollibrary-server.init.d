#!/bin/sh
### BEGIN INIT INFO
# Provides:          schoollibrary-server
# Required-Start:    $local_fs $network $remote_fs $syslog
# Required-Stop:     $local_fs $network $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: schoollibrary api and database
# Description:       Allows school libraries to keep track of their books in a
#                    database. Also keeps track of who lent a book and when it
#                    is due for return.
### END INIT INFO

[ -x "/usr/bin/nodejs" ] || exit 0
[ -e "/usr/share/schoollibrary/server.js" ] || exit 0
[ -r "/etc/default/schoollibrary-server" ] && . /etc/default/schoollibrary-server

. /lib/init/vars.sh
. /lib/lsb/init-functions

case "$1" in
  start)
    start-stop-daemon --start --quiet --make-pidfile --pidfile /var/run/schoollibrary.pid --background --startas /bin/bash -- -c "exec /usr/bin/nodejs /usr/share/schoollibrary/server.js >> /var/log/schoollibrary.log 2>&1"
    log_daemon_msg "Started schoollibrary-server"
    ;;

  stop)
    start-stop-daemon --stop --retry forever/QUIT/1 --quiet --oknodo --pidfile /var/run/schoollibrary.pid
    rm -f /var/run/schoollibrary.pid
    log_daemon_msg "Stopped schoollibrary-server"
    ;;

  restart|force-reload)
    ${0} stop
    ${0} start
    ;;

  status)
    if start-stop-daemon --stop --quiet --signal 0 --name bash --pidfile /var/run/schoollibrary.pid
    then
        echo "schoollibrary-server service running"
    else
        echo "schoollibrary-server service not running"
        exit 1
    fi
    ;;

  *)
    echo "Usage: /etc/init.d/schoollibrary-server {start|stop|restart|force-reload}" >&2
    exit 1
    ;;
esac

exit 0
