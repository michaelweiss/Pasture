#!/usr/bin/perl

use Core::Terms;

our $timestamp;

sub setup {
	$timestamp = time();
	unlink("data/terms.dat");
}

sub testAddTerms {
	print "testAddTerms\n";
	Terms::addTerms("bob", "privacy");
	Terms::hasAgreedToTerms("bob", "privacy") || die "bob agreed to the terms";
}

sub testCheckNonExistantTerms {
	print "testCheckNonExistantTerms\n";
	Terms::addTerms("bob", "privacy");
	Terms::hasAgreedToTerms("bob", "privacy") || die "bob agreed to the terms";
	! Terms::hasAgreedToTerms("alice", "privacy") || die "alice did not agree to the terms";
}

setup();
testAddTerms();

setup();
testCheckNonExistantTerms();

setup();
