package Role;

use lib '.';
use Core::Audit;
use Core::Lock;

sub addRole {
	my ($user, $conference, $role) = @_;
	Lock::lock("data", "roles");
	open(LOG, ">>data/roles.dat") ||
		Audit::handleError("Could not add role");
	print LOG "$user\t$conference\t$role\n";
	close(LOG);
	Lock::unlock("data", "roles");
}

sub hasRole {
	my ($user, $conference, $role) = @_;
	my $match = 0;
	Lock::lock("data", "roles");
	open(LOG, "data/roles.dat") ||
		return @roles;
	while (<LOG>) {
		if (/^$user\t$conference\t$role$/) {	
			$match = 1;
			last;
		}
	}
	close(LOG);
	Lock::unlock("data", "roles");
	return $match;
	
}

sub getRoles {
	my ($user, $conference) = @_;
	my @roles;
	Lock::lock("data", "roles");
	open(LOG, "data/roles.dat") ||
		return @roles;
	while (<LOG>) {
		if (/^$user\t$conference\t/) {	
			chomp;
			my @record = split(/\t/);
			push(@roles, $record[-1]);
		}
	}
	close(LOG);
	Lock::unlock("data", "roles");
	return @roles;
}

1;
