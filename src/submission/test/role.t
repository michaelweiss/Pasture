#!/usr/bin/perl

use Core::Role;

sub setup {
	unlink("data/roles.dat");
}

sub testAddRole {
	print "testAddRole\n";
	Role::addRole("bob", "europlop2012", "admin");
	my @roles = Role::getRoles("bob", "europlop2012");
	$roles[0] eq "admin" || die "roles does not match: " . $roles[0];
	Role::hasRole("bob", "europlop2012", "admin") || die "user should have role";
}

setup();
testAddRole();
