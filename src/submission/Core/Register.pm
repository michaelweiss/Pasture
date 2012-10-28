package Register;

use Core::Review;

our @fields = ("email", "name", "affiliation", "address_line_1", "address_line_2", "city", "state", "postal_code", "country", "phone", "gender", "billing_address", "author", "focus_group_leader", "room", "room_mate", "participants", "children", "vegetarian", "fee", "comments", "workshop", "focus_group_1", "focus_group_2", "name_on_card", "card_type");

# Create directory for registrations, if one does not exist
unless (-e "data/registration") {
	mkdir("data/registration", 0755) || 
		Audit::handleError("Cannot create registration directory");
}


=pod
Authenticate by checking account in admin, pc, reviewer or shepherd role. Then check if
the user has submitted a paper as an author.
TODO: deprecated
=cut
sub authenticate {
	my ($email, $password) = @_;
	my $role = Review::authenticate($email, $password);
	if ($role) {
		return $role;
	}
	if (checkParticipantPassword($email, $password)) {
		return "participant";
	}
	return "";
}


=pod
Get password.
TODO: deprecated
=cut
sub getPassword {
	my ($email) = @_;
	# TODO: add code to get author password
	# what is the purpose of this method: to get a password, or to check that a password 
	# has been assigned to this user, and that they do not need a new password?
	my $password = Review::getPassword($email) ||
		getParticipantPassword($email);
	if ($password) {
		return $password;
	}
	return "";
}


=pod
Guess user name from existing records.
=cut
sub getName {
	my ($email, $role) = @_;
	if ($role eq "author") {
		# TODO: get author name from submission record	
		return "";	
	} else {	# it's a reviewer
		return Review::getReviewerName($email);
	}
}


=pod
Add participant.
TODO: deprecated
=cut
sub logParticipantPassword {
	my ($email, $password) = @_;
	open (PASSWORD, ">>data/registration/password.dat") ||
		Audit::handleError("Internal: could not save password");
	flock(PASSWORD, $LOCK);
	print PASSWORD "$email, $password\n";
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
}


=pod
Check participant password.
TODO: deprecated
=cut
sub checkParticipantPassword {
	my ($email, $password) = @_;
	my $found = 0;
	unless (-e "data/registration/password.dat") {
		return $found;
	}
	open (PASSWORD, "data/registration/password.dat") ||
		Audit::handleError("Internal: could not check participant login");
	flock(PASSWORD, $LOCK);
	while (<PASSWORD>) {
		if (/^$email, $password/) {
			$found = 1;
			last;
		}
	}
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
	return $found;
}


=pod
Get participant password.
TODO: deprecated
=cut
sub getParticipantPassword {
	my ($email) = @_;	
	my $password = "";
	unless (-e "data/registration/password.dat") {
		return $password;
	}
	_lock("data/registration", "password");
	open (PASSWORD, "data/registration/password.dat") ||
		Audit::handleError("Internal: could not check participant login");
	while (<PASSWORD>) {
		if (/^$email, (\w+)/) {
			$password = $1;
			last;
		}	# lines that don't match are skipped
	}
	close (PASSWORD);
	_unlock("data/registration", "password");
	return $password;
}


=pod
Save registration info.
=cut
sub saveRegistration {
	my ($timestamp, $q) = @_;
		
	my $comments = $q->param("comments");
	$comments =~ s/\r\n/ /g;
	$q->param("comments" => $comments);

	my $billing_address = $q->param("billing_address");
	$billing_address =~ s/\r\n/, /g;
	$q->param("billing_address" => $billing_address);

	_lock("data/registration", "participants");
	open(LOG, ">>data/registration/participants.dat") ||
		Audit::handleError("Could not save registration information");
	print LOG "$timestamp";
	foreach $field (@fields) {
		# TODO: generalize to other multi-valued fields
		# TODO: no longer using focus_groups field
		unless ($field eq "focus_groups") {
			print LOG ":" . $q->param($field);
		} else {
			my @values = $q->param($field);
			print LOG ":" . join(',', @values);
		}
	}
	print LOG "\n";
	close(LOG);
	_unlock("data/registration", "participants");
}


=pod
Load registration info.
=cut
sub loadRegistration {
	my ($user, $q) = @_;
	_lock("data/registration", "participants");
	open(LOG, "data/registration/participants.dat") ||
		Audit::handleError("Could not load registration information");
	my @registration;
	while (<LOG>) {
		if (/^\d+:$user:/) {	# first element is timestamp
			chomp;
			@registration = split(/:/);
		}
	}
	$q->param( "timestamp" => $registration[0] );
	my $i = 1;
	foreach $field (@fields) {
		# TODO: generalize to other multi-valued fields
		unless ($field eq "focus_groups") {
			$q->param( $field => $registration[$i++] );
		} else {
			my @values = split(/,/, $registration[$i++]);
			$q->param( $field, @values );
		}		
	}
	close(LOG);
	_unlock("data/registration", "participants");
}


=pod
Return all registrations.
=cut
sub getAllRegistrations {
	_lock("data/registration", "participants");
	open(LOG, "data/registration/participants.dat") ||
		Audit::handleError("Could not load registration information");
	my %registrations;
	while (<LOG>) {
		if (/^\d+/) {
			chomp;
			my @record = split(/:/);
			# override any existing entries for the user, thus the hash contains
			# the most recent entry for each user
			# implementation note: $record[1] is the user's email
			if ($record[1]) {
				$registrations{$record[1]} = \@record;
			}
		}
	}
	close(LOG);
	_unlock("data/registration", "participants");
	return %registrations;
}

=pop
Return a CSV list with all registrations.
=cut
sub getAllRegistrationsAsCsvList {
	my %registrations = getAllRegistrations();
	my @table;
	foreach $record (values %registrations) {
		my @quoted = map { "\"$_\"" } @$record;
		my $row = join(',', @quoted);
		push(@table, $row);
	}
	return sort @table;
}


=pod
Get focus groups.
=cut
sub getFocusGroups {
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