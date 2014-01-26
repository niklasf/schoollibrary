#!/usr/bin/php
<?php

// Internal request.
$_SERVER['REMOTE_ADDR'] = '127.0.0.1';

// Get arguments.
if (empty($argv[1]) || empty($argv[2])) {
    exit;
}
$username = $argv[1];
$password = $argv[2];

// Remove hostname suffix from username.
$hostname = trim(exec("hostname -d"));
if (!$hostname) {
    $hostname = trim(exec("hostname"));
}
$pattern = preg_quote('@' . $hostname);
$username = preg_replace('/' . preg_quote('@' . $hostname) . '$/', '', $username);

// Include IServ library.
ini_set("include_path", ".:/usr/share/iserv/www/inc:/usr/share/php");
require("sec/login.inc");

// Try to authenticate.
try {
    if ($err = login($username, $password)) {
        exit;
    }

    print "user\n";

    foreach (array("library_modify", "library_delete", "library_admin", "library_lend") as $group) {
        if (secure_privilege($group)) {
            print "$group\n";
        }
    }
} catch (Exception $e) { }
