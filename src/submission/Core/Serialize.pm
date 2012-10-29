package Serialize;

use Core::Audit;

my $LOCK = 2;
my $UNLOCK = 8;

# Create directory for submission records, if one does not exist
unless (-e "data/records") {
	mkdir("data/records", 0755) || 
		Audit::handleError("Cannot create records directory");
}


# TODO: consider moving to another module
sub getReference {
	_lock("data", "reference");
	
	my $reference;
	if (open(DATA, "data/reference.dat")) {
		$reference = <DATA> + 1;
		close(DATA);
	} else {
		$reference = 1;
	}

	open(DATA, ">data/reference.dat") ||
		Audit::handleError("Internal: could not set next reference");
	print DATA "$reference";
	close(DATA);

	_unlock("data", "reference");

	return $reference;
}

sub getConfig {
	_lock("data", "config");

	my %config;
	open(DATA, "data/config.dat") ||
		Audit::handleError("Internal: could not get config");
	while (<DATA>) {
		chomp;
		if (/^(\w+)=(.*)/) {
			$config{$1} = $2;
		}
	}
	close(DATA);

	_unlock("data", "config");	

	return \%config;
}

# TODO: not used in current code
sub setConfig {
	_lock("data", "config");

	my $config = shift;
	open(DATA, ">data/config.dat") ||
		Audit::handleError("Internal: could not set config");
	foreach (keys %$config) {
		print DATA "$_=$config->{$_}\n";
	}
	close(DATA);

	_unlock("data", "config");	
}

sub saveState {
	my ($name) = @_;
    open FILE, ">data/records/$name" || 
    	Audit::handleError("Internal: could not save submission record");
    $::q->save(FILE);
    close FILE;
}

sub loadState {
	my ($reference) = @_;
    opendir DIR, "data/records" ||
    	Audit::handleError("Internal: could not search submission records");
    # find most recent record for this reference
    # TODO: also want to get a list of records for a reference, and access a specific record by name
    # DONE: can get list of records for a reference already (see next line)
	@records = grep (/_$reference$/, readdir DIR);
    closedir DIR;
    my $name = $records[-1];	# we know there is at least one
#	print "reading record $name:\n";
    open FILE, "data/records/$name" ||
    	Audit::handleError("Internal: could not read submission record");
    my $q_saved = new CGI(FILE);
    close FILE;
    return $q_saved;
}

# Utilities

# TODO: refactor into its own module
sub _lock {
	my ($directory, $resource) = @_;
	open(LOCK, ">$directory/$resource.lock");
	flock(LOCK, $LOCK);
}

# TODO: refactor into its own module
sub _unlock {
	my ($directory, $resource) = @_;
	unlink("$directory/$resource.lock");
}

1;
