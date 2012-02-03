package Review;

use CGI;

use lib '.';
use Core::Tags;
use Core::Screen;
use Core::Audit;

use Core::Serialize;
use Core::Serialize::Records;
use Core::Email;

use Core::Role;

our $config = Serialize::getConfig();
our $WEB_CHAIR = $config->{"web_chair"};
our $WEB_CHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $CONFERENCE_ID = $config->{"conference_id"};
our $baseUrl = $config->{"url"};

my $LOCK = 2;
my $UNLOCK = 8;

# deprecated
sub authenticate {
	my ($email, $password) = @_;
	my $role = "";
	_lock("data", "roles");
	open (ROLES, "data/roles.dat") ||
		Audit::handleError("Internal: could not check login");
	while (<ROLES>) {
		if (/^$email, $password, (\w+)/) {
			$role = $1;
			last;
		}	# lines that don't match are skipped
	}
	close (ROLES);
	_unlock("data", "roles");
	return $role;
}

# TODO: move to Core::Screen
sub canSeeRecord {
	my ($user, $label) = @_;
	if ($user eq $config->{"program_chair_email"}) {
		return 1;			# program chair can see all
	}
	my @submissions = Screen::getAssignments($user);
	$label =~ /_(\d+)/;		# get reference from record name (format: timestamp_reference)
	my $ref = $1;
	foreach $submission (@submissions) {
		if ($submission eq $ref) {
			return 1;		# in list of assigned submissions
		}
	}
	return 0;
}

sub getAuthors {
	my ($record) = @_;
	my $byline = $record->param("authors");
	@authors = split(/\r\n/, $byline);
	foreach (@authors) {
		chomp;
		s/,.+//;
	}
	$byline = join(", ", @authors);
	return $byline;
}

sub numberOfVotes {
	my ($votes, $reference) = @_;
	my $n = values %{$votes->{$reference}};
	return $n;
}
	
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

sub averageVote {
	my ($votes, $reference) = @_;
	my @users = values %{$votes->{$reference}};
	my $sum = 0;
	foreach $user (@users) {
		$sum += $user->{"vote"};
	}
	my $n = @users;
	if ($n == 0) {
		return 0;
	}
	return int(10*$sum/$n)/10;
}

sub getTags {
	my ($record) = @_;
	my $tags = $record->param("tags");
	@tags = split(/\s*\r\n/, $tags);
	my @normalizedTags;
	foreach (@tags) {
		$_ = Tags::_normalize($_);
		if ($_) {
			push @normalizedTags, $_;
		}
	}
	$tags = join(", ", @normalizedTags);
	return $tags;
}

sub containsTag {
	my ($record, $tag) = @_;
	my $tags = $record->param("tags");
	my @tags = split(/\s*\r\n/, $tags);
	my @normalizedTags;
	foreach (@tags) {
		$_ = Tags::_normalize($_);
		if ($_) {
			push @normalizedTags, $_;
		}
	}
	foreach (@normalizedTags) {
		if (/$tag/) {
			return 1;
		}
	}
	return 0;
}

sub abstractContainsTag {
	my ($record, $tag) = @_;
	my $abstract = $record->param("abstract");
	return $abstract =~ $tag;
}

# deprecated
sub addReviewer {
	my ($email, $name, $role) = @_;
	# DONE: guarantee that entries are unique
	if (getReviewerName($email)) {
		Audit::handleError("Name already in reviewer list");
	}
	_lock("data", "reviewers");
	open(REVIEWERS, ">>data/reviewers.dat") ||
		Audit::handleError("Could not write to reviewer file");
	print REVIEWERS "$email, $name, $role\n";
	close(REVIEWERS);
	_unlock("data", "reviewers");
}

# TODO: need to re-implement
sub getReviewerName {
	my ($email) = @_;
	my $name = "";
	_lock("data", "reviewers");
	open(REVIEWERS, "data/reviewers.dat") ||
		Audit::handleError("Could not access reviewer file");
	while (<REVIEWERS>) {
		if (/^$email, (.+?),/) {
			$name = $1;
			last;
		}	# lines that don't match are skipped
	}
	close(REVIEWERS);
	_unlock("data", "reviewers");
	return $name;
}

sub getReviewerEmail {
	my ($user) = @_;
	my %contact = Contact::loadContact($user);
	return $contact{"email"};
}

# DONE: need to re-implement
sub getProgramCommitteeMembers {
	return Role::getUsersInRole($CONFERENCE_ID, "pc");
}

sub getReviewersForPaper {
	my ($reference) = @_;
	my @reviewers;
	open (ASSIGNMENTS, "data/screen/assignments.dat") ||
		die "Internal: could not read assignments";
	# TODO: parse code not robust against syntax errors or empty lines
	while (<ASSIGNMENTS>) {
		chomp;
		my ($reviewer, @submissions) = split(/, /);
		foreach (@submissions) {
			if ($_ == $reference) {
				push(@reviewers, $reviewer);
				last;
			}
		}
	}
	close (ASSIGNMENTS);
	return @reviewers;
}

# deprecated
sub addRole {
	my ($email, $password, $role) = @_;
	# TODO: means that each user can only have one role (verify)
	if (getRole($email)) {
		return;
	}
	_lock("data", "roles");
	open (ROLES, ">>data/roles.dat") ||
		Audit::handleError("Internal: could not write to roles file");
	print ROLES "\n";	 # pre-pend with \n to be robust against manual editing of roles file
	print ROLES "$email, $password, $role";
	close (ROLES);
	_unlock("data", "roles");	
}

# deprecated
sub getRole {
	my ($email) = @_;	
	my $role = "";
	_lock("data", "roles");
	open (ROLES, "data/roles.dat") ||
		Audit::handleError("Internal: could not check role");
	while (<ROLES>) {
		if (/^$email, \w+, (\w+)/) {
			$role = $1;
			last;
		}	# lines that don't match are skipped
	}
	close (ROLES);
	_unlock("data", "roles");
	return $role;
}

# deprecated
sub getPassword {
	my ($email) = @_;	
	my $password = "";
	_lock("data", "roles");
	open (ROLES, "data/roles.dat") ||
		Audit::handleError("Internal: could not check role");
	while (<ROLES>) {
		if (/^$email, (\w+), \w+/) {
			$password = $1;
			last;
		}	# lines that don't match are skipped
	}
	close (ROLES);
	_unlock("data", "roles");
	return $password;
}

# deprecated
# Recover the password for a submission. Send to the contact author's email.
# $reference is the reference number of the submission
sub sendPasswordForEmail {
	my ($email) = @_;
	
	# get record metadata
	my %labels = Records::listCurrent();
	my $record = Records::getRecord($labels{$reference}); 
	
	my $name = Review::getReviewerName($email);
	my ($sanitizedName) = $name	=~ m/([\w\s-]*)/;	
	my $tmpFileName = Email::tmpFileName($timestamp, $sanitizedName);
	my ($firstName) = $sanitizedName =~ /^(\w+)/;	
	
	my $password = Review::getPassword($email);
	open (MAIL, ">$tmpFileName") || 
		Audit::handleError("Cannot create temporary file");
	if ($password) {
	print MAIL <<END;
Dear $firstName,

your reviewer password is: $password.

$WEB_CHAIR
$CONFERENCE Web Chair
END
	} else {
	print MAIL <<END;
We tried very hard to retrieve your password, but there is none for the email address you provided. Please check if you used the right email address.

$WEB_CHAIR
$CONFERENCE Web Chair
END
	}
	close (MAIL);
	my $status = Email::send($email, "",
		"[$CONFERENCE] Recovered reviewer password", 
		$tmpFileName, 0);
	return $status;
}


# Utilities

# deprecated
# TODO: throw error if unable to lock/unlock
sub _lock {
	my ($directory, $resource) = @_;
	open(LOCK, ">$directory/$resource.lock");
	flock(LOCK, $LOCK);
}

# deprecated
sub _unlock {
	my ($directory, $resource) = @_;
	unlink("$directory/$resource.lock");
}

1;