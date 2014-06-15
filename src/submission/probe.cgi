#!/usr/bin/perl

use CGI;
use CGI::Carp qw(fatalsToBrowser);

sub ok() {
    $q = new CGI();
    print $q->header("text/html");
    print "OK";
}

ok();