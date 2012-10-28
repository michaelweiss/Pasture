package Shepherd;

use lib '.';
use Core::Format;
use Core::Audit;

# Create directory for shepherding assignments and votes, if one does not exist
unless (-e "data/shepherd") {
	mkdir("data/shepherd", 0755) || 
		Audit::handleError("Cannot create shepherd directory");
}

sub savePreference {
	my ($timestamp, $user, $reference, $priority) = @_;
	$reason =~ s/\n/ /g;
	_lock("data/shepherd", "preferences");
	open(LOG, ">>data/shepherd/preferences.dat") ||
		Audit::handleError("Could not save preferences");
	print LOG "$timestamp:$user:$reference:$priority\n";
	close(LOG);
	_unlock("data/shepherd", "preferences");
}

sub preferences {
	my $preferences;
	unless (-e "data/shepherd/preferences.dat") {
		return $preferences;	# before first preference, no preferences file exists
	}
	_lock("data/shepherd", "preferences");
	open(LOG, "data/shepherd/preferences.dat") ||
		Audit::handleError("Could not read preferences");
	while (<LOG>) {
		chomp;
		my ($timestamp, $user, $reference, $priority) = split(/:/);
		if ($timestamp =~ /\d+/) {
			$preferences->{$reference}->{$user}->{"timestamp"} = $timestamp;
			$preferences->{$reference}->{$user}->{"priority"} = $priority;
		}	# lines that don't match are skipped
	}
	close(LOG);
	_unlock("data/shepherd", "preferences");
	return $preferences;
}

sub preferencesByUser {
	my $preferences;
	unless (-e "data/shepherd/preferences.dat") {
		return $preferences;	# before first preference, no preferences file exists
	}
	_lock("data/shepherd", "preferences");
	open(LOG, "data/shepherd/preferences.dat") ||
		Audit::handleError("Could not read preferences");
	while (<LOG>) {
		chomp;
		my ($timestamp, $user, $reference, $priority) = split(/:/);
		if ($timestamp =~ /\d+/) {
			$preferences->{$user}->{$reference}->{"timestamp"} = $timestamp;
			$preferences->{$user}->{$reference}->{"priority"} = $priority;
		}	# lines that don't match are skipped
	}
	close(LOG);
	_unlock("data/shepherd", "preferences");
	return $preferences;
}
	
sub status {
	my ($reference) = @_;
	unless (-e "data/shepherd/status.dat") {
		return "";
	}
	_lock("data/shepherd", "status");
	my $status = "";
	open(STATUS, "data/shepherd/status.dat") ||
		Audit::handleError("Could not read status file");
	while (<STATUS>) {
		chomp;
		# assumption: status can be set multiple times, so you want to
		# read the last value (TODO: this could be optimized)
		if (/^(\d+):$reference:(\w*)/) {
			$status = $2;
		}	# lines that don't match are skipped
	}
	close(STATUS);
	_unlock("data/shepherd", "status");
	return $status;
}

sub changeStatus {
	my ($timestamp, $reference, $status) = @_;
	# TODO: read from "data/shepherd/status.dat" file
	_lock("data/shepherd", "status");
	open(STATUS, ">>data/shepherd/status.dat") ||
		Audit::handleError("Could not access status file");
	print STATUS "$timestamp:$reference:$status\n";
	close(STATUS);
	_unlock("data/shepherd", "status");
	return $status || "review";
}

sub assign {
	my ($timestamp, $reference, $shepherd, $pc) = @_;
	_lock("data/shepherd", "assignments");
	open(ASSIGNMENTS, ">>data/shepherd/assignments.dat") ||
		Audit::handleError("Could not access assignments file");
	print ASSIGNMENTS "$timestamp:$reference:$shepherd:$pc\n";
	close(ASSIGNMENTS);
	_unlock("data/shepherd", "assignments");
}

sub assignedTo {
	my ($reference) = @_;
	my %assignment;
	unless (-e "data/shepherd/assignments.dat") {
		return %assignments;
	}
	_lock("data/shepherd", "assignments");
	open(ASSIGNMENTS, "data/shepherd/assignments.dat") ||
		Audit::handleError("Could not access assignments file");
	while (<ASSIGNMENTS>) {
		chomp;
		# DONE: returns first match (should this be the last one?)
		if (/^(\d+):$reference:(.+?):(.+)/) {
			$assignment{"shepherd"} = $2;
			$assignment{"pc"} = $3;
#			last;
		}	# lines that don't match are skipped
	}
	close(ASSIGNMENTS);
	_unlock("data/shepherd", "assignments");
	return %assignment;
}

sub papersAssigned {
	my %load;
	my %shepherds;
	unless (-e "data/shepherd/assignments.dat") {
		return %load;
	}
	_lock("data/shepherd", "assignments");
	open(ASSIGNMENTS, "data/shepherd/assignments.dat") ||
		Audit::handleError("Could not access assignments file");
	while (<ASSIGNMENTS>) {
		chomp;
		# DONE: does not work with reassignment (it does now!)
		if (/^(\d+):(\d+):(.+?):(.+)/) {
			my $shepherd = $3;
			if ($shepherds{$2}) {
				$load{$shepherds{$2}}--;
			}
			$load{$shepherd}++;
			$shepherds{$2} = $shepherd;
		}	# lines that don't match are skipped
	}
	close(ASSIGNMENTS);
	_unlock("data/shepherd", "assignments");
	return %load;
}

sub papersAssignedToSupervise {
	my %load;
	my %pcs;
	unless (-e "data/shepherd/assignments.dat") {
		return %load;
	}
	_lock("data/shepherd", "assignments");
	open(ASSIGNMENTS, "data/shepherd/assignments.dat") ||
		Audit::handleError("Could not access assignments file");
	while (<ASSIGNMENTS>) {
		chomp;
		# DONE: does not work with reassignment (it does now!)
		if (/^(\d+):(\d+):(.+?):(.+)/) {
			my $pc = $4;
			if ($pcs{$2}) {
				$load{$pcs{$2}}--;
			}
			$load{$pc}++;
			$pcs{$2} = $pcs;
		}	# lines that don't match are skipped
	}
	close(ASSIGNMENTS);
	_unlock("data/shepherd", "assignments");
	return %load;
}

sub assignments {
	my $assignments;
#		print "assignments:\n";
	unless (-e "data/shepherd/assignments.dat") {
		return %assignments;
	}
#		print "reading:\n";
	_lock("data/shepherd", "assignments");
	open(ASSIGNMENTS, "data/shepherd/assignments.dat") ||
		Audit::handleError("Could not access assignments file");
	while (<ASSIGNMENTS>) {
#		print "> $_";
		chomp;
		if (/^(\d+):(\d+):(.+?):(.+)/) {
			# format: timestamp:reference:shepherd:pc
			my $assignment = {
				"shepherd" => $3,
				"pc" => $4,
			};
			$assignments->{$2} = $assignment;
		}
	}
	close(ASSIGNMENTS);
	_unlock("data/shepherd", "assignments");
	return $assignments;
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