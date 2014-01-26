#!/bin/bash

# Called with the username as $1 and the given plain-text password as $2.
# Needs to list all groups of the user, one group per line.
#
# Available groups:
# - user
# - library_lend
# - library_modify
# - library_delete
# - library_admin
#
# If the authentication failed, do not even output user.
#
# The username is structured as user@host, where @host is optional and should
# default to the servers hostname.

# Use apache htpasswd and htgroups file for authentication.
HTPASSWD=/etc/schoollibrary/htpasswd \
HTGROUPS=/etc/schoollibrary/htgroups \
    /usr/share/schoollibrary/auth-htpasswd.pl $1 $2

# Uncomment to allow authenticating against IServ.
#sudo -u www-data php /usr/share/schoollibrary/auth-iserv.php $1 $2
