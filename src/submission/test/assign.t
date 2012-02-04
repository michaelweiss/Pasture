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
}

setup();
testAssignPapers();