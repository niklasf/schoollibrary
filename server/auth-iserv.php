#!/usr/bin/php
<?php

if (empty($argv[1]) || empty($argv[2])) {
    exit;
}

ini_set("include_path", ".:/usr/share/iserv/www/inc:/usr/share/php");

require("sec/login.inc");

try {
    if ($err = login($argv[1], $argv[2])) {
        exit;
    }

    print "user\n";

    foreach (array("library_modify", "library_delete", "library_admin", "library_lend") as $group) {
        if (secure_privilege($group)) {
            print "$group\n";
        }
    }
} catch (Exception $e) { }
