package Lock;

use lib '.';
use Core::Audit;

sub lock {
	my ($directory, $resource) = @_;
	open(LOCK, ">$directory/$resource.lock") ||
		Audit::handleError("Can't create lock: $directory/$resource.lock");
	flock(LOCK, $LOCK);
}

sub unlock {
	my ($directory, $resource) = @_;
	unlink("$directory/$resource.lock");
}

1;