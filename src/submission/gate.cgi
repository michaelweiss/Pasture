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
use Core::User;
use Core::Contact;
use Core::Audit;
use Core::Debug;

our $q = new CGI;
our $timestamp = time();

our $config = Serialize::getConfig();
our $WEB_CHAIR = $config->{"web_chair"};
our $WEB_CHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $SUBMISSION_OPEN = $config->{"submission_open"};
our $SHEPHERD_SUBMISSION_OPEN = $config->{"shepherd_submission_open"};
our $baseUrl = $config->{"url"};

my $script = "gate.cgi";

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
	Format::createHeader("Gate > Sign in", "", "js/validate.js");
	Format::startForm("post", "menu");
	
	# TODO: add hidden field or session parameter in cookie for the user's role
	# we might want to log in users as a shepherd when they sign up to become a shepherd
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
		"If you forgot your password, <a href=\"$baseUrl/$script?action=send_login\">click here</a>.");
		
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
	
	# fake getting roles from user profile
	my $roles;
	$roles{"author"} = 1;

	Format::createHeader("Gate > Menu");
	
	print <<END;
<p>Here is what you can do:</p>
END

	if ($roles{"author"}) {
		authorMenu($session, $user);
	}
		
	Format::createFooter();
}

# Handle sign up request
sub handleSignUp {
	Format::createHeader("Gate > Sign up", "", "js/validate.js");
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
			<td>Affiliation (*):</td>
			<td width="10"></td>
			<td><input name="affiliation" type="text" size="40"/></td>
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
	my $user, $firstName, $lastName;
	my $email, $affiliation, $country;
	my $password, $passwordConfirmed; 
	
	Assert::assertNotEmpty("user", "Need to enter a user name");
	Assert::assertNotEmpty("firstName", "Need to enter your first name");
	Assert::assertNotEmpty("lastName", "Need to enter your last name");
	Assert::assertNotEmpty("email", "Need to enter your email");
	Assert::assertNotEmpty("affiliation", "Need to enter your affiliation");
	Assert::assertNotEmpty("country", "Need to enter your country");
	Assert::assertNotEmpty("password", "Need to enter a password");
	Assert::assertNotEmpty("passwordConfirmed", "Need to confirm your password");

	$user = $::q->param("user");
	$firstName = $::q->param("firstName");
	$lastName = $::q->param("lastName");
	$email = $::q->param("email");
	$affiliation = $::q->param("affiliation");
	$country = $::q->param("country");
	$password = $::q->param("password");
	$passwordConfirmed = $::q->param("passwordConfirmed");
	
	# TODO: check that user name is a single word, which may contain numbers
	
	# check whether this user name is taken already
	Assert::assertTrue(! Password::retrieveUserPassword($user),
		"This user name already exists. Please select a different name");
		
	# check whether the passwords match
	Assert::assertTrue($password eq $passwordConfirmed, 
		"Passwords do not match");
		
	Password::logUserPassword($user, $password);
	User::saveUser($user, $firstName, $lastName, $affiliation, $country);
	Contact::saveContact($user, $email);

	# default role is author
	my $role = "author";
	
	Format::createHeader("Gate > Profile", "", "js/validate.js");
	
	print <<END;
<p>Hello, $firstName $lastName. Your account has been created.</p>
<p>You can now <a href=\"$baseUrl/$script?action=sign_in\">log into the submission system</a>.</p>
END
	
	Format::createFooter();
}

# Handle send login requests
sub handleSendLogin {
	Format::createHeader("Gate > Sign up", "", "js/validate.js");
	print <<END;
<p>Oops, this feature has not been implemented yet. If you don't have an account, 
you need to <a href=\"$baseUrl/$script?action=sign_up\">sign up for one</a>.</p>
END
	Format::createFooter();
}

# Check password
sub checkPassword {
	my ($user, $password) = @_;
	# if user and password are correct, allow the user to access the system
	# default user role is "author"  
	# TODO: should remember the last role the user was logged in as
	if (Password::checkUserPassword($user, $password)) {
		return "author";
	}
}

# Menus

sub authorMenu {
	my ($session, $user) = @_;
	print <<END;
	<ul>
END

	# user can submit a paper ...
	Format::createAction($SUBMISSION_OPEN, $baseUrl . "/submit.cgi?action=submit&status=new", 
		"Submit a paper", "submission is now closed");
	
	# TODO: need to rewrite getReferencesByAuthor to read from submission log
	my @references = (); #Password::getReferencesByAuthor($user);
	my %labels = Records::listCurrent();
	foreach $reference (@references) {
		my $record = Records::getRecord($labels{$reference}); 
		my $title = $record->param("title");
		print <<END;
		<li><a href="submit.cgi?action=submit&session=$session&status=existing&reference=$reference">Update your submission (#$reference): $title</a></li>
END
	}
	print <<END;
	</ul>
END
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
} elsif ($action eq "send_login") {
	handleSendLogin();
} else {
	Audit::handleError("No such action");
}