package Email2;

use LWP;
use URI;
use URI::Escape ('uri_escape');
use Core::Audit;
use Core::Serialize;

# Setting debug results in the email printed on the screen, rather than
# being sent. Helpful for debugging. Turn off for deployment.
#
# TODO: should set debug flag in main script (but sending email already takes
# time, so this is not a high priority task)
our $config = Serialize::getConfig();
our $debug = $config->{"debug"};

our $WEB_CHAIR_EMAIL = $config->{"web_chair_email"};
our $PROGRAM_CHAIR_EMAIL = $config->{"program_chair_email"};
our $CONFERENCE_CHAIR_EMAIL = $config->{"conference_chair_email"};

# Set PATH and remove some environment variables for running in taint mode
# https://www.boards.ie/b/thread/2055293899

$ENV{ 'PATH' } = '/bin:/usr/bin:/usr/local/bin';
delete @ENV{ 'IFS', 'CDPATH', 'ENV', 'BASH_ENV' };

# Create temporary mail directory if one does not exist
unless (-e "data/mail") {
	mkdir("data/mail", 0755) || 
		Audit::handleError("Cannot create mail directory");
}

# Generate a temporary file name to hold email body.
#
# File name is generated from a timestamp and an id (anything unique, currently
# the full name of the recipient, eg "Joe Smith").
#
# This file will be used by Email::send.
sub tmpFileName {
	my ($timestamp, $id) = @_;
	$id =~ s/ //g;
	return "data/mail/tmp_${timestamp}_${id}.txt";
}

# Send email with optional copy to chairs.
#
# Body of email is expected in a temporary file named $body.
# $copy indicates whether chairs should be copied.
#
# Send email from within Perl.

sub send {
	my ($email, $cc, $subject, $body, $copy) = @_;
	my $page = "";
	$page .= headers($email, $cc, $subject, $copy);
	$page .= content($body);
	unless ($debug) {
		unless (open (MAIL, "| /usr/sbin/sendmail -t -i")) {
			$page = "Error sending mail\n";
		} else {
			print MAIL $page;
			close(MAIL) || warn "Error closing mail: $!";
		}
	} else {
		# don't send the actual email
	}
	return $page;
}

# When chairs are copied on the email, the chairs' addresses should be in the 
# reply-to field. Recipients expect to reply to the chairs.
sub headers {
	my ($email, $cc, $subject, $copy) = @_;
	my $headers = "From: $WEB_CHAIR_EMAIL\n";
	$headers .= "To: $email\n";
	# DONE: if copy flag set, send email with copy to chairs
	if ($copy) {
		$headers .= "Reply-To: $PROGRAM_CHAIR_EMAIL,$CONFERENCE_CHAIR_EMAIL\n";
	}
	if ($cc) {
		$headers .= "CC: $cc";
		if ($copy) {
			$headers .= ",$PROGRAM_CHAIR_EMAIL,$CONFERENCE_CHAIR_EMAIL";
		}
		$headers .= "\n";
	}
	$headers .= "BCC: $WEB_CHAIR_EMAIL\n";
	$headers .= "Subject: $subject\n";
	$headers .= "\n";
	return $headers;
}

sub content {
	my ($body) = @_;
	my $content = "";
	open(BODY, "$body") ||
		Audit::handleError("Cannot find temporary mail file: $body");
	while (<BODY>) {
		$content .= $_;
	}
	close(BODY);
	return $content;
}

1;