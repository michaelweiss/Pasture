#!/usr/bin/perl

use Core::Password;

sub testCrypt {
	print "testCrypt\n";
	my $hash = crypt("test", "salt");
	$hash eq "salSp1wOPp6fk" || die "hash does not match: $hash";
}

sub testSalt {
	print "testSalt\n";
	our $config;
	$config->{"salt"} = "pepper";
	my $hash = Password::_salt("test");
	$hash eq "pe3unRVcD64ek" || die "hash does not match: $hash ";
}

sub setup {
	unlink("data/password.dat");
}

sub testLogPassword {
	print "testLogPassword\n";
	Password::logUserPassword("bob", "secret");
	Password::checkUserPassword("bob", "secret") || die "user and password should match";
	! Password::checkUserPassword("bob", "wrong_secret") || die "user and wrong password should not match";
}

sub testExistsUser {
	print "testExistsUser\n";
	Password::logUserPassword("bob", "secret");
	Password::logUserPassword("alice", "another_secret");
	Password::existsUser("alice") || die "no password for user alice";
	! Password::existsUser("sue") || die "user sue should not exist";
}

testCrypt();
testSalt();

setup();
testLogPassword();

setup();
testExistsUser();
