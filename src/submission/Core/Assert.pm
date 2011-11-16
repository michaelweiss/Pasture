package Assert;

use CGI;

# validation functions

sub assertEquals {
	my ($name, $pattern, $error) = @_;
	unless ($::q->param($name) =~ /$pattern/) {
		::handleError($error);
	}
}

sub assertNotEmpty {
	my ($name, $error) = @_;
	unless ($::q->param($name)) {
		::handleError($error);
	}
}

sub assertTrue {
	my ($condition, $error) = @_;
	unless ($condition) {
		::handleError($error);
	}
}

1;