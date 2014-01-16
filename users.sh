#!/bin/bash

# Needs to list all authenticated users of the system.
# These are people that can lend books.
#
# Each line should be structured as user@host.

# List all users from an htpasswd file.
HTPASSWD=/etc/schoollibrary/htpasswd /usr/share/schoollibrary/users-htpasswd.pl

# Uncomment to list all IServ users.
#sudo -u www-data php /usr/share/schoollibrary/users-iserv.php
