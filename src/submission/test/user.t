#!/usr/bin/perl

use Core::User;

sub setup {
	unlink("data/users.dat");
}

sub testCreateUser {
	print "testCreateUser\n";
	User::saveUser("bob", "Bob", "Smith", "Acme Inc", "Canada");
	my %user = User::loadUser("bob");
	$user{"affiliation"} eq "Acme Inc" || die "affiliation does not match: " . $user{"affiliation"};
}

sub testUpdateUser {
	print "testUpdateUser\n";
	User::saveUser("bob", "Bob", "Smith", "Bob's", "Canada");
	my %user = User::loadUser("bob");
	$user{"firstName"} eq "Bob" || die "first name does not match: " . $user{"firstName"};
	$user{"lastName"} eq "Smith" || die "last name does not match: " . $user{"lastName"};
	$user{"affiliation"} eq "Bob's" || die "affiliation does not match: " . $user{"affiliation"};
	$user{"country"} eq "Canada" || die "country does not match: " . $user{"country"};
}

setup();
testCreateUser();
testUpdateUser();
