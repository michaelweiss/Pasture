#!/usr/bin/perl -wT
use CGI;
use CGI::Carp qw( fatalsToBrowser );

use URI::Escape ('uri_escape');

use lib '.';
use Core::Assert;
use Core::Audit;
use Core::Format;
use Core::Upload;
use Core::Serialize;
use Core::Serialize::Records;
use Core::Email2;
use Core::Session;
use Core::Password;
use Core::Access;
use Core::Shepherd;
use Core::Review;
use Core::User;
use Core::Contact;
use Core::Submission;
use Core::Role;

my $LOCK = 2;
my $UNLOCK = 8;

our $q = new CGI;
our $timestamp = time();

our $config = Serialize::getConfig();
our $PROGRAM_CHAIR = $config->{"program_chair"};
our $PROGRAM_CHAIR_EMAIL = $config->{"program_chair_email"};
our $PROGRAM_CHAIR_TITLE = $config->{"program_chair_title"};
our $CONFERENCE_CHAIR = $config->{"conference_chair"};
our $WEB_CHAIR = $config->{"web_chair"};
our $WEB_CHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $CONFERENCE_ID = $config->{"conference_id"};
our $SUBMISSION_OPEN = $config->{"submission_open"};
our $MULTI_TRACK = $config->{"multi_track"};
our $NUMBER_OF_TRACKS = $config->{"focus_group_track"};
our $baseUrl = $config->{"url"};

my $script = "submit.cgi";

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
	Format::createHeader("Submit > Sign in", "", "js/validate.js");
	# DONE: client-side validation of input
	
	my $disabled = $config->{"shepherd_submission_open"} || 
		$config->{"shepherding_open"} ? "" : "disabled";

	# TODO: disabled PC login for now
	# TODO: make participant login configurable

	print <<END;
<p>For the initial submission of your paper, create a new submission. When you submit the initial version paper of your paper, you will be given a reference number. Enter it to submit an updated version of your paper.</p> 
END
	Format::startForm("post", "submit", "return checkSignInForm(this)");
	Format::createHidden("session", Session::create(Session::uniqueId(), $timestamp));
	my $open = $SUBMISSION_OPEN ? "" : "disabled";
	my $message = $SUBMISSION_OPEN ? "" : "&nbsp; <font color=\"red\">(SUBMISSION IS NOW CLOSED)</font>";
	print <<END;
<table cellspacing="0" cellpadding="0">
	<tr height="5"></tr>
	<tr>
		<td valign="top"><input name="status" type="radio" value="new" $open/></td>
		<td width="5"></td>
		<td valign="top">
			<table cellpadding="0" cellspacing="0">
				<tr>
					<td>New submission $message</td>
				</tr>
			</table>
		</td>
	</tr>
	<tr>
		<td height="5"></td>
	</tr>
	<tr>
		<td valign="top"><input name="status" type="radio" value = "existing" checked/></td>
		<td width="5"></td>
		<td valign="top">
			<table cellpadding="0" cellspacing="0">
				<tr>
					<td>No, my reference number is:</td>
					<td width="10"></td>
					<td><input name="reference" type="text"/></td>
				</tr>
				<tr>
					<td height="5"></td>
				</tr>
				<tr>
					<td>and my password is:</td>
					<td width="10"></td>
					<td><input name="password" type="password"/></td>
				</tr>
			</table>
		</td>
	</tr>
</table>
END
	# DONE: ask for password, and allow author to select submission
	Format::endForm("Sign in");
	Format::createFreetext(
		"<a href=\"$baseUrl/$script?action=send_author_login\">Forgot your password? Click here</a>");
	Format::createFooter();
}

sub handleSubmit {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	my ($user, $role) = $sessionInfo =~ /:(.+?):(.+)/;

	my $reference;
	if ($q->param("status") eq "new") {
		unless ($session) {
			$session = Session::create(Session::uniqueId(), $timestamp);
		}
	} elsif ($q->param("status") eq "existing") {
		Assert::assertEquals("reference", "\\d+", "No valid reference number");
		$reference = $q->param("reference");
		# DONE: enable, once we use passwords
		unless ($user) {
			# password only needed if user not already authenticated
			Assert::assertNotEmpty("password", "Please enter your password.");
		}
	}

	# DONE: check that this is a valid session id
	Assert::assertTrue($session ne "", "Need to sign in first");
	Assert::assertTrue(Session::check($session), 
		"Session expired. Please sign in first.");
		
	# Only registered authors can submit a paper
	Assert::assertTrue($user, "Need to create an account first");
		
	my %profile = User::loadUser($user);
	my %contact = Contact::loadContact($user);	

	# existing data
	my $q_saved = new CGI();
	
	if ($q->param("status") eq "new") {
		$q_saved->param("contact_name" => $profile{"firstName"} . " " . $profile{"lastName"});
		$q_saved->param("contact_email" => $contact{"email"});
	}
	
	# DONE: for an existing paper check reference against email and password
	if ($reference) {
		if ($user) {
			# if user already authenticated, check if he/she is the author
			# of the submission $reference
			my @references = Submission::lookupSubmissionsByAuthor($user);
			my $found = 0;
			foreach $r (@references) {
				if ($r == $reference) {
					$found = 1;
				}
			}
			unless ($found) {
				handleError("No such reference for this author");
			}
		} else {
			# if user is not already authenticated, check supplied password
			unless (Password::checkPassword($reference, 0, $q->param("password"))) {
			 	handleError("Please check that you entered the correct reference number and password");
			}
		}
		$q_saved = Serialize::loadState($reference);
		Format::createHeader("Submit > Edit", "", "js/validate.js");
		print <<END;
	<p>Dear $profile{"firstName"}, to update your submission (#$reference) make changes below.</p>
END
	} else {
		Format::createHeader("Submit > Edit", "", "js/validate.js");
		print <<END;
	<p>Dear $profile{"firstName"}, enter your initial submission for $CONFERENCE below.</p>
END
	}
		 
	print <<END;	
	<div id="widebox">
END
	
	# TODO: client-side validation of input
	Format::startMultiPartForm("post", "submit_confirmed", "return checkSubmitForm(this)");
	Format::createHidden("session", $session);
	
	# information to keep for the submission record
	if ($reference) {
		Format::createHidden("reference", $reference);
	}
	
	# TODO: somewhat redundant, as user will also be in session data
	Format::createHidden("user", $user);
	
	Format::createTextWithTitle("Title (*)", 
		"Title of your submission", "title", 60, $q_saved->param("title"));
	Format::createTextAreaWithTitle("Authors (*)", 
		"Enter each author (first and last name) on a separate line", "authors", 50, 4,
		$q_saved->param("authors"));
	Format::createTextWithTitle("Contact author (*)", 
		"Name (first and last name)", "contact_name", 60, $q_saved->param("contact_name"));
	# DONE: carry forward email from sign-in form
	Format::createTextWithTitle("", 
		"Email address", "contact_email", 60, 
			$q_saved->param("contact_email"));
			
	# DONE: preselected track 1 (general)
	# NOTE: added to avoid annoying error when track was left unselected (but should
	# really be validating track selection on client)
	# TODO: make number of tracks and track rerpresenting focus groups
	# configurable in config.dat

	my @tracks;
	for (my $i = 1; $i <= $NUMBER_OF_TRACKS; $i++) {
		push(@tracks, $i);
		push(@tracks, $config->{"track_" . $i});
	}
	Format::createRadioButtonsWithTitle("Track (*)", 
		"Desired track", "track", @tracks,
		$q_saved->param("track") || "1");
		
	Format::createTextAreaWithTitle("Abstract (*)", 
		"Enter your abstract here", "abstract", 50, 8,
		$q_saved->param("abstract"));
	Format::createTextWithTitle("Keywords", 
		"Enter keywords (separated by commas) that describe your submission", "tags", 60, $q_saved->param("tags"));
	Format::createFileUpload("File upload (*)",						# no default
		"Upload your file in PDF or Word format", "paper", 40);
	if ($q->param("status") eq "existing") {
		Format::createTextWithTitle("Reason for update (*)",		# no default
			"Provide a reason for the update (required)", "reason", 60);
	}
	Format::createTextAreaWithTitle("Comments", 				# no default
		"If you have additional comments for the program committee, enter them here", "comments", 50, 4);
	Format::createFreetext("Once you submit, you will receive a confirmation email");
	Format::endForm("Submit", "Clear");

	print <<END;
	</div>
END

	Format::createFooter();
}

sub handleUpload {
    # MOVE redirect to action "submit_confirmed"
    # MOVE: move handleSubmitConfirmed here
}

sub handleSubmitConfirmed {
	# User must be logged in already in this version
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	my ($user, $role) = $sessionInfo =~ /:(.+?):(.+)/;
	Assert::assertTrue($user, "Need to create an account first");

	# Check that form is complete
	Assert::assertNotEmpty("title", "Please enter a title for your submission");
	Assert::assertNotEmpty("authors", "Please enter at least one author");
	Assert::assertEquals("contact_name", "\\w+\\s+\\w+", "No valid contact name provided (FirstName LastName)");
	Assert::assertNotEmpty("contact_email", "No email address provided for contact author");
	Assert::assertNotEmpty("track", "You did not choose a track");
	Assert::assertNotEmpty("abstract", "Please enter an abstract for your submission");
	# 09-02-12 mw removed check because some users don't want to enter keywords,
	# and it can make the system annoying to use
	# Assert::assertNotEmpty("tags", "Please enter at least one keyword");
	Assert::assertNotEmpty("paper", "Please select a file to upload");
		
	my $isInitialSubmission;
	if ($q->param("reference")) {
		Assert::assertNotEmpty("reason", "Please enter a reason for the update");
		$isInitialSubmission = 0;
	} else {
		# DONE: create new reference in Core::Upload
		$isInitialSubmission = 1;
	}
	
	my $paper = $q->param("paper");
	my @status = Upload::save($paper);
	
	my $uploadedSize = int(10 * $status[1] / 1024 + 0.5)/10;
	$q->param("file_name" => $status[0]); 
	$q->param("version" => $status[2]);
	my $version = $status[2];
	
	# DONE: invalidate session
	# NOTE: Only invalidate session if all required parameters have been submitted
	
	# DONE: no longer invalidate the session (session expires when user logs out or exits browser)
	# Session::invalidate($q->param("session"));
	
    # DONE: save submission record (with timestamp, so history can be reconstructed)
	my ($reference) = $q->param("reference") =~ /(\d+)/;
    saveSubmission($reference);
    
    # MOVE: redirect to action "submit_confirmed"
    # MOVE: this action should be renamed to "upload" instead
    
	Format::createHeader("Submit > Confirmed", "", "js/validate.js");
	
	my $name =  $q->param("contact_name");
	my ($firstName) = $q->param("contact_name") =~ /^(\w+)/;
	
	# TODO: sanitizing email requires more thought
	my $contact_email = $q->param("contact_email");
	$contact_email =~ s/,|\s//g;
	
	my $title = $q->param("title");
	my $track = $q->param("track");
	my $trackTitle = $config->{"track_$track"};
	
	my $password = "";
	my $reason = $q->param("reason");
	my $abstract = $q->param("abstract");
	my $comments = $q->param("comments");

	if ($isInitialSubmission) {
		# create record of submission
		# while information is available from full submission records, creating this index will be 
		# more efficient, and provides a simple way of looking up submissions by author
		Submission::recordSubmission($reference, $user);
		
		# add user as author on first submission
		unless (Role::hasRole($user, $CONFERENCE_ID, "author")) {
			Role::addRole($user, $CONFERENCE_ID, "author");
		}
		
		print <<END;
<p>Dear $firstName,</p>
<p>Thank you for your submission "$title" ($uploadedSize kB).</p>
	<dd>Track: $trackTitle</dd>
	<dd>Reference number: $reference</dd>
END
	} else {
		print <<END;
<p>Dear $firstName,</p>
<p>Thank you for your updated submission "$title" ($uploadedSize kB).</p>
	<dd>Track: $trackTitle</dd>
	<dd>Reference number: $reference</dd>
	<dd>Reason for update: $reason</dd>
END
	}

	print <<END;
<p>Within a few minutes you should also receive an email confirmation.</p>

<p>$PROGRAM_CHAIR, $CONFERENCE_CHAIR<br/>
$CONFERENCE Conference Chairs</p>
END

	# No longer send password in email
	my $status1 = sendSubmissionConfirmation($contact_email, $name, $firstName, 
		$title, $track, $uploadedSize, $reference, $isInitialSubmission, $reason);
	my $status2 = notifyChairsOfSubmission($contact_email, $name, 
		$title, $track, $reference, $isInitialSubmission, $reason, $abstract, $comments);
	if ($config->{"debug"}) {
		print "Email 1: <pre>$status1</pre>";
		print "Email 2: <pre>$status2</pre>";
	}
	Format::createFooter();	
}

sub handleSendAuthorLogin {
	unless ($q->param("reference")) {
		Format::createHeader("Submit > Password", "", "");
		Format::startForm("post", "send_author_login");
		Format::createFreetext("To retrieve your password, please provide the reference number of your paper.");
		Format::createTextWithTitle("Enter your reference number", 
			"My reference number is", "reference", 40);
		Format::createFreetext("Once you submit, your password will be sent to this email address.");
		Format::endForm("Send password");
		Format::createFooter();
	} else {
		Assert::assertEquals("reference", "\\d+", "Please enter a valid reference number");
		my $status = sendPasswordForReference($q->param("reference"));
		if ($config->{"debug"}) {
			Format::createHeader("Submit > Password", "", "");
			print "Email: <pre>$status</pre>";
			Format::createFooter();
		} else {
			handleSignIn();
		}
	}
}

# Not working yet, but can be implemented with new retrievePassword
sub handleSendNonAuthorLogin {
	unless ($q->param("email")) {
		Format::createHeader("Submit > Password", "", "");
		Format::startForm("post", "send_non_author_login");
		Format::createFreetext("To retrieve your password, please provide the email address you use to log in.");
		Format::createTextWithTitle("Enter your email address", 
			"My email address is", "email", 40);
		Format::createFreetext("Once you submit, your password will be sent to this email address.");
		Format::endForm("Send password");
		Format::createFooter();
	} else {
		handleSignIn();
	}
}

sub handleError {
	my ($error) = @_;
	# DONE: log errors with error details
	addToErrorLog($error);
	Format::createHeader("Submit > Error");
	my $uriEncodedError = uri_escape($error);
	print <<END;
<p><b style="color:red">$error</b></p>
<p><input type=button value="Back to form" onClick="history.go(-1)"/></p>
END
	Format::createFooter();
	exit(0);
}

# Subservient functions

sub retrievePassword_no_longer_used {
	my ($reference) = @_;
	my $match = "";
	open (PASSWORD, "data/password.dat") ||
		handleError("Internal: could not check login");
	flock(PASSWORD, $LOCK);
	while (<PASSWORD>) {
		if (/^$reference, .+?, (.+)/) {
			$match = $1; 
			last;
		}
	}
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
	return $match;
}

sub saveSubmission {
	# DONE: why are parameters set in this script not saved to the state as well?
	# UPDATE: remote_host is, but version is not (does not show up in dump either now?)
	# they both are, just version was only created if an existing paper was updated
	my ($reference) = @_;
	$q->param("remote_host" => $q->remote_host());
	Serialize::saveState($timestamp . "_" . $reference);
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

# Send submission confirmation to author and chairs
sub sendSubmissionConfirmation {
	my ($contact_email, $name, $firstName, 
		$title, $track, $uploadedSize, $reference, $isInitialSubmission, $reason) = @_;

	my $label = $timestamp . "_" . $reference;
	my $token = Access::token($label);

# 	TODO: notify shepherd and associated pc member (once assigned)
#	DONE: remind me ... what is bid? ... should have been $reference
#	NOTE: can defer this until shepherds are assigned

	my $trackTitle = $config->{"track_$track"};
	my $trackChairEmail = $config->{"track_${track}_chair_email"};

	my ($sanitizedName) = $name	=~ m/([\w\s-]*)/;	
	my $tmpFileName = Email2::tmpFileName($timestamp, $sanitizedName);
	open (MAIL, ">$tmpFileName") || 
		Audit::handleError("Cannot create temporary file");

	if ($isInitialSubmission) {
		print MAIL <<END;
Dear $firstName,

thank you for your submission "$title" ($uploadedSize kB).

Track: $trackTitle
Reference number: $reference

$PROGRAM_CHAIR, $CONFERENCE_CHAIR	
$CONFERENCE Conference Chairs
END
	} else {
		print MAIL <<END;
Dear $firstName,

thank you for your updated submission "$title" ($uploadedSize kB).

Track: $trackTitle
Reference number: $reference
Reason for update: $reason
	
$PROGRAM_CHAIR, $CONFERENCE_CHAIR
$CONFERENCE Conference Chairs
END
	}
	close (MAIL);
	my $mail_status = Email2::send($contact_email, "$trackChairEmail",
		"[$CONFERENCE] Submission $reference received", 
		$tmpFileName, 1);
	return $mail_status;
}

# Notify chairs of submission
#
sub notifyChairsOfSubmission {
	my ($contact_email, $name, 
		$title, $track, $reference, $isInitialSubmission, $reason, 
		$abstract, $comments) = @_;

	my $label = $timestamp . "_" . $reference;
	my $token = Access::token($label);

	my $shepherdAndPcEmails = shepherdAndPcEmails($reference);

	my $trackTitle = $config->{"track_$track"};
	my $trackChairEmail = $config->{"track_${track}_chair_email"};
	
	# temporary file name is PROGRAM_CHAIR name plus "_" to cover the
	# particular case that the chair submits a paper
	my ($sanitizedName) = $PROGRAM_CHAIR =~ m/([\w\s-]*)/;	
	my $tmpFileName = Email2::tmpFileName($timestamp, $sanitizedName . "_");
	open (MAIL, ">$tmpFileName") || 
	Audit::handleError("Cannot create temporary file");

	my $status;
	if ($isInitialSubmission) {
		$status = "New";
		print MAIL <<END;
New submission received from $name ($contact_email).

Title: $title
Track: $trackTitle
Abstract: $abstract
Comments: $comments
File: $baseUrl/shepherd.cgi?token=$token&action=download&label=$label
END
	} else {
		$status = "Updated";
		print MAIL <<END;
Updated submission received from $name ($contact_email).

Title: $title
Track: $trackTitle
Reason for update: $reason
Abstract: $abstract
Comments: $comments
File: $baseUrl/shepherd.cgi?token=$token&action=download&label=$label
END
	}
	close (MAIL);
	$mail_status = Email2::send($PROGRAM_CHAIR_EMAIL, $trackChairEmail . $shepherdAndPcEmails, 
		"[$CONFERENCE] $status submission $reference received", 
		$tmpFileName, 0);
	return $mail_status;
}

sub shepherdAndPcEmails {
	my ($reference) = @_;
	my %assignment = Shepherd::assignedTo($reference);
	if ($assignment{"shepherd"}) {
		# lookup shepherd's and pc member's contact information
		my %shepherd = Contact::loadContact($assignment{"shepherd"});
		my %pc = Contact::loadContact($assignment{"pc"});
		return "," . $shepherd{"email"} . "," . $pc{"email"};
	} else {
		return "";
	}
}

# Recover the password for a submission. Send to the contact author's email.
#
# $reference is the reference number of the submission
#
# TODO: no longer storing raw password
# this function needs to be replaced by a password reset option 
sub sendPasswordForReference {
	my ($reference) = @_;
	
	# get record metadata
	my %labels = Records::listCurrent();
	my $record = Records::getRecord($labels{$reference}); 
	my $name = $record->param("contact_name");
	my $email = $record->param("contact_email");
	
	# create temporary file
	my ($sanitizedName) = $name	=~ m/([\w\s-]*)/;	
	my $tmpFileName = Email2::tmpFileName($timestamp, $sanitizedName);
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
	my $status = Email2::send($email, "",
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
} elsif ($action eq "submit") {
	handleSubmit();
} elsif ($action eq "submit_confirmed") {
	handleSubmitConfirmed();
} elsif ($action eq "test") {
	Format::createHeader("Submit > Test");
	printEnv();
	Format::createFooter();
} elsif ($action eq "send_author_login") {
	handleSendAuthorLogin();
} elsif ($action eq "send_non_author_login") {
	handleSendNonAuthorLogin();
} else {
	handleError("No such action");
}
