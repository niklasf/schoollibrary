#!/bin/bash

# Accept the user admin with password admin.
HTPASSWD=etc/schoollibrary/htpasswd HTGROUPS=etc/schoollibrary/htgroups usr/share/schoollibrary/auth-htpasswd.pl $1 $2
