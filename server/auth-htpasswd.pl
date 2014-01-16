#!/usr/bin/perl -w

use strict;
use Env qw(HTPASSWD HTPASSWD_ALLOW_PLAIN HTGROUPS);

# Get command line arguments.
if ($#ARGV != 1) {
    exit;
}
my $username = $ARGV[0];
my $password = $ARGV[1];

# Check the password.
my $user_found = 0;
open my $htpasswd_fh, $HTPASSWD or exit;
while (<$htpasswd_fh>) {
    chop;
    my @record = split(/:/, $_, 2);

    if ($record[0] eq $username) {
        if (index($record[1], '$apr1$') == 0) {
            # Mechanism: Apache MD5 hash.
            require Crypt::PasswdMD5;

            my $salt = $record[1];
            $salt =~ s/^\$apr1\$//;
            $salt =~ s/^(.*)\$/$1/;
            $salt = substr($salt, 0, 8);

            if (Crypt::PasswdMD5::apache_md5_crypt($password, $salt) eq $record[1]) {
                print "user\n";
            } else {
                exit;
            }
        } elsif (index($record[1], '{SHA}') == 0) {
            # Mechanism: SHA-1.
            require Digest::SHA;
            require MIME::Base64;

            if ('{SHA}' . MIME::Base64::encode_base64(Digest::SHA::sha1($password), '') eq $record[1]) {
                print "user\n";
            } else {
                exit;
            }
        } else {
            # Mechanism: crypt.
            if (crypt($password, $record[1]) eq $record[1]) {
                print "user\n";
            } else {
                # Mechanism: plain text.
                if ($HTPASSWD_ALLOW_PLAIN && $password eq $record[1]) {
                    print "user\n";
                } else {
                    exit;
                }
            }
        }
        $user_found = 1;
        last;
    }
}
exit unless $user_found;

# Get groups.
open my $htgroups_fh, $HTGROUPS or exit;
while (<$htgroups_fh>) {
    chop;
    my @record = split(/:\s+/, $_, 2);
    my @users = split(/\s+/, $record[1]);

    foreach my $user (@users) {
        if ($user eq $username && $record[0] ne 'user') {
            print "$record[0]\n";
        }
    }
}
