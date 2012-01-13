package Password;

use lib '.';
use Core::Audit;

my $LOCK = 2;
my $UNLOCK = 8;

my @symbols = ('0'..'9', 'a'..'z');

sub _randomNumber {
	my ($max) = @_;
	return int(rand() * $max);
}

sub generatePassword {
	my ($maxlen) = @_;
	my $password;
	until ($password) {
		$password = _generateSinglePassword($maxlen);
		if (_restricted($password)) {
			$password = "";
		}
	}
	return $password;
}

sub _generateSinglePassword {
	my ($maxlen) = @_;
	my $password;
	$password = join '', map { $symbols[_randomNumber($#symbols+1)] } 1..$maxlen;
	return $password;
}

# check for letter sequences that might offend some
# based on ideas in Crypt::GeneratePassword
sub _restricted {
	my ($password) = @_;
	return $password =~ /f.ck|ass|rsch|tit|cum|[aoi]ck|asm|orn|eil|otz|oes/i;
}

sub checkUserPassword {
	my ($user, $password) = @_;
	# TODO: convert user name to lower case, should be case-insensitive
	# TODO: create hash of password
	my $match = 0;
	open (PASSWORD, "data/password.dat") ||
		Audit::handleError("Internal: could not check login");
	flock(PASSWORD, $LOCK);
	while (<PASSWORD>) {
		if (/^$user, $password$/) {
			$match = 1; 
			last;
		}
	}
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
	return $match;
}

# obsolete
sub checkPassword_ {
	my ($reference, $email, $password) = @_;
	my $match = 0;
	open (PASSWORD, "data/password.dat") ||
		Audit::handleError("Internal: could not check login");
	flock(PASSWORD, $LOCK);
	# Can check password for reference or email
	if ($reference) {
		# Reference provided -> check password
		while (<PASSWORD>) {
			# Skip email
			if (/^$reference, .+?, $password/) {
				$match = 1; 
				last;
			}
		}
	} elsif ($email) {
		# Email provided -> check password
		while (<PASSWORD>) {
			# Skip reference
			if (/, $email, $password$/) {
				$match = 1; 
				last;
			}
		}
	}
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
	return $match;
}

sub logUserPassword {
	my ($user, $password) = @_;
	# TODO: convert user name to lower case, should be case-insensitive
	open (PASSWORD, ">>data/password.dat") ||
		Audit::handleError("Internal: could not save password");
	flock(PASSWORD, $LOCK);
	print PASSWORD "$user, $password\n";
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
}

# obsolete
sub logPassword_ {
	my ($reference, $email, $password) = @_;
	open (PASSWORD, ">>data/password.dat") ||
		Audit::handleError("Internal: could not save password");
	flock(PASSWORD, $LOCK);
	print PASSWORD "$reference, $email, $password\n";
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
}

sub retrieveUserPassword {
	my ($user) = @_;
	my $match = "";
	open (PASSWORD, "data/password.dat") ||
#		Audit::handleError("Internal: could not check login");
		return "";
	flock(PASSWORD, $LOCK);
	while (<PASSWORD>) {
		if (/^$user, (.+)$/) {
			$match = $1; 
			last;
		}
	}
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
	return $match;	
}

# obsolete
sub retrievePassword_ {
	my ($referenceOrEmail) = @_;
	my $match = "";
	open (PASSWORD, "data/password.dat") ||
		Audit::handleError("Internal: could not check login");
	flock(PASSWORD, $LOCK);
	# Can retrieve password for reference or email
	if ($referenceOrEmail =~ /^\d+$/) {
		# Reference provided -> retrieve password
		while (<PASSWORD>) {
			if (/^$referenceOrEmail, .+?, (.+)/) {
				$match = $1; 
				last;
			}
		}
	} else {
		# Email provided -> retrieve password
		while (<PASSWORD>) {
			# Skip reference
			if (/, $referenceOrEmail, (.+)$/) {
				$match = $1; 
				last;
			}
		}
	}
	
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
	return $match;
}

# TODO: now I need to create a submission log, or search the submission records
# second alternative requires less changes, even though it less efficient

# TODO: refactor
sub getReferencesByAuthor_ {
	my ($email) = @_;
	my @references;
	open (PASSWORD, "data/password.dat") ||
		Audit::handleError("Internal: could not check login");
	
	flock(PASSWORD, $LOCK);
	while (<PASSWORD>) {
		if (/^(\d+), $email,/) {
			push(@references, $1); 
		}
	}
	flock(PASSWORD, $UNLOCK);
	
	close (PASSWORD);
	return @references;
}


