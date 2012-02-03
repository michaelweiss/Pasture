#!/usr/bin/perl

use Core::Review;
use Core::Role;

sub setup {
	unlink("data/roles.dat");
}

sub testAddPcMember {
	print "testAddPcMember\n";
	Role::addRole("bob", "europlop2012", "author");
	Role::addRole("bob", "europlop2012", "pc");
	
	my @roles = Role::getRoles("bob", "europlop2012");
	$roles[0] eq "author" || die "roles does not match: " . $roles[0];
	$roles[1] eq "pc" || die "roles does not match: " . $roles[1];
	
	Role::hasRole("bob", "europlop2012", "author") || 
		die "user should have role author";
	Role::hasRole("bob", "europlop2012", "pc") || 
		die "user should have role pc";
}

sub testGetAllPcMembers {
	print "testGetAllPcMembers\n";
	Role::addRole("alice", "europlop2012", "pc");
	Role::addRole("bob", "europlop2012", "pc");
	Role::addRole("carl", "europlop2012", "pc");
	
	my @users = Role::getUsersInRole("europlop2012", "pc");
	$users[0] eq "alice" || die "users.0 does not match: " . $users[0];
	$users[1] eq "bob" || die "users.1 does not match: " . $users[1];
	$users[2] eq "carl" || die "users.2 does not match: " . $users[2];
}

setup();
testAddPcMember();

setup();
testGetAllPcMembers();
