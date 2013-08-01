package Assign;

use CGI;
use Core::Audit;
use Core::Lock;

my %assignments;

# Create directory for screening assignments and votes, if one does not exist
unless (-e "data/screen") {
	mkdir("data/screen", 0755) || 
		Audit::handleError("Cannot create screen directory");
}

sub getAssignments {
	unless (%assignments) {
		loadAssignments(); 
	}
	return %assignments;
}

sub getAssignmentsForReviewer {
	my ($reviewer) = @_;
	unless (%assignments) {
		loadAssignments();
	}
	return @{$assignments{$reviewer}};
}

sub loadAssignments {
	my %_assignments;
	Lock::lock("data/screen", "assignments");
	open (ASSIGNMENTS, "data/screen/assignments.dat") ||
		return;
	while (<ASSIGNMENTS>) {
		chomp;
		# FIXED: $reviewer instead of $_reviewer 
		my ($reviewer, @submissions) = split(/, /);
		# FIXED: \@submissions instead of @submissions
		$_assignments{$reviewer} = \@submissions;
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
	foreach $p (@{$assignments{$reviewer}}) {
		return if ($p == $paper);
	}
	push(@{$assignments{$reviewer}}, $paper);
}

1;