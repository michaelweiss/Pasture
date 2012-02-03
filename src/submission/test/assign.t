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

sub testAssignOnePaper {
	print "testAssignOnePaper\n";
	Role::addRole("bob", "europlop2012", "pc");
	Submission::recordSubmission(1, "bob");
	Assign::assignPaper("bob", 1);
	Assign::
}

setup();
