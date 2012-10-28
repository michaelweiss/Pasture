package Screen;

use lib '.';
use Core::Format;
use Core::Lock;
use Core::Assign;

# Create directory for screening assignments and votes, if one does not exist
unless (-e "data/screen") {
	mkdir("data/screen", 0755) || 
		Audit::handleError("Cannot create screen directory");
}

sub saveVote {
	my ($timestamp, $user, $reference, $vote, $reason) = @_;
	$reason =~ s/\n/ /g;
	Lock::lock("data/screen", "votes");
	open(LOG, ">>data/screen/votes.dat") ||
		::handleError("Could not save vote");
	print LOG "$timestamp:$user:$reference:$vote:$reason\n";
	close(LOG);
	Lock::unlock("data/screen", "votes");
}

# TODO: refactor to getAllReviews
sub votes {
	my $votes;
	unless (-e "data/screen/votes.dat") {
		return $votes;	# before first vote, not votes file exists
	}
	Lock::lock("data/screen", "votes");
	open(LOG, "data/screen/votes.dat") ||
		::handleError("Could not read votes");
	my ($timestamp, $user, $reference, $vote, $reason);
	while (<LOG>) {
		chomp;
		if (/^\d+:/) {
			($timestamp, $user, $reference, $vote, $reason) = 
				/^(\d+?):(.+?):(\d+?):(\d?):(.*)/;
			$votes->{$reference}->{$user}->{"vote"} = $vote;
			$votes->{$reference}->{$user}->{"reason"} = Format::trim($reason);
		} else {
			# this works since we are in control of the file format
			$votes->{$reference}->{$user}->{"reason"} .= 
				"\n" . Format::trim($_);
		}
	}
	close(LOG);
	Lock::unlock("data/screen", "votes");
	return $votes;
}

sub getReviews {
	my ($reference) = @_;
	my $reviews;
	unless (-e "data/screen/votes.dat") {
		return $reviews;	# before first vote, not votes file exists
	}
	Lock::lock("data/screen", "votes");
	open(LOG, "data/screen/votes.dat") ||
		::handleError("Could not read votes");
	my ($timestamp, $user, $_reference, $vote, $reason);
	while (<LOG>) {
		chomp;
		if (/^\d+:/) {
			($timestamp, $user, $_reference, $vote, $reason) = 
				/^(\d+?):(.+?):(\d+?):(\d?):(.*)/;
			if ($reference eq $_reference) {
				$reviews->{$user}->{"vote"} = $vote;
				$reviews->{$user}->{"reason"} = Format::trim($reason);
			}
		} else {
			$reviews->{$user}->{"reason"} .= 
				"\n" . Format::trim($_);
		}
	}
	close(LOG);
	Lock::unlock("data/screen", "votes");
	return $reviews;
}

# TODO: find all references, and point them to Assign module
sub getAssignments {
	my ($user) = @_;
	return Assign::getAssignmentsForReviewer($user);
}

1;
