package Password;

use lib '.';
use Core::Audit;
use Core::Assert;

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

sub _salt {
	my ($password) = @_;
	Assert::assertTrue($::config->{"salt"}, "Admin: salt not configured");
	return crypt($password, $::config->{"salt"});
}

sub checkUserPassword {
	my ($user, $password) = @_;
	# create hash of password
	$password = _salt($password);
	
	my $match = 0;
	open (PASSWORD, "data/password.dat") ||
		return "";
	flock(PASSWORD, $LOCK);
	while (<PASSWORD>) {
		if (/^$user\t$password$/) {
			$match = 1; 
			last;
		}
	}
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
	return $match;
}

sub logUserPassword {
	my ($user, $password) = @_;
	# create hash of password
	$password = _salt($password);
	
	open (PASSWORD, ">>data/password.dat") ||
		Audit::handleError("Internal: could not save password");
	flock(PASSWORD, $LOCK);
	print PASSWORD "$user\t$password\n";
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
}

# retrieves password hash: can use this to check whether user exists
# DONE: create a better name for this function
sub existsUser {
	my ($user) = @_;
	# user name should not be case sensitive
	$user = lc($user);

	my $match = "";
	open (PASSWORD, "data/password.dat") ||
#		Audit::handleError("Internal: could not check login");
		return "";
	flock(PASSWORD, $LOCK);
	while (<PASSWORD>) {
		if (/^$user\t(.+)$/) {
			$match = $1; 
			last;
		}
	}
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
	return $match;	
}

1;
