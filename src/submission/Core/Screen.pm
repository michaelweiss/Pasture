package Screen;

use lib '.';
use Core::Format;

sub saveVote {
	my ($timestamp, $user, $reference, $vote, $reason) = @_;
	$reason =~ s/\n/ /g;
	_lock("data/screen", "votes");
	open(LOG, ">>data/screen/votes.dat") ||
		::handleError("Could not save vote");
	print LOG "$timestamp:$user:$reference:$vote:$reason\n";
	close(LOG);
	_unlock("data/screen", "votes");
}

# TODO: refactor to getAllReviews
sub votes {
	my $votes;
	unless (-e "data/screen/votes.dat") {
		return $votes;	# before first vote, not votes file exists
	}
	_lock("data/screen", "votes");
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
	_unlock("data/screen", "votes");
	return $votes;
}

sub getReviews {
	my ($reference) = @_;
	my $reviews;
	unless (-e "data/screen/votes.dat") {
		return $reviews;	# before first vote, not votes file exists
	}
	_lock("data/screen", "votes");
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
	_unlock("data/screen", "votes");
	return $reviews;
}

sub getAssignments {
	my ($user) = @_;
	open (ASSIGNMENTS, "data/screen/assignments.dat") ||
		die "Internal: could not read assignments";
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
	
# Utilitites

sub _lock {
	my ($directory, $resource) = @_;
	open(LOCK, ">$directory/$resource.lock");
	flock(LOCK, $LOCK);
}

sub _unlock {
	my ($directory, $resource) = @_;
	unlink("$directory/$resource.lock");
}

1;