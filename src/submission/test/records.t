#!/usr/bin/perl

use Core::Serialize::Records;

sub testListAllVersions {
	print "testListAllVersions\n";
	my @versions = Records::listAllVersions("3");
	foreach (@versions) {
		print $_, " ";
	}
	print "\n";
}

testListAllVersions();
