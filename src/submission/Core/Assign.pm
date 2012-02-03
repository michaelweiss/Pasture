package Assign;

use CGI;
use Core::Audit;

sub getAssignments {
	my ($user) = @_;
	open (ASSIGNMENTS, "data/screen/assignments.dat") ||
		return ();
	while (<ASSIGNMENTS>) {
		chomp;
		my ($fooUser, @submissions) = split(/, /);
		if ($user eq $fooUser) {
			close (ASSIGNMENTS);
			return @submissions;
		}
	}
	close (ASSIGNMENTS);
	return ();
}

1;