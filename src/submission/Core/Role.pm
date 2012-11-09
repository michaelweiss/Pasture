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

# remove roles add an entry with -role instead of role
# assumes that hasRole will read all entries in the role file
sub removeRole {
	my ($user, $conference, $role) = @_;
	my $match = 0;
	Lock::lock("data", "roles");
	open(LOG, ">>data/roles.dat") ||
		Audit::handleError("Could not add role");
	print LOG "$user\t$conference\t-$role\n";
	Lock::unlock("data", "roles");
	return $match;
}

# checks if user has a role
sub hasRole {
	my ($user, $conference, $role) = @_;
	my $match = 0;
	Lock::lock("data", "roles");
	open(LOG, "data/roles.dat") ||
		return @roles;
	# reads all entries in the role file 
	while (<LOG>) {
		# for each entry:
		# 1. notes when a matching add role entry is found
		# 2. revert match when a remove role entry is found
		# order matters: role, -role removes role
		# -role, role does not remove role
		if (/^$user\t$conference\t$role$/) {	
			$match = 1;
		}
		if (/^$user\t$conference\t-$role$/) {	
			$match = 0;
		}
	}
	close(LOG);
	Lock::unlock("data", "roles");
	return $match;
}

sub getRoles {
	my ($user, $conference) = @_;
	my %roles;
	Lock::lock("data", "roles");
	open(LOG, "data/roles.dat") ||
		return ();
	while (<LOG>) {
		chomp;
		if (/^$user\t$conference\t(\w+)/) {	
			$roles{$1} = 1;
		}
		if (/^$user\t$conference\t-(\w+)/) {	
			$roles{$1} = 0;
		}
	}
	close(LOG);
	Lock::unlock("data", "roles");
	my @roles;
	foreach (keys %roles) {
		push(@roles, $_) if ($roles{$_});
	}	
	return @roles;
}

sub getUsersInRole {
	my ($conference, $role) = @_;
	my %roles;
	Lock::lock("data", "roles");
	open(LOG, "data/roles.dat") ||
		return ();
	while (<LOG>) {
		chomp;
		if (/^(.+?)\t$conference\t$role$/) {	
			$roles{$1} = $role;
		}
		if (/^(.+?)\t$conference\t-$role$/) {	
			$roles{$1} = "-" . $role;
		}
	}
	close(LOG);
	Lock::unlock("data", "roles");
	my @users;
	foreach (keys %roles) {
		push(@users, $_) if ($roles{$_} eq $role);
	}
	return @users;
}

1;
