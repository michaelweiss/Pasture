#!/usr/bin/perl

use lib '.';
use Core::Serialize;
use Core::Serialize::Records;

my %assignments;
my %reviewers;

my $config = Serialize::getConfig();
my $PROGRAM_CHAIR = $config->{"program_chair_email"};

sub loadReviewers {
	open (ROLES, "data/roles.dat") ||
		die "Internal: could not read reviewers";
	while (<ROLES>) {
		my ($user, $password, $role) = split(/, /);
		$reviewers{$user} = $role;
	}
	close (ROLES);
}

sub assign {
	my %records = Records::getAllRecords(Records::listCurrent());
	my $currentTrack = -1;
	foreach $label (sort { $records{$a}->param("track") <=> $records{$b}->param("track") }
			sort { $records{$a}->param("reference") <=> $records{$b}->param("reference") } 
				keys %records) {
		my $record = $records{$label};
		my $track = $record->param("track");
		if ($currentTrack != $track) {
			print "\nassigning track $track:\n";
			$currentTrack = $track;
		}
		my $reference = $record->param("reference");
		
		# program chair sees all papers
		assignPaper($PROGRAM_CHAIR, $reference);
		
		# track chairs see all track submissions
		# note: need to check if track chair is program chair
		my $trackChair = getTrackChair($track);
		unless ($trackChair eq $PROGRAM_CHAIR) {
			assignPaper($trackChair, $reference);
		}
		
		# each track submission is seen by one pc member
		# note: need to ensure different from track chair, if s/he is a pc member
		# note: need to ensure that there is no conflict of interest
		my $secondReviewer;
		do {
			$secondReviewer = chooseReviewerExcept($PROGRAM_CHAIR, $trackChair);
		} while (isConflictOfInterest($secondReviewer, $reference));
		assignPaper($secondReviewer, $reference);
	}
}

sub assignPaper {
	my ($reviewer, $paper) = @_;
	print "assign $paper to $reviewer\n";
	unless ($reviewer) {
		print "error: no reviewer specified\n";
		return;
	}
	push(@{$assignments{$reviewer}}, $paper);
}

sub listAssignments {
	print "\n";
	foreach $reviewer (keys %reviewers) {
		print "$reviewer";
		foreach $paper (@{$assignments{$reviewer}}) {
			print ", $paper";
		}
		print "\n";
	}
}

sub getTrackChair {
	my ($track) = @_;
	# format: track_N_chair_email
	return $config->{"track_" . $track . "_chair_email"};
}	

# TODO: should seed random number generator, eg with current time
# TODO: should really balance among reviewers (it is an issue: checked the naive approach)
sub chooseReviewerExcept {
	my @exceptions = @_;
	my @reviewers = keys %reviewers;
	foreach $excluded (@exceptions) {
		@reviewers = removeFromList($excluded, @reviewers);
	}
	print "pool of reviewers: @reviewers\n";
	my $pool = @reviewers;
	print "pool.size=$pool\n";
	my $selected = int rand($pool);
	print "pool.selected=$selected\n";
	return $reviewers[$selected];
}		

# TODO: check if such a function exists already
sub removeFromList {
	my ($elem, @list) = @_;
	my @copyOfList;
	foreach $e (@list) {
		unless ($e eq $elem) {
			push(@copyOfList, $e);
		}
	}
	return @copyOfList;
}

# TODO: check for conflicts of interest, there are several options:
# 1. easiest implementation is to create a file of conflicts, but needs extra effort
# 2. lookup full name of reviewer from email (should be in reviewers.dat file), and check
#    if they are an author of this paper
# 3. combine 1 and 2 by computing a list of conflicts offline and put it in a file: this
#    reasonable because it allows somebody to check if the conflict are real conflicts
sub isConflictOfInterest {
	my ($reviewer, $paper) = @_;
	return 0;
}
		
loadReviewers();
assign();
listAssignments();

