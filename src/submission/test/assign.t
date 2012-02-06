#!/usr/bin/perl

use Core::Assign;
use Core::Review;
use Core::Role;
use Core::Submission;

sub setup {
	unlink("data/roles.dat");
	unlink("data/submissions.dat");
	unlink("data/screen/assignments.dat");
}

sub testAssignPapers {
	print "testAssignPapers\n";
	Role::addRole("bob", "europlop2012", "pc");
	Role::addRole("joe", "europlop2012", "pc");
	Submission::recordSubmission(1, "mark");
	Submission::recordSubmission(2, "nancy");
	Submission::recordSubmission(3, "peter");
	Assign::loadAssignments();
	Assign::assignPaper("bob", 1);
	Assign::assignPaper("joe", 2);
	Assign::assignPaper("bob", 3);
	Assign::saveAssignments();
	my @bobs = Assign::getAssignmentsForReviewer("bob");
	$bobs[0] eq "1" || die "expected 1, but got: $bobs[0]";
	$bobs[1] eq "3" || die "expected 3, but got: $bobs[1]";
}

# requires testAssignPapers to have run before
sub testLoadAssignments {
	print "testLoadAssignments\n";
	Assign::loadAssignments();
	my @bobs = Assign::getAssignmentsForReviewer("bob");
	$bobs[0] eq "1" || die "expected 1, but got: $bobs[0]";
	$bobs[1] eq "3" || die "expected 3, but got: $bobs[1]";
}

# requires testAssignPapers to have run before
sub testGetAssignmentsForReviewer {
	print "testGetAssignmentsForReviewer\n";
	my @joes = Assign::getAssignmentsForReviewer("joe");
	$joes[0] eq "2" || die "expected 2, but got: $joes[0]";
}

setup();
testAssignPapers();

testLoadAssignments();
testGetAssignmentsForReviewer();