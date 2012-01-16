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

testCrypt();
testSalt();
