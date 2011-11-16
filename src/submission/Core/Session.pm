package Session;

sub uniqueId {
	# Return a unique id (using Apache's mod_unique_id module)
	my $uniqueId = $ENV{UNIQUE_ID};
	if ($uniqueId eq "") {
		# Required for testing on servers that do not use the mod_unique_id module
		# Hillside server does, so this will not be used during deployment
		$uniqueId = 1 + int(rand(10000));
	}
    return $uniqueId;
}

sub create {
	my ($session, $timestamp) = @_;
	unless ($timestamp) {
		$timestamp = time();
	}
	_lock("data", "sessions");
	my %sessions;
	dbmopen(%sessions, "data/sessions", 0666) ||
		::handleError("Internal: cannot open session database");
	$sessions{$session} = $timestamp;
	_unlock("data", "sessions");
	return $session;
}

# setUser expects that a session with session id exists
sub setUser {
	my ($session, $user, $role) = @_;
	_lock("data", "sessions");
	my %sessions;
	dbmopen(%sessions, "data/sessions", 0666) ||
		::handleError("Internal: cannot open session database");
	$sessions{$session} = $sessions{$session} . ":" . $user . ":" . $role;
	_unlock("data", "sessions");
	return $session;	
}

# return user and role from session info
sub getUserRole {
	my ($session) = @_;
	my $info = Session::check($session);
	return $info =~ /:(.+?):(.+)/;
}

# return timestamp from session info
sub getTimestamp {
	my ($session) = @_;
	my $info = Session::check($session);
	my ($time) = $info =~ /^(.+?):/;
	return $time;
}

sub check {
	my ($session) = @_;
	unless ($session) {
		return "";  # not a valid session key
	}
	_lock("data", "sessions");
	my %sessions;
	dbmopen(%sessions, "data/sessions", 0666) ||
		::handleError("Internal: cannot open session database");
	my $timestamp = $sessions{$session};
	_unlock("data", "sessions");
#	if ($timeout > 0) {
#		if (time() - $timestamp > $timeout) {
#			invalidate($session);	# remove timed out sessions
#			return 0;
#		}
#	}
	return $timestamp;
}

sub invalidate {
	my ($session) = @_;
	_lock("data", "sessions");
	my %sessions;
	dbmopen(%sessions, "data/sessions", 0666) ||
		::handleError("Internal: cannot open session database");
	delete $sessions{$session};
	_unlock("data", "sessions");
}

sub sessions {
	my ($session) = @_;
	_lock("data", "sessions");
	my %sessions;
	dbmopen(%sessions, "data/sessions", 0666) ||
		::handleError("Internal: cannot open session database");
	my @keys = keys %sessions;
	_unlock("data", "sessions");
	return @keys;
}

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