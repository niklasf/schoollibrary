#!/usr/bin/php
<?php

$hostname = trim(system('hostname -d'));
if (!$hostname) {
    $hostname = trim(system('hostname'));
}

ini_set("include_path", ".:/usr/share/iserv/www/inc:/usr/share/php");

require("db.inc");

db_user("login");

$query = db_query("SELECT act FROM users");

while ($row = pg_fetch_assoc($query)) {
    print $row["act"];
    print "@";
    print $hostname;
    print "\n";
}
