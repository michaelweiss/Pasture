package Terms;

use strict;
use warnings;

use lib '.';
use Core::Audit;
use Core::Assert;
use Core::Lock;

# we also log the timestamp, so we can ask the user again should the terms be
# updated at some future point. This information is not used right now.
sub addTerms {
	my ($user, $terms) = @_;
	Lock::lock("data", "terms");
	open(LOG, ">>data/terms.dat") ||
		Audit::handleError("Could not add terms");
	print LOG "$::timestamp\t$user\t$terms\n";
	close(LOG);
	Lock::unlock("data", "terms");
}

sub hasAgreedToTerms {
	my ($user, $terms) = @_;
	my $match = 0;
	Lock::lock("data", "terms");
	open(LOG, "data/terms.dat") ||
		return 0;
	# reads all entries in the terms file 
	while (<LOG>) {
		# for each entry:
		# 1. notes when a matching add terms entry is found
		# 2. revert match when a remove terms entry is found
		# order matters: terms, -terms removes terms
		# -terms, terms does not remove terms
		if (/^(\d+)\t$user\t$terms$/) {	
			$match = 1;
		}
		if (/^(\d+)\t$user\t-$terms$/) {
			$match = 0;
		}
	}
	close(LOG);
	Lock::unlock("data", "terms");
	return $match;
}

1;
