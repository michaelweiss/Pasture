package Contact;

use lib '.';
use Core::Audit;
use Core::Lock;

sub saveContact {
	my ($user, $email) = @_;
	Lock::lock("data", "contacts");
	open(LOG, ">>data/contacts.dat") ||
		Audit::handleError("Could not save contact information");
	print LOG "$user\t$email\n";
	close(LOG);
	Lock::unlock("data", "contacts");
}

sub loadContact {
	my ($user) = @_;
	Lock::lock("data", "contacts");
	open(LOG, "data/contacts.dat") ||
		Audit::handleError("Could not load contact information");
	while (<LOG>) {
		if (/^$user\t/) {	
			chomp;
			@contact = split(/\t/);
		}
	}
	my %contact, $i=0;
	foreach $key ("user", "email") {
		$contact{$key} =  $contact[$i++];
	}
	close(LOG);
	Lock::unlock("data", "contacts");
	return %contact;
}

# Find contact by email
# TODO: refactor (only one line different from loadContact)
sub lookupContactByEmail {
	my ($email) = @_;
	Lock::lock("data", "contacts");
	open(LOG, "data/contacts.dat") ||
		Audit::handleError("Could not load contact information");
	while (<LOG>) {
		if (/^\w+\t$email$/) {	
			chomp;
			@contact = split(/\t/);
		}
	}
	my %contact, $i=0;
	foreach $key ("user", "email") {
		$contact{$key} =  $contact[$i++];
	}
	close(LOG);
	Lock::unlock("data", "contacts");
	return %contact;
}

sub loadAllContacts {
	Lock::lock("data", "contacts");
	my @contacts;
	open(LOG, "data/contacts.dat") ||
		Audit::handleError("Could not load contact information");
	while (<LOG>) {
		if (/^(.+?)\t/) {	
			push(@contacts, $1);
		}
	}
	return @contacts;
}

1;
