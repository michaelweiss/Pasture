package Decision;

use CGI;

use lib '.';
use Core::Audit;
use Core::Serialize;
use Core::Screen;
use Core::Shepherd;

our $config = Serialize::getConfig();
our $WEBCHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $baseUrl = $config->{"url"};

my $LOCK = 2;
my $UNLOCK = 8;

# Create directory for decisions, if one does not exist
unless (-e "data/decision") {
	mkdir("data/decision", 0755) || 
		Audit::handleError("Cannot create decision directory");
}



=pod
Assumption: Each paper isreviewed by multiple PC members, including 
the one who oversaw the shepherding process. Second reviewers for each paper
are specified in data/decision/assignments.dat. The format is:

reference:pc_member1,pc_member2,...

STATUS: incomplete
=cut

sub getSecondReviewersForPaper {
	my ($reference) = @_;
	my $currentReference;
	my @reviewers;
	open (ASSIGNMENTS, "data/decision/assignments.dat") ||
		die "Internal: could not read assignments";
	# TODO: parse code not robust against syntax errors or empty lines
	while (<ASSIGNMENTS>) {
		chomp;
		($currentReference, @reviewers) = split(/, /);
		last if ($currentReference == $reference);
	}
	close (ASSIGNMENTS);
	return @reviewers;
}

=pod
Save vote.
=cut

sub saveVote {
	my ($timestamp, $user, $reviewRole, $reference, $vote, $reason) = @_;
	$reason =~ s/\n/ /g;		# remove newlines
	$reason =~ s/\r//g;	 		# this caused some reasons to be multi-line in Screen.pm
	$reason =~ s/:/&#58;/g;		# colon used to separate fields, must escape
	_lock("data/decision", "votes");
	open(LOG, ">>data/decision/votes.dat") ||
		::handleError("Could not save vote");
	print LOG "$timestamp:$user:$reviewRole:$reference:$vote:$reason\n";
	close(LOG);
	_unlock("data/decision", "votes");
}

=pod
Get all reviews for a submission.
=cut

sub getReviews {
	my ($reference) = @_;
	my $reviews;
	unless (-e "data/decision/votes.dat") {
		return $reviews;	# before first vote, not votes file exists
	}
	_lock("data/decision", "votes");
	open(LOG, "data/decision/votes.dat") ||
		::handleError("Could not read votes");
	while (<LOG>) {
		chomp;
		my ($timestamp, $user, $review_role, $_reference, $vote, $reason) = split(/:/);
		if ($reference eq $_reference) {
			$reviews->{$user}->{"vote"} = $vote;
			$reviews->{$user}->{"reason"} = Format::trim($reason);
			$reviews->{$user}->{"review_role"} = $review_role;
		}
	}
	close(LOG);
	_unlock("data/decision", "votes");
	return $reviews;
}

=pod
Read all votes.
=cut

sub votes {
	my $votes;
	unless (-e "data/decision/votes.dat") {
		return $votes;	# before first vote, not votes file exists
	}
	_lock("data/decision", "votes");
	open(LOG, "data/decision/votes.dat") ||
		::handleError("Could not read votes");
	while (<LOG>) {
		chomp;
		my ($timestamp, $user, $review_role, $reference, $vote, $reason) = split(/:/);
		$votes->{$reference}->{$user}->{"vote"} = $vote;
		$votes->{$reference}->{$user}->{"reason"} = Format::trim($reason);
		$votes->{$reference}->{$user}->{"review_role"} = $review_role;
	}
	close(LOG);
	_unlock("data/decision", "votes");
	return $votes;
}

=pod
Get user's vote.
=cut

sub userVote {
	my ($votes, $user, $reference) = @_;
	my $reviews = $votes->{$reference};
	if ($reviews) {
		$review = $reviews->{$user};
		if ($review) {
			return $review->{"vote"};
		}
	}
	return 0;
}

=pod
Get all screening assignments for a user (except rejected ones).
=cut

sub getScreenAssignmentsExceptRejected {
	my ($user) = @_;
	my @papers = Screen::getAssignments($user);
	my @assignedPapers;
	foreach $paper (@papers) {
		unless (Shepherd::status($paper) eq "rejected" ||
			Shepherd::status($paper) eq "withdrawn") {
			push (@asssignedPapers, $paper);
		}
	}
	return @asssignedPapers;
}

=pod
Get indicator of review status.
=cut

sub trafficLights {
	my ($reference) = @_;
	my $reviews = Decision::getReviews($reference);
	my @reviewers = keys %$reviews;
	my $lights = "<table border=1 cellpadding=0 cellspacing=0><tr>";
	if (scalar @reviewers == 0) {
		return "";
	}
	foreach $reviewer (@reviewers) {
		my $review = $reviews->{$reviewer};
		my $vote = $review->{"vote"};
		my $color;
		if ($vote eq "2") {				# accept for writer's workshop
			$color = "lightgreen";
		} elsif ($vote eq "1") {		# accept for writing group
			$color = "yellow";
		} elsif ($vote eq "0") {		# reject
			$color = "red";
		} elsif ($vote eq "-1") {		# not assessed
			$color = "white";
		}
		$lights .= "<td bgcolor=$color height=10 width=10></td>";
	}
	$lights .= "</tr></table>";
	return $lights;
}

=pod
These are utilities.
=cut

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