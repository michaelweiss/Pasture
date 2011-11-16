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

sub checkPassword {
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

sub logPassword {
	my ($reference, $email, $password) = @_;
	open (PASSWORD, ">>data/password.dat") ||
		Audit::handleError("Internal: could not save password");
	flock(PASSWORD, $LOCK);
	print PASSWORD "$reference, $email, $password\n";
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
}

sub retrievePassword {
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

# TODO: refactor
sub getReferencesByAuthor {
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


