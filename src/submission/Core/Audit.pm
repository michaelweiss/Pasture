package Audit;

use CGI;
use URI::Escape ('uri_escape');

use lib '.';
use Core::Format;

my $LOCK = 2;
my $UNLOCK = 8;

sub trace {
	my ($action) = @_;
	my $remote_host = $::q->remote_host();
	open(LOG, ">>data/log.dat") ||
		handleError("Could not log action: $remote_host, $::timestamp, $action");
	flock(LOG, $LOCK);
	print LOG "$remote_host, $::timestamp, $::script.$action\n";
	flock(LOG, $UNLOCK);
	close(LOG);
}

sub addToErrorLog {
	my ($error) = @_;
	unless ($q) { return; }
	my $action = $::q->param("action") || "unknown";
	my $remote_host = $::q->remote_host();
	my $user_agent = $::q->user_agent();
	my $email = $::q->param("email") || "NA";
	open(LOG, ">>data/errors.dat") ||
		return;		# just stop here, can't log that we cannot log
	flock(LOG, $LOCK);
	print LOG "$remote_host|$::timestamp|$::script.$action|$user_agent|$email|$error\n";
	flock(LOG, $UNLOCK);
	close(LOG);	
}

sub handleError {
	my ($error, $no_framecheck, $url) = @_;
	# DONE: log errors with error details
	addToErrorLog($error);
	my $WEBCHAIR_EMAIL = $::config->{"web_chair_email"};
	Format::createHeader("Error", "Error", "", $no_framecheck);
	my $uriEncodedError = uri_escape($error);
	my $goBackAction = "history.go(-1)";
	if ($url) {
		$goBackAction = "document.location='$url'";
	}
	print <<END;
<p><b style="color:red">$error</b></p>
<p><input type=button value="Back to form" onClick="$goBackAction"/></p>
END
	Format::createFooter();
	exit(0);
}

sub handleUnexpectedError {
	my ($error) = @_;
	addToErrorLog($error);
	my $q = new CGI;
	print $q->start_html(-title => "Unexpected error"),
		$q->h1("Unexpected error:"),
		$q->pre($error),
		$q->p("Please report the error to the conference web chair <a href=\"mailto:$::WEBCHAIR_EMAIL\">$::WEBCHAIR_EMAIL</a>."),
		$q->end_html;
}
