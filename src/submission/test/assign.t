#!/usr/bin/perl

use Core::Assign;
use Core::Review;
use Core::Role;

sub setup {
	unlink("data/roles.dat");
}

setup();
