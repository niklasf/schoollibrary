#!/bin/bash

# Accept the user admin with password admin.
HTPASSWD=htpasswd HTGROUPS=htgroups ./auth-htpasswd.pl $1 $2
