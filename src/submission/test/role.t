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

sub testRemoveRole {
	print "testRemoveRole\n";
	Role::addRole("bob", "europlop2012", "admin");
	Role::addRole("bob", "europlop2012", "pc");
	Role::hasRole("bob", "europlop2012", "pc") || die "user should have role";
	Role::removeRole("bob", "europlop2012", "pc");
	!Role::hasRole("bob", "europlop2012", "pc") || die "user should no longer have role";
}

sub testGetUsersInRole {
	print "testGetUsersInRole\n";
	Role::addRole("bob", "europlop2012", "pc");
	Role::addRole("alice", "europlop2012", "pc");
	my @users = Role::getUsersInRole("europlop2012", "pc");
	$#users == 1 || die "alice and bob should be in (@users)";
	Role::removeRole("bob", "europlop2012", "pc");
	@users = Role::getUsersInRole("europlop2012", "pc");
	$#users == 0 || die "now only alice should be in (@users)";
}

setup();
testAddRole();

setup();
testRemoveRole();

setup();
testGetUsersInRole();