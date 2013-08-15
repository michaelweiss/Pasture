package User;

use strict;
use warnings;

use lib '.';
use Core::Audit;
use Core::Lock;

sub saveUser {
	my ($user, $firstName, $lastName, $affiliation, $country) = @_;
	Lock::lock("data", "users");
	open(LOG, ">>data/users.dat") ||
		Audit::handleError("Could not save user profile");
	print LOG "$user\t$firstName\t$lastName\t$affiliation\t$country\n";
	close(LOG);
	Lock::unlock("data", "users");
}

sub loadUser {
	my ($user) = @_;
	my (@profile, %profile);
	Lock::lock("data", "users");
	open(LOG, "data/users.dat") ||
		Audit::handleError("Could not load user profile");
	while (<LOG>) {
		if (/^$user\t/) {	
			chomp;
			@profile = split(/\t/);
		}
	}
	my $i=0;
	foreach my $key ("user", "firstName", "lastName", "affiliation", "country") {
		$profile{$key} =  $profile[$i++];
	}
	close(LOG);
	Lock::unlock("data", "users");
	return %profile;
}

1;
