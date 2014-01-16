#!/usr/bin/perl -w

use strict;
use Env qw(HTPASSWD);

open my $htpasswd_fh, $HTPASSWD or exit;

my $hostname = `hostname -d` || `hostname`;
chop($hostname);

while (<$htpasswd_fh>) {
    chop;

    if (!($_ =~ /^(\s*|\s*#.*)$/)) {
        my @record = split(/:/, $_, 2);

        my $username = $record[0];
        if (index($username, '@') == -1) {
            $username .= '@' . $hostname;
        }

        print "$username\n";
    }
}
