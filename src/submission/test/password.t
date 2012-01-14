#!/usr/bin/perl

use Core::Password;
use Core::Serialize;

sub testCrypt {
	print "testCrypt\n";
	my $hash = crypt("test", "salt");
	$hash eq "salSp1wOPp6fk" || die "hash does not match";
}

sub testSalt {
	print "testSalt\n";
	our $config = Serialize::getConfig();
	my $hash = Password::_salt("test");
	$hash eq "pe3unRVcD64ek" || die "hash does not match";
}

testCrypt();
testSalt();
