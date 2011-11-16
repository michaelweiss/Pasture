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

my $LOCK = 2;
my $UNLOCK = 8;

our $q = new CGI;
our $timestamp = time();

our $config = Serialize::getConfig();
our $PROGRAM_CHAIR = $config->{"program_chair"};
our $PROGRAM_CHAIR_EMAIL = $config->{"program_chair_email"};
our $CONFERENCE_CHAIR = $config->{"conference_chair"};
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
	
	print <<END;
	<p>Welcome to the submission system for $CONFERENCE. </p>
	<ul>
END

	# user can submit a paper ...
	Format::createAction($SUBMISSION_OPEN, $baseUrl . "/submit.cgi?action=submit&status=new", 
		"Submit a paper", "submission is now closed");
	
	# ... or sign up as a shepherd
	Format::createAction($SHEPHERD_SUBMISSION_OPEN, $baseUrl . "/shepherd.cgi", 
		"Become a shepherd", "we are not looking for shepherds at this time");
		
	print <<END;
	</ul>

	<p>If you have an account, please enter your email and password. 
	<b>Note:</b> if you are an author and want to update a submission, all of your submissions are linked to your email. 
	Please use the password we sent you.</p>
	
	<table cellpadding="0" cellspacing="5">
		<tr>
			<td>My email address is:</td>
			<td width="10"></td>
			<td><input name="user" type="text"/></td>
		</tr><tr>
			<td>My password is:</td>
			<td width="10"></td>
			<td><input name="password" type="password"/></td>
		</tr>
	</table>
END

	# DONE: ask for password, and allow author to select submission
	Format::endForm("Sign in");
	Format::createFreetext(
		"<a href=\"$baseUrl/$script?action=send_login\">Forgot your password? Click here</a>");
	Format::createFooter();
}

sub handleMenu {
	my $user, $password;
	my $author, $role;
	
	$user = $q->param("user");
	$password = $q->param("password");
	
	$author = checkAuthorPassword($user, $password); 
	$reviewer = checkReviewerPassword($user, $password);
	
	Assert::assertTrue($author || $reviewer,
		"Please check that you entered the correct user name and password");
		
	# TODO: merge the two authentication schemes	
	# reviewer role includes: pc, shepherd, and admin
	$role = $reviewer ? $reviewer : $author;
	
	my $session = Session::create(Session::uniqueId(), $timestamp);
	Session::setUser($session, $user, $role);
	
	# at this point $reviewer tells me the reviewer role, and $author tells me whether this user has submitted any papers
	
	Format::createHeader("Gate > Menu");

	if ($author) {
		authorMenu($session, $user);
	}
	if ($role eq "pc" || $role eq "admin") {
		pcMenu($session, $user);
	}
	if ($role eq "shepherd" || $role eq "pc" || $role eq "admin") {
		shepherdMenu($session, $user);
	}
	if ($role eq "admin") {
		adminMenu($session, $user);
	}
	
#	print <<END;
#	<ul>
#		<li><a href="$script?action=selection&session=$session&choice=a">Do A</a></li>
#		<li><a href="$script?action=selection&session=$session&choice=b">Do B</a></li>
#		<li><a href="$script?action=selection&session=$session&choice=c">Do C</a></li>
#		<li><a href="$script?action=selection&session=$session&choice=d">Do D</a></li>
#	</ul>
#END
	
	Format::createFooter();
}

sub authorMenu {
	my ($session, $user) = @_;
	print <<END;
	<h2>Author</h2>
	<ul>
END
	my @references = Password::getReferencesByAuthor($user);
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

sub pcMenu {
	my ($session, $user) = @_;
	print "<h2>Programme Committee</h2>";
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

sub shepherdMenu {
	my ($session, $user) = @_;
	print "<h2>Shepherd</h2>";
	print <<END;
	<ul>
		<!--
		<li><a href="shepherd.cgi?action=submissions&session=$session">Submit additional bids</a></li>
		-->
		<li>Submit additional bids</li>
		<li><a href="shepherd.cgi?action=shepherded_papers&user=$user&role=shepherd&session=$session">View all papers you are shepherding</a></li>
		<li><a href="shepherd.cgi?action=assignments&session=$session">Screen updated submissions</a></li>
	</ul>
END
}

sub adminMenu {
	my ($session, $user) = @_;
	print "<h2>Admin</h2>";
	print <<END;
	<ul>
		<li><a href="admin.cgi?action=view_submissions&session=$session">View submissions</a></li>
		<li><a href="admin.cgi?action=authors&session=$session">View authors</a></li>
		<li><a href="admin.cgi?action=pc&session=$session">View PC members</a></li>
		<li><a href="admin.cgi?action=shepherds&session=$session">View shepherds</a></li>
		<li><a href="admin.cgi?action=participants&session=$session">View participants</a></li>
		<li><a href="admin.cgi?action=participants&session=$session&format=csv">View participants as CSV list</a></li>
	</ul>
END
}

sub handleSelection {
	# DONE: check that this is a valid session id
	Assert::assertTrue(Session::check($q->param("session")), 
		"Session expired. Please sign in first.");
	Assert::assertTrue($q->param("choice"),
		"No choice provided.");
		
	Format::createHeader("Gate > Menu");
	my $choice = $q->param("choice");
	print <<END;
	<p>You chose action $choice.</p>
END
	Format::createFooter();
}

sub handleSendLogin {
	unless ($q->param("email")) {
		Format::createHeader("Password help", "", "");
		Format::startForm("post", "send_login");
		Format::createFreetext("To retrieve your password, please provide the email address you use to log in.");
		Format::createTextWithTitle("Enter your email address", 
			"My email address is", "email", 40);
		Format::createFreetext("Once you submit, your password will be sent to this email address.");
		Format::endForm("Send password");
		Format::createFooter();
	} else {
		my $status = sendPasswordForEmail($q->param("email"));
		if ($config->{"debug"}) {
			Format::createHeader("Password help", "", "");
			print "Email: <pre>$status</pre>";
			Format::createFooter();
		} else {
			handleSignIn();
			# Format::createHeader("Password help", "", "");
			# print "$status";
			# Format::createFooter();
		}

	}
}

sub handleError {
	my ($error) = @_;
	# DONE: log errors with error details
	addToErrorLog($error);
	Format::createHeader("Error");
	my $uriEncodedError = uri_escape($error);
	print <<END;
<p><b style="color:red">$error</b></p>
<p><input type=button value="Back to form" onClick="history.go(-1)"/></p>
END
	Format::createFooter();
	exit(0);
}

# Subservient functions

sub checkPassword {
	my ($user, $password) = @_;
	if (checkAdminPassword($user, $password)) {
		return "admin";
	}
	return "";
}

sub checkAuthorPassword {
	my ($user, $password) = @_;
	if (Password::checkPassword(0, $user, $password)) {
		return "author";
	}
	return "";
}

sub checkAdminPassword {
	my ($user, $password) = @_;
	if ($user eq "europlop") {
		if ($password eq $config->{"admin_password"}) {
			return "admin";
		}
	}
	return "";
}

sub checkReviewerPassword {
	my ($user, $password) = @_;
	return Review::authenticate($user, $password);
}

# Audit

sub trace {
	my ($action) = @_;
	my $remote_host = $q->remote_host();
	open(LOG, ">>data/log.dat") ||
		handleError("Could not log action: $remote_host, $timestamp, $action");
	flock(LOG, $LOCK);
	print LOG "$remote_host, $timestamp, submit.$action\n";
	flock(LOG, $UNLOCK);
	close(LOG);
}

sub addToErrorLog {
	my ($error) = @_;
	if ($q) {
		my $action = $q->param("action") || "unknown";
		my $remote_host = $q->remote_host();
		my $user_agent = $q->user_agent();
		my $email = $q->param("email") || "NA";
		open(LOG, ">>data/errors.dat") ||
			return;
		flock(LOG, $LOCK);
		print LOG "$remote_host|$timestamp|submit.$action|$user_agent|$email|$error\n";
		flock(LOG, $UNLOCK);
		close(LOG);	
	}
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

# Mails

# Recover the password for a submission. Send to the contact author's email.
#
# $reference is the reference number of the submission
sub sendPasswordForEmail {
	my ($email) = @_;
	my $password, $name;
	
	$password = Password::retrievePassword($email);
	if ($password) {
		# get name from submission record
		my @references = Password::getReferencesByAuthor($email);
		my %labels = Records::listCurrent();
		my $record = Records::getRecord($labels{$references[0]}); 
		$name = $record->param("contact_name");
	} else {
		# get name for reviewer list (includes pc, shepherds, and admin)
		$password = Review::getPassword($email);
		$name = Review::getReviewerName($email);
	}
	
	my ($sanitizedName) = $name	=~ m/([\w\s-]*)/;	
	my $tmpFileName = Email::tmpFileName($timestamp, $sanitizedName);
	my ($firstName) = $sanitizedName =~ /^(\w+)/;	
	
	open (MAIL, ">$tmpFileName") || 
		Audit::handleError("Cannot create temporary file");
	if ($password) {
	print MAIL <<END;
Dear $firstName,

your password is: $password.

$WEB_CHAIR
$CONFERENCE Web Chair
END
	} else {
	print MAIL <<END;
We tried very hard to retrieve your password, but there is none for the email address you provided. Please check if you used the right email address.

$WEB_CHAIR
$CONFERENCE Web Chair
END
	}
	close (MAIL);
	my $status = Email::send($email, "",
		"[$CONFERENCE] Recovered password", 
		$tmpFileName, 0);
	return $status;
}

# Recover the password for a submission. Send to the contact author's email.
#
# $reference is the reference number of the submission
sub sendPasswordForReference {
	my ($reference) = @_;
	
	# get record metadata
	my %labels = Records::listCurrent();
	my $record = Records::getRecord($labels{$reference}); 
	my $name = $record->param("contact_name");
	my $email = $record->param("contact_email");
	
	# create temporary file
	my ($sanitizedName) = $name	=~ m/([\w\s-]*)/;	
	my $tmpFileName = Email::tmpFileName($timestamp, $sanitizedName);
	my ($firstName) = $sanitizedName =~ /^(\w+)/;

	my $password = Password::retrievePassword($reference);
	open (MAIL, ">$tmpFileName") || 
		Audit::handleError("Cannot create temporary file: $tmpFileName");
	print MAIL <<END;
Dear $firstName,

your password for submission $reference is: $password.

$WEB_CHAIR
$CONFERENCE Web Chair
END
	close (MAIL);
	my $status = Email::send($email, "",
		"[$CONFERENCE] Recovered password for submission $reference", 
		$tmpFileName, 0);
	return $status;
}

# Main dispatcher

my $action = $q->param("action") || "sign_in";
Format::sanitizeInput();
trace($action);
if ($action eq "sign_in") {
	handleSignIn();
} elsif ($action eq "menu") {
	handleMenu();
} elsif ($action eq "selection") {
	handleSelection();
} elsif ($action eq "test") {
	Format::createHeader("Test");
	printEnv();
	Format::createFooter();
} elsif ($action eq "send_login") {
	handleSendLogin();
} else {
	handleError("No such action");
}