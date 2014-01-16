#!/usr/bin/perl -w

use strict;
use Env qw(HTPASSWD);

open my $htpasswd_fh, $HTPASSWD or exit;

while (<$htpasswd_fh>) {
    chop;

    if (!($_ =~ /^(\s*|\s*#.*)$/)) {
        my @record = split(/:/, $_, 2);
        print "$record[0]\n";
    }
}
