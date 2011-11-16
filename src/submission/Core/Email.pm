package Email;

use LWP;
use URI;
use URI::Escape ('uri_escape');
use Core::Audit;

# Setting debug results in the email printed on the screen, rather than
# being sent. Helpful for debugging. Turn off for deployment.
#
# TODO: should set debug flag in main script (but sending email already takes
# time, so this is not a high priority task)
our $config = Serialize::getConfig();
our $debug = $config->{"debug"};

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
# TODO: This is a workaround since sending email from Perl is not configured
# on the hillside site, but PHP mail works already.
sub send {
	my ($email, $cc, $subject, $body, $copy) = @_;
	my ($page, $php);
	
	# set copy flag to send email with copy to chairs, or without
	if ($copy) {
		$php = "$::baseUrl/mail.php";
	} else {
		$php = "$::baseUrl/mail_no_cc.php";
	}
	unless ($debug) {			
		my $browser = LWP::UserAgent->new();
		my $url = URI->new($php);
		$page = $browser->post($url, 
			[
				email => $email,
				cc => $cc,
				subject => $subject,
				body => $body
			]
		)->content();	
	} else {	
		# don't send the actual email
		# $page .= "<hr/>";
		$page = "To: $email\n";
		if ($cc) {
			$page .= "CC: $cc\n";
		}
		$page .= "Subject: $subject\n";
		$page .= "\n";
		open (BODY, "$body") ||
			Audit::handleError("Cannot find temporary mail file: $body");
		while (<BODY>) {
			$page .= $_;
		}
		close (BODY);	
	}
	return $page;
}

1;