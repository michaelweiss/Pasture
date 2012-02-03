package Assert;

use CGI;
use Core::Audit;

# validation functions

sub assertEquals {
	my ($name, $pattern, $error) = @_;
	unless ($::q->param($name) =~ /$pattern/) {
		Audit::handleError($error);
	}
}

sub assertNotEmpty {
	my ($name, $error) = @_;
	unless ($::q->param($name)) {
		Audit::handleError($error);
	}
}

sub assertTrue {
	my ($condition, $error) = @_;
	unless ($condition) {
		Audit::handleError($error);
	}
}

1;