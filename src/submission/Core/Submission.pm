package Submission;

use lib '.';
use Core::Audit;
use Core::Lock;

sub recordSubmission {
	my ($reference, $user) = @_;
	Lock::lock("data", "submissions");
	open(LOG, ">>data/submissions.dat") ||
		Audit::handleError("Could not record submission");
	print LOG "$reference\t$user\n";
	close(LOG);
	Lock::unlock("data", "submissions");
}

sub lookupSubmission {
	my ($reference) = @_;
	Lock::lock("data", "submissions");
	open(LOG, "data/submissions.dat") ||
		Audit::handleError("Could not lookup submission");
	while (<LOG>) {
		if (/^$reference\t/) {	
			chomp;
			@submission = split(/\t/);
		}
	}
	my %submission, $i=0;
	foreach $key ("reference", "user") {
		$submission{$key} =  $submission[$i++];
	}
	close(LOG);
	Lock::unlock("data", "submissions");
	return %submission;
}

sub lookupSubmissionsByAuthor {
	my ($user) = @_;
	my @references;
	Lock::lock("data", "submissions");
	open(LOG, "data/submissions.dat") ||
		return @references;
	while (<LOG>) {
		if (/^(\d+)\t$user$/) {
			push(@references, $1); 
		}
	}
	close(LOG);
	Lock::unlock("data", "submissions");
	return @references;
}

1;
