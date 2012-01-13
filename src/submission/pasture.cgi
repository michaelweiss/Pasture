#!/usr/bin/perl -wT
use CGI;
use CGI::Carp qw( fatalsToBrowser );

use URI::Escape ('uri_escape');

use lib '.';
use Core::Assert;
use Core::Format;
use Core::Upload;
use Core::Serialize;
use Core::Serialize::Records;
use Core::Email;
use Core::Session;
use Core::Password;
use Core::Access;
use Core::Shepherd;
use Core::Review;
use Core::Audit;

my $LOCK = 2;
my $UNLOCK = 8;

our $q = new CGI;
our $timestamp = time();

our $config = Serialize::getConfig();
our $WEB_CHAIR = $config->{"web_chair"};
our $WEB_CHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $baseUrl = $config->{"url"};

my $script = "pasture.cgi";

BEGIN {
	sub handleInternalError {
		my $error = shift;
		# DONE: log errors with error details
		# Removed because of potential loop created by this
		# addToErrorLog($error);
		my $q = new CGI;
		print $q->start_html(-title => "Error"),
			$q->h1("Internal error:"),
			$q->pre($error),
			$q->p("If this is not what you expected, please email the web chair at <a href=\"mailto:$WEB_CHAIR_EMAIL\">$WEB_CHAIR_EMAIL</a>."),
			$q->end_html;
	}
	CGI::Carp::set_message( \&handleInternalError );
}

# Handlers

sub handleSignIn {
	Format::createHeader("Pasture > Sign in", "", "js/validate.js");
	Format::startForm("post", "menu");
	
	print <<END;
	<p>Welcome to the $CONFERENCE submission site.</p>
	<ul>
END

	print <<END;
	</ul>

	<div id="box">
	<p>Please sign in using your account.</p>
	<table cellpadding="0" cellspacing="5">
		<tr>
			<td>My user name is:</td>
			<td width="10"></td>
			<td><input name="user" type="text"/></td>
		</tr><tr>
			<td>My password is:</td>
			<td width="10"></td>
			<td><input name="password" type="password"/></td>
		</tr>
	</table>
END

	Format::endForm("Sign in");

	Format::createFreetext(
		"If you do not have an account, please <a href=\"$baseUrl/$script?action=sign_up\">sign up for one</a>.");
	Format::createFreetext(
		"If you forgot your password, <a href=\"$baseUrl/$script?action=send_login\">retrieve it here</a>.");
		
	print <<END;
	</div>
END

	Format::createFooter();
}

# Main dispatcher

my $action = $q->param("action") || "sign_in";
Format::sanitizeInput();
Audit::trace($action);
if ($action eq "sign_in") {
	handleSignIn();
} else {
	Audit::handleError("No such action");
}