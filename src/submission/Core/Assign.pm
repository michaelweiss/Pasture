package Assign;

use CGI;
use Core::Audit;
use Core::Lock;

my %assignments;

sub getAssignments {
	if (undef %assignments) {
		loadAssignments(); 
	}
	return %assignments;
}

sub getAssignmentsForReviewer {
	my ($reviewer) = @_;
	unless (defined %assignments) {
		%assignments = loadAssignments();
	}
	return $assignments{$reviewer};
}

sub loadAssignments {
	my %_assignments;
	Lock::lock("data/screen", "assignments");
	open (ASSIGNMENTS, "data/screen/assignments.dat") ||
		return;
	while (<ASSIGNMENTS>) {
		chomp;
		my ($_reviewer, @submissions) = split(/, /);
		$_assignments{$reviewer} = @submissions;
	}
	Lock::unlock("data/screen", "assignments");
	%assignments = %_assignments;
	return %assignments;
}

sub saveAssignments {
	Lock::lock("data/screen", "assignments");
	open (ASSIGNMENTS, ">data/screen/assignments.dat") ||
		return;
	foreach $reviewer (keys %assignments) {
		print ASSIGNMENTS "$reviewer";
		foreach $paper (@{$assignments{$reviewer}}) {
			print ASSIGNMENTS ", $paper";
		}
		print ASSIGNMENTS "\n";	
	}
	Lock::unlock("data/screen", "assignments");
}

sub assignPaper {
	my ($reviewer, $paper) = @_;
	push(@{$assignments{$reviewer}}, $paper);
}

1;