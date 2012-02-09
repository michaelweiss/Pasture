#!/usr/bin/perl

use Core::Submission;

sub setup {
	unlink("data/submissions.dat");
}

sub testRecordSubmission {
	print "testRecordSubmission\n";
	Submission::recordSubmission(1, "bob");
	my %submission = Submission::lookupSubmission(1);
	$submission{"user"} eq "bob" || die "user does not match: " . $submission{"user"};
}

sub testMultipleSubmissions {
	print "testRecordMultipleSubmissions\n";
	Submission::recordSubmission(1, "bob");
	Submission::recordSubmission(2, "alice");
	Submission::recordSubmission(3, "sue");
	my %submission = Submission::lookupSubmission(2);
	$submission{"user"} eq "alice" || die "user does not match: " . $submission{"user"};
}

sub testLookupSubmissionsByAuthor {
	print "testLookupSubmissions\n";
	Submission::recordSubmission(1, "bob");
	Submission::recordSubmission(2, "alice");
	Submission::recordSubmission(3, "bob");
	my @references = Submission::lookupSubmissionsByAuthor("bob");
	$references[0] == 1 && $references[1] == 3 || 
		die "references do not match: " . $references[0] . ", " . $references[1];
}

setup();
testRecordSubmission();

setup();
testMultipleSubmissions();

setup();
testLookupSubmissionsByAuthor();
