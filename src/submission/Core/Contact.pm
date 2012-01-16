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

1;
