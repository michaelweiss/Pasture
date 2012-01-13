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

# Handle menu request
sub handleMenu {
	my $user, $password;
	my $role;
	
	Assert::assertNotEmpty("user", "Need to enter a user name");
	Assert::assertNotEmpty("password", "Need to enter a password");

	$user = $q->param("user");
	$password = $q->param("password");
		
	$role = checkPassword($user, $password);
	Assert::assertTrue($role, "User name and password do not match");
	
	my $session = Session::create(Session::uniqueId(), $timestamp);
	Session::setUser($session, $user, $role);
	
	Format::createHeader("Pasture > Menu");
	
	print <<END;
<p>You have logged in successfully.</p>
END
	
	Format::createFooter();
}

# Handle sign up request
sub handleSignUp {
	Format::createHeader("Pasture > Sign up", "", "js/validate.js");
	Format::startForm("post", "profile");
	
	print <<END;
	<p>To sign up for an account, please fill in your profile.</p>

	<div id="widebox">
	<table cellpadding="0" cellspacing="5">
		<tr>
			<td>Select a user name (*):</td>
			<td width="10"></td>
			<td><input name="user" type="text"/></td>
		</tr><tr>
			<td></td>
			<td width="10"></td>
			<td><em>User names must be in one word, but can contain numbers</em></td>
		</tr><tr>
			<td>&nbsp;</td>
			<td width="10"></td>
			<td></td>
		</tr><tr>
			<td>First name (*):</td>
			<td width="10"></td>
			<td><input name="firstName" type="text" size="40"/></td>
		</tr><tr>
			<td>Last name (*):</td>
			<td width="10"></td>
			<td><input name="lastName" type="text" size="40"/></td>
		</tr><tr>
			<td>Email (*):</td>
			<td width="10"></td>
			<td><input name="email" type="text" size="40"/></td>
		</tr><tr>
			<td>Organization (*):</td>
			<td width="10"></td>
			<td><input name="organization" type="text" size="40"/></td>
		</tr><tr>
			<td>Country (*):</td>
			<td width="10"></td>
			<td><input name="country" type="text"/></td>
		</tr><tr>
			<td>Password (*):</td>
			<td width="10"></td>
			<td><input name="password" type="password"/></td>
		</tr><tr>
			<td>Confirm your password (*):</td>
			<td width="10"></td>
			<td><input name="passwordConfirmed" type="password"/></td>
		</tr>
	</table>
END

	Format::endForm("Sign up");
		
	print <<END;
	</div>
END

	Format::createFooter();
}

# Handle profile request
sub handleProfile {
	my $user, $password;
	
	Assert::assertNotEmpty("user", "Need to enter a user name");
	Assert::assertNotEmpty("firstName", "Need to enter your first name");
	Assert::assertNotEmpty("lastName", "Need to enter your last name");
	Assert::assertNotEmpty("email", "Need to enter your email");
	Assert::assertNotEmpty("organization", "Need to enter your organization");
	Assert::assertNotEmpty("country", "Need to enter your country");
	Assert::assertNotEmpty("password", "Need to enter a password");
	Assert::assertNotEmpty("passwordConfirmed", "Need to confirm your password");

	$user = $::q->param("user");
	$firstName = $::q->param("firstName");
	$lastName = $::q->param("lastName");
	$email = $::q->param("email");
	$organization = $::q->param("organization");
	$country = $::q->param("country");
	$password = $::q->param("password");
	$passwordConfirmed = $::q->param("passwordConfirmed");
	
	Assert::assertTrue($password eq $passwordConfirmed, "Passwords do not match");

	Format::createHeader("Pasture > Profile", "", "js/validate.js");
	
	print <<END;
<p>Hello, $firstName $lastName. Thank you for creating your account "$user".</p>
END
	
	Format::createFooter();
}

# Check password
sub checkPassword {
	my ($user, $password) = @_;
	if (checkAdminPassword($user, $password)) {
		return "admin";
	}
	return "";
}

sub checkAdminPassword {
	my ($user, $password) = @_;
	if ($user eq $config->{"admin_user"}) {
		if ($password eq $config->{"admin_password"}) {
			return "admin";
		}
	}
	return "";
}

# Debug 

sub dumpParameters {
	print "<hr/>\n";
	print "<ul>\n";
	foreach $name ($q->param()) {
		my $value = $q->param($name);
		print "<li>$name: $value</li>\n";
	}
	print "</ul>\n";
	print "<hr/>\n";
}

sub dumpRecord {
	my ($record) = @_;
	print "<hr/>\n";
	print "<ul>\n";
	foreach $name (keys %$record) {
		my $value = $record->{$name};
		print "<li>$name: $value</li>\n";
	}
	print "</ul>\n";
	print "<hr/>\n";
}

sub printEnv {
	print "<hr/>\n";
	print "<tt>\n"; 
	foreach $key (sort keys(%ENV)) { 
		print "<li> $key = $ENV{$key}"; 
   	} 
	print "<tt/><hr/>\n";
}
	
# Main dispatcher

my $action = $q->param("action") || "sign_in";
Format::sanitizeInput();
Audit::trace($action);
if ($action eq "sign_in") {
	handleSignIn();
} elsif ($action eq "menu") {
	handleMenu();
} elsif ($action eq "sign_up") {
	handleSignUp();
} elsif ($action eq "profile") {
	handleProfile();
} else {
	Audit::handleError("No such action");
}