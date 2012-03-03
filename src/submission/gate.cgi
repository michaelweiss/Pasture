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
use Core::Submission;
use Core::Role;
use Core::Audit;
use Core::Access;
use Core::Debug;

our $q = new CGI;
our $timestamp = time();

our $config = Serialize::getConfig();
our $WEB_CHAIR = $config->{"web_chair"};
our $WEB_CHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $CONFERENCE_ID = $config->{"conference_id"};
our $CONFERENCE_WEBSITE = $config->{"conference_website"};
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
	
	unless ($config->{"making_changes"}) {
		# TODO: add hidden field or session parameter in cookie for the user's role
		# we might want to log in users as a shepherd when they sign up to become a shepherd
		print <<END;
	<p>Welcome to the <a href="$CONFERENCE_WEBSITE">$CONFERENCE</a> submission site.</p>

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
	} else {
		print <<END;
	<p>Welcome to the $CONFERENCE submission site.</p>

	<div id="box">
	<p>The site is being updated.</p>
	<p>Please check back in a few minutes.</p>
END
	}
		
	print <<END;
	</div>
END

	Format::createFooter();
}

# Handle menu request
sub handleMenu {	
	my $session = $q->param("session");
	my ($user, $role) = Session::getUserRole($session);	
	
	unless ($user && $role) {
		Assert::assertNotEmpty("user", "Need to enter a user name");
		Assert::assertNotEmpty("password", "Need to enter a password");
	
		# convert user name to lower case
		$user = lc($q->param("user"));
		my $password = $q->param("password");
			
		$role = checkPassword($user, $password);
		Assert::assertTrue($role, "User name and password do not match");
		
		$session = Session::create(Session::uniqueId(), $timestamp);
		Session::setUser($session, $user, $role);
	}
	
	my %profile = User::loadUser($user);
	my %contact = Contact::loadContact($user);
	
	Format::createHeader("Gate > Menu");
	
	print <<END;
<p>Dear $profile{"firstName"}, you are logged into the <a href="$CONFERENCE_WEBSITE">$CONFERENCE</a> submission site as <b>$role</b>.</p>

<div id="widebox">
<p>Here is what you can do:</p>
END

	if ($role eq "author") {
		authorMenu($session, $user);
	} elsif ($role eq "admin") {
		adminMenu($session, $user);
	} elsif ($role eq "pc") {
		pcMenu($session, $user);
	} elsif ($role eq "shepherd") {
		shepherdMenu($session, $user);
	} else {
		print "<p>Oops, nothing at all in this role.</p>";
	}

	print <<END;
<ul>
	<li>Change role to:
END
	
	my @roles = Role::getRoles($user, $CONFERENCE_ID);
	my $first = 1;
	foreach (@roles) {
		unless ($_ eq $role) {
			print " <a href=\"$baseUrl/$script?action=change_role&session=$session&role=$_\">$_</a>";	
		}
	}
	print "</li>\n";
	
	print <<END;
	<li>Change conference</li>
</ul>
</div>
END
		
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

# Handle change role request
sub handleChangeRole {
	my $session = $q->param("session");
	my ($user, $role) = Session::getUserRole($session);	
	
	# user can only switch into new role, if s/he has that role
	my $newRole = $q->param("role");
	Assert::assertTrue(Role::hasRole($user, $CONFERENCE_ID, $newRole),
		"No privileges to change to this role");
	Session::setUser($session, $user, $newRole);
	
	# redirect to handle menu request
	print $q->redirect(-uri => "$baseUrl/$script?action=menu&session=$session");
}

# Handle shepherd request
sub handleBecomeShepherd {
	my $session = $q->param("session");
	my ($user, $role) = Session::getUserRole($session);	
	
	Session::setUser($session, $user, "shepherd");
	
	# redirect to handle menu request
	print $q->redirect(-uri => $baseUrl . "/shepherd.cgi?session=$session");
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

	# convert user name to lower case
	$user = lc($::q->param("user"));
	$firstName = $::q->param("firstName");
	$lastName = $::q->param("lastName");
	$email = $::q->param("email");
	$affiliation = $::q->param("affiliation");
	$country = $::q->param("country");
	$password = $::q->param("password");
	$passwordConfirmed = $::q->param("passwordConfirmed");
	
	# TODO: check that user name is a single word, which may contain numbers
	
	# check whether this user name is taken already
	Assert::assertTrue(! Password::existsUser($user),
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
	if ($q->param("user")) {
		# if user parameter is supplied, generate email with token
		sendResetPasswordToken($q->param("user"));
		print $q->redirect(-uri => "$baseUrl/$script");
	} else {
		# otherwise, ask user to enter their user name
		# form will send user back to this handler
		Format::createHeader("Gate > Reset password", "", "js/validate.js");
		Format::startForm("post", "send_login");
		
		print <<END;
	<p>To reset your password please enter your user name. You will receive an email asking
	you to confirm. You can then enter your new password.</p>

	<div id="widebox">
	<table cellpadding="0" cellspacing="5">
		<tr>
			<td>Your user name:</td>
			<td width="10"></td>
			<td><input name="user" type="text"/></td>
		</tr>
	</table>
END

		Format::endForm("Reset password");
		
		print <<END;
	</div>
END

		Format::createFooter();
		
	}
}

# Handle requests to enter a new password
sub handlePassword {
	# DONE: check token that was sent to the user
	# other users can't pass
	$user = $q->param("user");
	Assert::assertTrue(Access::check($q->param("token"), $user),
		"Token does not match");
	
	$session = Session::create(Session::uniqueId(), $timestamp);
	Session::setUser($session, $user, "author");
	
	Format::createHeader("Gate > Password", "", "js/validate.js");

	Format::startForm("post", "change_password");
	Format::createHidden("session", $session);
	
	print <<END;
	<p>To change your password, enter and confirm your new password.</p>

	<div id="widebox">
	<table cellpadding="0" cellspacing="5">
		<tr>
			<td>Password:</td>
			<td width="10"></td>
			<td><input name="password" type="password"/></td>
		</tr><tr>
			<td>Confirm your password:</td>
			<td width="10"></td>
			<td><input name="passwordConfirmed" type="password"/></td>
		</tr>
	</table>
END

	Format::endForm("Change password");
	
	print <<END;
	</div>
END
	
	Format::createFooter();	
}

# Handle change password requests
sub handleChangePassword {
	my $session = $q->param("session");
	my ($user, $role) = Session::getUserRole($session);	
	Assert::assertTrue($user, 
		"You are not allowed to change this password");
	
	Assert::assertNotEmpty("password", "Need to enter a password");
	Assert::assertNotEmpty("passwordConfirmed", "Need to confirm your password");	
	
	my $password = $q->param("password");
	my $passwordConfirmed = $q->param("passwordConfirmed");
	
	# check whether the passwords match
	Assert::assertTrue($password eq $passwordConfirmed, 
		"Passwords do not match");
			
	# TODO: change logUserPassword to replace existing password	
	Password::logUserPassword($user, $password);
	
	# redirect to handle menu request
	print $q->redirect(-uri => "$baseUrl/$script");
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
	Format::createAction($SUBMISSION_OPEN, $baseUrl . "/submit.cgi?action=submit&session=$session&status=new", 
		"Submit a new paper", "submission is now closed");
	
	# DONE: need to rewrite getReferencesByAuthor to read from submission log
	my @references = Submission::lookupSubmissionsByAuthor($user);
	my %labels = Records::listCurrent();
	foreach $reference (@references) {
		my $record = Records::getRecord($labels{$reference}); 
		my $title = $record->param("title");
		print <<END;
		<li><a href="submit.cgi?action=submit&session=$session&status=existing&reference=$reference">Update your submission (#$reference): $title</a></li>
END
	}
	
	# ... or sign up as a shepherd
	Format::createAction($SHEPHERD_SUBMISSION_OPEN, "$baseUrl/$script?action=shepherd&session=$session", 
		"Become a shepherd", "we are not looking for shepherds at this time");
	
	print <<END;
	</ul>
END
}

sub pcMenu {
	my ($session, $user) = @_;
	print <<END;
	<ul>
		<li><a href="screen.cgi?action=submissions&session=$session">Screen initial submissions</a></li>
		<!-- li>Screen initial submissions (closed)</li> -->
		<li><a href="shepherd.cgi?action=shepherded_papers&user=$user&role=pc&session=$session">View all papers you are supervising as a PC member</a></li>
		<li><a href="shepherd.cgi?action=shepherded_papers&session=$session">View all papers being shepherded</a></li>
		<li><a href="shepherd.cgi?action=assignments&session=$session">Screen updated submissions</a></li>
	</ul>
END
}

sub adminMenu {
	my ($session, $user) = @_;
	print <<END;
	<ul>
		<li><a href="admin.cgi?action=view_submissions&session=$session">View submissions</a></li>
		<li><a href="admin.cgi?action=authors&session=$session">View authors</a></li>
		<li><a href="admin.cgi?action=pc&session=$session">View PC members</a></li>
		<li><a href="bids.cgi?session=$session">Assign shepherds (bids)</a></li>
		<li><a href="admin.cgi?action=shepherds&session=$session">View shepherds</a></li>
	<!--
		<li><a href="admin.cgi?action=participants&session=$session">View participants</a></li>
		<li><a href="admin.cgi?action=participants&session=$session&format=csv">View participants as CSV list</a></li>
	-->
	</ul>
END
}

sub shepherdMenu {
	my ($session, $user) = @_;
	print <<END;
	<ul>
END
	
	Format::createAction($SHEPHERD_SUBMISSION_OPEN, "$baseUrl/$script?action=shepherd&session=$session", 
		"Submit additional bids", "no more bids required");
	
	print <<END;
		<li><a href="shepherd.cgi?action=shepherded_papers&user=$user&role=pc&session=$session">View all papers you are shepherding</a></li>
		<li><a href="shepherd.cgi?action=assignments&session=$session">Screen updated submissions</a></li>
	</ul>
END
}
	
# Emails

sub sendResetPasswordToken {
	my ($user) = @_;
	
	my %contact = Contact::loadContact($user);
	my $email = $contact{"email"};
	
	my %user = User::loadUser($user);
	my $name = $user{"firstName"} . $user{"lastName"};
	my $firstName = $user{"firstName"};
	
	# create temporary file
	my ($sanitizedName) = $name	=~ m/([\w\s-]*)/;	
	my $tmpFileName = Email::tmpFileName($timestamp, $sanitizedName);

	my $token = uri_escape(Access::token($user));
	open (MAIL, ">$tmpFileName") || 
		Audit::handleError("Cannot create temporary file: $tmpFileName");
	print MAIL <<END;
Dear $firstName,

A request to reset your password has been received. To reset your password, 
please click on the following URL: 

$baseUrl/$script?action=password&user=$user&token=$token

$WEB_CHAIR
$CONFERENCE Web Chair
END
	close (MAIL);
	my $status = Email::send($email, "",
		"[$CONFERENCE] Request to reset password", 
		$tmpFileName, 0);
	return $status;
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
} elsif ($action eq "change_role") {
	handleChangeRole();
} elsif ($action eq "shepherd") {
	handleBecomeShepherd();
} elsif ($action eq "send_login") {
	handleSendLogin();
} elsif ($action eq "password") {
	handlePassword();
} elsif ($action eq "change_password") {
	handleChangePassword();
} else {
	Audit::handleError("No such action");
}