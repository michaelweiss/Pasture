#!/usr/bin/perl -wT
use CGI;
use CGI::Carp qw( fatalsToBrowser );
use URI::Escape ('uri_escape');
use Time::Local;

use lib '.';
use Core::Format;
use Core::Serialize;
use Core::Serialize::Records;
use Core::Email;
use Core::Session;
use Core::Password;
use Core::Access;
use Core::Tags;
use Core::Assert;
use Core::Screen;
use Core::Audit;
use Core::Review;
use Core::Shepherd;
use Core::Decision;

our $q = new CGI;
our $timestamp = time();

our $script = "shepherd.cgi";

our $config = Serialize::getConfig();
our $WEBCHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $CONFERENCE_ID = $config->{"conference_id"};
our $CONFERENCE_WEBSITE = $config->{"conference_website"};
our $baseUrl = $config->{"url"};
our $PROGRAM_CHAIR_TITLE = $config->{"program_chair_title"};
our $FOCUS_GROUP_TRACK = $config->{"focus_group_track"};

our %labels = Records::listCurrent();

# initially, mode is submissions
# once assigments have been made, we can switch to assginments mode
our $mode;
if ($config->{"shepherd_submission_open"}) {
	$mode = "submissions";	# get shepherds
} elsif ($config->{"shepherding_open"}) {
	$mode = "assignments";	# view shepherding assignments
}

# turn on so that all PCs can view the same papers as the $PROGRAM_CHAIR_TITLE
# to be used during last phase of final review to fill in gaps in reviewing
our $pcCanViewAll = 0;
if ($config->{"pc_can_view_all"}) {
	$pcCanViewAll = 1;
}

# remember whether a new account was created
TODO: deprecated
my $newAccountCreated = 0;

BEGIN {
	CGI::Carp::set_message( \&Audit::handleUnexpectedError );
}

# Handlers

sub handleSignIn {
	Format::createHeader("Shepherd > Sign in", "", "js/validate.js");
	
	my $disabled = $config->{"shepherd_submission_open"} || 
		$config->{"shepherding_open"} ? "" : "disabled";
		
#	print <<END;
#<h3>Log in as</h3>
#<p>
#<input name="role" type="radio" value="author" 
#	onClick="document.location='$baseUrl/submit.cgi'"/> Author &nbsp;
#<input name="role" type="radio" value="shepherd" checked
#	onClick="document.location='$baseUrl/shepherd.cgi'" $disabled/> Shepherd &nbsp;
#<input name="role" type="radio" value="pc"
#	onClick="document.location='$baseUrl/screen.cgi'"/> PC Member (Screening) &nbsp;
#<input name="role" type="radio" value="admin" 
#	onClick="document.location='$baseUrl/admin.cgi'"/> Chair &nbsp;
#<input name="role" type="radio" value="participant"
#	onClick="document.location='$baseUrl/register.cgi'"/> Participant
#</p>
#END

	# form action selected based on mode (submissions or assignments)
	Format::startForm("post", $mode, "return checkShepherdSignInForm(this)");
	Format::createHidden("session", Session::create(Session::uniqueId(), $timestamp));

	if ($mode eq "submissions") {
		print <<END;
<p>Thank you for your interest in shepherding a paper for $CONFERENCE.</p>
END
	} elsif ($mode eq "assignments") {
		print "<p>Please log in as a shepherd for $CONFERENCE.</p>\n";
	} else {
		print "<p>No shepherding is taking place right now.</p>\n";
		Format::createFooter();
		return;
	}
	
#	Format::createTextWithTitle("What is your email address?", 
#		"My email address is:", "email", 40);
		
	print <<END;
			<table cellpadding="0" cellspacing="5">
				<tr>
					<td colspan="1">My email address is:</td>
					<td width="10"></td>
					<td><input name="email" type="text"/></td>
				</tr>
END
	if ($mode eq "submissions") {
		print <<END;
				<tr>
					<td>My name is:</td>
					<td width="10"></td>
					<td colspan="2"><input name="name" type="text"/></td>
				</tr>
				<tr>
					<td>The access code is:</td>
					<td width="10"></td>
					<td><input name="code" type="password"
						onFocus="this.form.status[0].checked=true"/>
						<input name="status" type="hidden" value="new"></td>
				</tr>
			<!--
				<tr>
					<td height="10"></td>
				</tr>
				<tr>
					<td><input name="status" type="radio" value ="existing"/></td>
					<td colspan="3">No, I already have a password:</td>
				</tr>
				<tr>
					<td height="5"></td>
				</tr>
				<tr>
					<td></td>
					<td>My password is:</td>
					<td width="10"></td>
					<td><input name="password" type="password"
						onFocus="this.form.status[1].checked=true"/></td>
				</tr>
			-->
			</table>
END
	} else {
		print <<END;
				<tr>
					<td colspan="2">My password is:</td>
					<td width="10"></td>
					<td><input name="password" type="password"/></td>
				</tr>
			</table>
END
	}

	Format::endForm("Sign in");

	unless ($mode eq "submissions") {
		Format::createFreetext(
			"<a href=\"$baseUrl/$script?action=send_pc_login\">Forgot your password? Click here</a>");
	}

	Format::createFooter();
}

# show submissions (except ones that were rejected during screening)
sub handleSubmissions {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired. Please sign in first.");
		
	my ($user, $role) = $sessionInfo =~ /:(.+?):(.+)/;	
	
	unless ($user) {
		# TODO: shepherds need to create an account
		Assert::assertTrue(0, "You need to create an account first");
		
		Assert::assertEquals("email", "@", "Please enter a valid email address");
		if ($q->param("status") eq "new") {
			unless ($q->param("code") eq $config->{"shepherd_password"}) {
				Audit::handleError("Please reenter the access code");
			}
			Assert::assertNotEmpty("name", "Please enter your name");
			$role = "shepherd";
		} else {
			unless ($role = Review::authenticate($q->param("email"), $q->param("password"))) {
				# user is shepherd, pc, or admin
			 	Audit::handleError("Sorry, you no not have access to this site");
			}
			$q->param( "name" => Review::getReviewerName($q->param("email")) );
		}
		Session::setUser($q->param("session"), $q->param("email"), $role);
		
		# need to set user, checking later to find existing bids
		$user = $q->param("email");
	}
	Assert::assertTrue($role eq "shepherd" || $role eq "pc" || $role eq "admin",
		"Only shepherds, PC members, and shepherds can perform this action.");
		
	Format::createHeader("Bids", "", "js/validate.js");
	
		print <<END;
	<p>Oops, this feature is unavailable at this time.</p>
END

	Format::createFooter();
	return;
	
	Format::createFreetext("Please bid for the papers you wish to shepherd. If you provide us with multiple options, we can assign you a paper even if your top preference has already been assigned to somebody else.");
	Format::createFreetext("If you only want to submit a specific paper, just bid once and email the chair that you really want that paper.");
	Format::createFreetext("If you had previously made a bid for a paper, your old bid will be shown in <font color=green>green</font>.");
	Format::createFreetext("<em>Note: By clicking on the number left to the paper description, you can download the paper.</em>");
	
	print <<END;
	<h4>Legend</h4>
	<p>If you want to shepherd a paper, choose your level of priority in the dropdown menu on the left:</p>
	<p>
		<table>
			<tr><td width="20" align="left">1</td><td>I would like to shepherd this paper</td></tr>
			<tr><td align="left">2</td><td>I could be convinced to shepherd this paper</td></tr>
			<tr><td align="left">3</td><td>I am willing to shepherd this paper, but only if nobody else does</td></tr> 
			<tr><td height="15"></td></tr>
			<tr><td><img border="0" src="/europlop/images/vote.png"/></a></td><td><em>average-vote</em> pre-sheperding vote &nbsp; (1:it's a joy, 2:good ideas, 3:strong shepherd needed, 4:high risk)</td></tr>
		</table>
	</p>
END

	Format::startForm("post", "selection", "");
	
	Format::createHidden("session", $q->param("session"));
	Format::createHidden("email", $q->param("email"));
	Format::createHidden("name", $q->param("name"));

	my $votes = Screen::votes();
	my $preferences = Shepherd::preferencesByUser();
	
	my $currentTrack = -1;
	my %records = Records::getAllRecords(Records::listCurrent());
	foreach $label (
		sort { $records{$a}->param("track") <=> $records{$b}->param("track") }
			sort { $records{$a}->param("reference") <=> $records{$b}->param("reference") } 
				keys %records) {
		my $record = $records{$label};
		my $reference = $record->param("reference");
		unless (Shepherd::status($reference) eq "rejected" ||
			Shepherd::status($reference) eq "withdrawn" ||
			Shepherd::status($reference) eq "pending" ||
        	$record->param("track") eq $FOCUS_GROUP_TRACK) {
			my $authors = Review::getAuthors($record);
			$authors =~ s|\r\n|, |g;

			my $contact_name = $record->param("contact_name");
			my $email = $record->param("contact_email");
			
			my $title = $record->param("title");
			my $abstract = $record->param("abstract");
			my $fileName = $record->param("file_name");
			$fileName =~ s/\.\w+$//;
			my $comments = $record->param("comments");
			
			my $track = $record->param("track");
			if ($currentTrack != $track) {
				Format::createFreetext("<h3>" . $config->{"track_" . $track} . "</h3>");
				$currentTrack = $track;
			}
			
			my $token = uri_escape(Access::token($label));
			my $tags = Review::getTags($record);
						
			my $averageVote =  ($role eq "pc" || $role eq "admin") && 
				Review::averageVote($votes, $reference) || "(-)";
			print <<END;
<table border="0" cellpadding="2" cellspacing="10" width="100%">
	<tbody>
		<tr>
			<td valign="top" width="8%" align="left">
END

			unless (Shepherd::status($reference) eq "assigned") {
				print <<END;
				<select name="submission_$label"/>
					<option value="" selected></option>
					<option value="1">1</option>
					<option value="2">2</option>
					<option value="3">3</option>
				</select>
END
			} else {
				print "NA ";
			}
			
			showSavedBid($preferences, $user, $reference);
			
			# DONE: otherwise list PC member and shepherd
			
			print <<END;
			</td>
			<td valign="top" align="right" width="3%">
				<a href="?token=$token&action=download&label=$label">$reference</a>
			</td>
			<td valign="top">
			 	$authors <!--<br/>
			 	<a href="mailto:$email">$email--></a>
			</td>
		</tr>
END

			# DONE: show shepherd and PC for papers that have been assigned
			if (Shepherd::status($reference) eq "assigned") {
				my %assignment = Shepherd::assignedTo($reference);
				# TODO: email -> user id
				my $pc_email = $assignment{"pc"};
				my $pc_name = Review::getReviewerName($pc_email);
				# TODO: email -> user id
				my $shepherd_email = $assignment{"shepherd"};
				my $shepherd_name = Review::getReviewerName($shepherd_email);
				print <<END;
		<tr>
			<td valign="top"></td>
			<td valign="top"></td>
			<td valign="top"> 
				Shepherd: <a href="mailto:$shepherd_email">$shepherd_name</a>
				(PC: <a href="mailto:$pc_email">$pc_name</a>)
			</td>
		</tr>
END
			}
			
			print <<END;
		<tr>
			<td valign="top"></td>
			<td valign="top"></td>
			<td valign="top">
				<b>$title</b>
				<p><font size="-1" color="grey">$comments</font></p>
				<p>$abstract</p>
				<p>Tags: $tags</p>
			</td>
		</tr>
		<tr>
			<td valign="top"></td>
			<td valign="top"></td>
			<td><image border="0" src="/europlop/images/vote.png"/></a>&nbsp; $averageVote pre-shepherding vote &nbsp; (1:it's a joy, 2:good ideas, 3:strong shepherd needed, 4:high risk)
			</td>
		</tr>
		</tbody>
</table>
END
		}
	} 
		
	Format::endForm("Submit");
	
	Format::createFooter();
}

# show submissions currently shepherded
sub handleShepherdedPapers {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired. Please sign in first.");
		
	my ($user, $role) = $sessionInfo =~ /:(.+?):(.+)/;	

	Format::createHeader("Shepherded Papers", "", "");
	
print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	print <<END;
	<p>Oops, this feature is unavailable at this time.</p>
END

	Format::createFooter();
	return;
	
	my $user = $q->param("user");
	unless ($user) { # show all
		Format::createFreetext("The following papers are currently shepherded for $CONFERENCE, which means that an experienced pattern author collaborates with the authors of the submissions to improve them prior to acceptance for $CONFERENCE.");
	} else {
		Format::createFreetext("The following papers have been assigned to you as supervising PC member.");
	}
	Format::createFreetext("<em>Note: Click on the email icon next to the author name(s) to send an email to everyone involved with a paper</em><br/><em>Click on the document icon next to the title to download the most recent version of a paper</em>");
	
	# TODO: make configurable
	# Format::createFreetext("The shepherding phase is now closed. Please see the workshop assignments for the list of accepted papers.");
	
	print <<END;
	<table border="0" cellpadding="2" cellspacing="10" width="100%">
		<tbody>
END

	my $currentTrack = -1;
	my %records = Records::getAllRecords(Records::listCurrent());
	foreach $label (sort { $records{$a}->param("track") . "_" . $records{$a}->param("reference") cmp 
		$records{$b}->param("track") . "_" . $records{$b}->param("reference") } keys %records) {
		my $record = $records{$label};
		my $reference = $record->param("reference");
		unless (Shepherd::status($reference) eq "reject" ||
			Shepherd::status($reference) eq "withdrawn" ||
        	$record->param("track") eq $FOCUS_GROUP_TRACK) {
			if (Shepherd::status($reference) eq "assigned") {
				my %assignment = Shepherd::assignedTo($reference);
				# TODO: email -> user id
				my $pc_email = $assignment{"pc"};
				my $shepherd_email = $assignment{"shepherd"};
				# either all, or only for a specific user
				if (!$user || 
					$q->param("role") eq "pc" && $pc_email eq $user ||
					$q->param("role") eq "shepherd" && $shepherd_email eq $user) {
					my $pc_name = Review::getReviewerName($pc_email);
					my $shepherd_name = Review::getReviewerName($shepherd_email);
					
					my $authors = Review::getAuthors($record);
					$authors =~ s|\r\n|, |g;
		
					my $contact_name = $record->param("contact_name");
					my $email = $record->param("contact_email");
					
					my $title = $record->param("title");
					my $abstract = $record->param("abstract");
					my $fileName = $record->param("file_name");
					$fileName =~ s/\.\w+$//;
					
					my $token = uri_escape(Access::token($label));
					
					# TODO: check why it generates Dec 31
					my $lastUpdated = lastUpdated($reference);
			
					my $track = $record->param("track");
					if ($currentTrack != $track) {
						print <<END;
		<tr>
			<td colspan="1">
				<h3>$config->{"track_$track"}</h3>
			</td>
		</tr>
END
						$currentTrack = $track;
					}	# if
			
					print <<END;
		<tr>
			<td valign="top">
			 	<a href="mailto:$email?cc=$shepherd_email,$pc_email&subject=[$CONFERENCE] $title"><img src="/europlop/images/email.gif"></a> &nbsp; $authors
			</td>
		</tr>
		<tr>
			<td valign="top" width="97%">
				PC member: $pc_name<br/>
				Shepherd: $shepherd_name
			</td>
		</tr>
		<tr>
			<td valign="top" width="97%">
				<a href="?token=$token&action=download&label=$label"><img width="11" height="11" src="/europlop/images/text.gif"></a> &nbsp;
				<b>$title</b><br/><font size='-2' color='grey'>Last updated on $lastUpdated</font>
				<p>$abstract</p>
				<hr/>
			</td>
		</tr>
END
    			}	# if
			}	# if
        } 	# unless
	}	# foreach
	
	print <<END;
			</tbody>
	</table>
	
	<p>This list will be updated once we have made a final acceptance decision.</p>
END
	
	Format::createFooter();
}

sub handleSelection {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired. Please sign in first.");

	# DONE: check that at least one selection has been made
	my @papers;
	foreach ($q->param()) {
		if (/submission_(\d+)_(\d+)/) {
			my $timestamp = $1;
			my $reference = $2;
			my $priority = $q->param($_);
			if ($priority) {
				my $record = Records::getRecord($timestamp . "_" . $reference);
				my $title = $record->param("title");
				push(@papers, "$priority, $reference, $timestamp");
			}
		}
	}
	unless (scalar @papers > 0) {
		Audit::handleError("Please select at least one submission");
	}
		
	Format::createHeader("Bid confirmation", "", "js/validate.js");
	
print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	my $email = $q->param("email");
	my ($firstName) = $q->param("name") =~ /^(\w+)/;

	print <<END;
<p>Dear $firstName,</p>
<p>thanks for volunteering as a shepherd for the following papers:</p>
	<p>
		<table>
END

	# PART: store the following in a string to insert in confirmation email
	my $papers = "";
	foreach (sort @papers) {
		my ($priority, $reference, $timestamp) = split(/, /);
		Shepherd::savePreference($timestamp, $email, $reference, $priority);
		my $record = Records::getRecord($timestamp . "_" . $reference);
		my $title = $record->param("title");
		$papers .= "$priority, $reference, $timestamp\n";
		print <<END;
			<tr><td width="20" align="left">$priority</td><td>$title</td></tr>
END
	}
	
	# get password associated with email 
	# ... check if pc member, chair, or existing shepherd
	my $password = Review::getPassword($email);
	  
	# create shepherding account if no password assigned to email
  	unless ($password) {
	    my $role = "shepherd";
	    Review::addReviewer($q->param("email"), $q->param("name"), $role);
		# if user is an author use their author password
		$password = Password::retrievePassword($email);
		# ... otherwise generate one
		unless ($password) {
	    	$password = Password::generatePassword(6);
	    	$newAccountCreated = 1;
		} 
		# authors as well as new shepherds will be added
	    Review::addRole($q->param("email"), $password, $role);
  	}

	print <<END;		
		</table>
	</p>
	
	<p><b>Legend:</b></p>
	<p>
			<table>
			<tr><td width="20" align="left">1</td><td>I would like to shepherd this paper</td></tr>
			<tr><td align="left">2</td><td>I could be convinced to shepherd this paper</td></tr>
			<tr><td align="left">3</td><td>I am willing to shepherd this paper, but only if nobody else does</td></tr> 
		</table>
	</p>
	
	<p>Your bid has been sent to the $CONFERENCE $PROGRAM_CHAIR_TITLE who will confirm them as soon as possible.<p>
	<p>Please keep in mind that there may be more then one volunteer for a specific paper. This is the reason why we cannot start shepherding immediately.</p>
END

	if ($newAccountCreated) {
		print <<END;
	<p>We have created a new account for you. The user name is your email address and the password is "$password". If selected as a shepherd, you need this account to submit your shepherding recommendations.</p>
END
	}

	print <<END;
	<p>Thanks for being patient,</p>

	<p>$config->{"program_chair"}<br/>
	$CONFERENCE $PROGRAM_CHAIR_TITLE</p>
END
	Format::createFreetext("You should receive a confirmation email in a few minutes. If not, please contact the web chair at <a href=\"mailto:$WEBCHAIR_EMAIL\">$WEBCHAIR_EMAIL</a>.");
	
	sendConfirmationOfSherpherdingBid($email, $firstName, $papers);
	notifyShepherdingBid($q->param("name"), $email, $papers);
		
	Format::createFooter();
}

sub handleAccept {
	my $token = Access::token($q->param("email") . "_" . $q->param("label"));
	unless ($token eq $q->param("token")) {
		Audit::handleError("You are not allowed to perform this action");
	} 
					
	# TODO: email -> user id
	# can get user name from the session
	my $email = $q->param("email");
	my $name = Review::getReviewerName($email);
	
	my ($reference) = $q->param("label") =~ /_(\d+)$/;

	Format::createHeader("Accept", "", "js/validate.js");
	
	my $record = Records::getRecord($q->param("label"));
	my $authors = Review::getAuthors($record);
	my $title = $record->param("title");

	my %assignment = Shepherd::assignedTo($reference);
	if ($assignment{"shepherd"}) {
		
		my $name = Review::getReviewerName($assignment{"shepherd"});
		print <<END;
<p>Paper $reference has already been assigned to $name:</p>
<dd><p>$authors, <b>$title</b></p></dd>
END
		Session::invalidate($session);
		
	} else {
		
		Format::startForm("post", "accept_confirmed", "");
		Format::createHidden("session", Session::create(Session::uniqueId(), $timestamp));
		Format::createHidden("email", $q->param("email"));
		Format::createHidden("label", $q->param("label"));
		Format::createHidden("token", $q->param("token"));
			
		print <<END;
<p>Confirm that you want to accept the bid from $name for paper $reference:</p>
<p>$authors, <b>$title</b></p>
END

		# DONE: select PC member
		print("Select PC member: ");
		showReviewersOfPaper($reference);		
		
		Format::endForm("Confirm");
		
		showBids($reference);
	}
	Format::createFooter();
}

sub handleReject {
	my $token = Access::token($q->param("email") . "_" . $q->param("label"));
	unless ($token eq $q->param("token")) {
		Audit::handleError("You are not allowed to perform this action");
	} 

	# TODO: email -> user id
	my $email = $q->param("email");
	my $name = Review::getReviewerName($email);

	my ($reference) = $q->param("label") =~ /_(\d+)$/;
	
	Format::createHeader("Reject", "", "js/validate.js");

	my $record = Records::getRecord($q->param("label"));
	my $authors = Review::getAuthors($record);
	my $title = $record->param("title");

	my %assignment = Shepherd::assignedTo($reference);
	unless ($assignment{"shepherd"}) {
		
		my $name = Review::getReviewerName($assignment{"shepherd"});
		print <<END;
<p>Paper $reference has not been assigned to anyone yet:</p>
<dd><p>$authors, <b>$title</b></p></dd> 
END
		Session::invalidate($session);
		
	} else {
		
		Format::startForm("post", "reject_confirmed", "");
		Format::createHidden("session", Session::create(Session::uniqueId(), $timestamp));
		Format::createHidden("email", $q->param("email"));
		Format::createHidden("label", $q->param("label"));
		Format::createHidden("token", $q->param("token"));
			
		print <<END;
<p>Confirm that you want to reject the bid from $name for paper $reference:</p>
<dd><p>$authors, <b>$title</b></p></dd>
END
		Format::endForm("Confirm");
		
		showBids($reference);
	}
	Format::createFooter();
}

sub handleAcceptConfirmed {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired. Please sign in first.");
	
	Session::invalidate($session);
	
	Format::createHeader("Accept confirmed", "", "js/validate.js");
	
	# TODO: email -> user id
	my $email = $q->param("email");
	my $name = Review::getReviewerName($email);
	my $label = $q->param("label");

	my ($reference) = $q->param("label") =~ /_(\d+)$/;
	
	my $pc_email = $q->param("pc_email");
	my $pc_name = Review::getReviewerName($pc_email);

	# DONE: update status of paper
	Shepherd::changeStatus($timestamp, $reference, "assigned");
	
	# TODO: record review assignment (PC and shepherd)
	Shepherd::assign($timestamp, $reference, $email, $pc_email);

	Format::createFreetext("Emails have been sent to the shepherd and the sheep.");

	confirmBid($email, $name, $label, $pc_email, $pc_name);
	introduceSheepToShepherd($email, $name, $label, $pc_email, $pc_name);
	
	Format::createFooter();
}

sub handleRejectConfirmed {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired. Please sign in first.");
	
	Session::invalidate($session);

	Format::createHeader("Reject confirmed", "", "js/validate.js");
	
	# TODO: email -> user id
	my $email = $q->param("email");
	my $name = Review::getReviewerName($email);
	my $label = $q->param("label");

	Format::createFreetext("An email has been sent to the shepherd.");

	rejectBid($email, $name, $label);
	
	Format::createFooter();
}

# TODO: move to Review.pm
sub handleDownload {
	# DONE: check that this is a valid session id
	# DONE: use token-based authentication instead (not user-based)
	# TODO: implement session timeout
#	Assert::assertTrue(Session::check($q->param("session")), 
#		"Session expired. Please sign infirst.");

	my ($label) = $q->param("label") =~ /^(\d+_\d+)$/;
#	Assert::assertTrue(Access::check($q->param("token"), $label),
#		"You are not allowed to access the requested document.");
	my $token = Access::token($label);
	unless ($token eq $q->param("token")) {
		Audit::handleError("You are not allowed to access the requested document");
	} else {
		my $record = Records::getRecord($label);
		my $fileName = $record->param("file_name");
		my ($type) = $fileName =~ /\.(\w+)$/;
		if ($type eq "pdf") {
			print $::q->header(-type => "application/pdf",
				-attachment => $fileName);
		} elsif ($type eq "doc") {
			print $::q->header(-type => "application/msword",
				-attachment => $fileName);
		} elsif ($type eq "txt") {	# 09-02-12 mw can download .txt files now
			print $::q->header(-type => "text/plain",
				-attachment => $fileName);
		} else {
			Audit::handleError("file type not supported");
		}
		open FILE, "papers/$fileName";
		while (<FILE>) {
			print;
		}
		close FILE;
	}
}

sub handleAssignments {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired. Please sign in first.");

	my ($user, $role) = $sessionInfo =~ /:(.+?):(.+)/;	
	unless ($user) {
		Assert::assertEquals("email", "@", "Please enter a valid email address");
		$user = $q->param("email");
		$role = Review::authenticate($user, $q->param("password"));
		Session::setUser($q->param("session"), $user, $role);
	}
	Assert::assertTrue($role eq "shepherd" || $role eq "pc" || $role eq "admin",
		"Only shepherds, PC members, and shepherds can perform this action.");

	# TODO: email -> user id
	$q->param( "name" => Review::getReviewerName($user) );
	
	Format::createHeader("Review of updated submissions", "", "js/validate.js");
	
print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

print <<END;
	<p>Oops, this feature is unavailable at this time.</p>
END

	Format::createFooter();
	return;
	
	my ($firstName) = $q->param("name") =~ /^(\w+)/;
	
	# get all record metadata
	my %records = Records::getAllRecords(%labels);
	
	# initial PC assignments
	my @initialPcForPaper;
	unless ($pcCanViewAll) {
		@initialPcForPaper = Decision::getScreenAssignmentsExceptRejected($user);
	} else {
		# TODO: should use $config->{"program_chair_email"}, but during testing this is
		# set to a dummy address so won't get the right result here
		@initialPcForPaper = Decision::getScreenAssignmentsExceptRejected(
			$config->{"program_chair_email"});
	}
		
	# get all assignments for this shepherd/pc member
	my $assignments = Shepherd::assignments();
	my @shepherdForPaper = ();
	my @pcForPaper = ();
	foreach $reference (sort { $a <=> $b } keys %$assignments) {
		my $shepherd = $assignments->{$reference}->{"shepherd"};
		
		# TODO: distinguish supervising pc from other pc (initial or all)
		my $pc = $assignments->{$reference}->{"pc"};
		
		# DONE: if $pcCanViewAll is enabled, pc members still see the papers they
		# shepherd or supervise as PCs in the sections below
		if ($shepherd eq $user) {
			push (@shepherdForPaper, $reference);
			@initialPcForPaper = copyWithoutElements($reference, @initialPcForPaper);
		} elsif ($pc eq $user) {
			push (@pcForPaper, $reference);
			@initialPcForPaper = copyWithoutElements($reference, @initialPcForPaper);
		}
	}
	
	# all votes
	my $votes = Decision::votes();
	
	print <<END;
<table border=0 cellspacing=10 width=100%>
  <tr><td colspan=2><p>$firstName, this page allows you to enter your review decisions.</p>
    <ul>
    <li>To access the most recent versions of your shepherding and PC assignments, please select the paper numbers on the left. The last upload time is shown after the title.</li> 
    <li>To enter your votes click on the "vote" buttons on right.</li>
    </ul>
  </td></tr>
END
	if ($pcCanViewAll) {
		print <<END;
  <tr><td colspan=2><b>Special instructions</b></td></tr> 
  <tr><td colspan=2><p>At this phase of the review, you can see all submissions and comment on them. Please look at the problematic papers, and at papers that do not have any reviews yet.</p>
	<p>We want to complete the reviews by $config->{"shepherding_decisions_date"}.</p>
  </td></tr>
END
	}

	print <<END;
<tr><td colspan=2><b>Legend</b></td></tr>
<tr><td>N*</td><td>Indicates that you have reviewed paper N</td></tr>
<tr><td valign="top"><table border=1 cellpadding=0 cellspacing=0><tr><td bgcolor=yellow height=10 width=10></td>
<td bgcolor=lightgreen height=10 width=10></td></tr></table></td><td>Traffic light summarizes the current review decisions for a paper<br/>(red: reject, yellow: accepted for writing group, green: accepted for writer's workshop)</td></tr>
END

	# TODO: refactor code below that generates table rows to eliminate duplication
	if (scalar @shepherdForPaper > 0) {
		print <<END;
<tr><td height="10"></td></tr>
<tr><td colspan=2><h3>Shepherd</h3></td></tr>
END
		foreach $reference (@shepherdForPaper) {
			my $label = $labels{$reference};
			my $date = getDate($label);
			my $record = $records{$label};
			my $authors = $record->param("authors");
			my $title = $record->param("title");
			my $token = Access::token($label);
			my $status = "";	 # "" or "disabled"
			my $trafficLights = Decision::trafficLights($reference);
			my $voted = Decision::userVote($votes, $user, $reference) ? "*" : "";
			print <<END;
<tr>
	<td valign="top"><a href="?token=$token&action=download&label=$label" target=_blank>$reference</a>$voted</td>
	<td valign="top">$title <font size="-2" color="grey">$date</font></td>
	<td valign="top" width="40">$trafficLights</td>
	<td valign="top"><form method="post" target="_blank">
		<input type="hidden" name="action" value="vote"/>
		<input type="hidden" name="session" value="$session"/>
		<input type="hidden" name="reference" value="$reference"/>
		<input type="hidden" name="authors" value="$authors"/>
		<input type="hidden" name="title" value="$title"/>
		<input type="hidden" name="review_role" value="Shepherd"/>
		<input type="submit" value="Vote" 
			style="position:relative" $status/>
		</form>
	</td>
</tr>
END
		}
	}
		
	if (scalar @pcForPaper > 0) {
		print <<END;
<tr><td height="10"></td></tr>
<tr><td colspan=2><h3>PC</h3></td></tr>
END
		foreach $reference (@pcForPaper) {
			my $label = $labels{$reference};
			my $date = getDate($label);
			my $record = $records{$label};
			my $authors = $record->param("authors");
			my $title = $record->param("title");
			my $token = Access::token($label);
			my $status = "";	 # "" or "disabled"
			my $trafficLights = Decision::trafficLights($reference);
			my $voted = Decision::userVote($votes, $user, $reference) ? "*" : "";
#			my $reviews = ($role eq "admin" || $role eq "pc" && $pcCanViewAll) ? 
#				reviewsForPaper($reference) : "";
			my $reviews = reviewsForPaper($reference);
			print <<END;
<tr>
	<td valign="top"><a href="?token=$token&action=download&label=$label" target=_blank>$reference</a>$voted</td>
	<td valign="top">$title <font size="-2" color="grey">$date</font></td>
	<td valign="top" width="40">$trafficLights</td>
	<td valign="top"><form method="post" target="_blank">
		<input type="hidden" name="action" value="vote"/>
		<input type="hidden" name="session" value="$session"/>
		<input type="hidden" name="reference" value="$reference"/>
		<input type="hidden" name="authors" value="$authors"/>
		<input type="hidden" name="review_role" value="PC"/>
		<input type="hidden" name="title" value="$title"/>
		<input type="submit" value="Vote" 
			style="position:relative" $status/>
		</form>
	</td>
</tr>
END
			# TODO: does this mean that shepherds cannot see reviews?
#			if ($role eq "admin" || $role eq "pc" && $pcCanViewAll) {
				print <<END;
<tr>
	<td/>
	<td>$reviews</td>
</tr>
END
#			}
		}
	}
	
	# TODO: same for chairs
	# TODO: same for initial PC members (but remove the papers that were rejected)
	# These can be combined, since the screening assignment lists all papers assigned
	# to a reviewer, including if the reviewer is a chair
	
	if (scalar @initialPcForPaper > 0) {
		print <<END;
<tr><td height="10"></td></tr>
<tr><td colspan=2><h3>Initial PC</h3></td></tr>
END
		foreach $reference (@initialPcForPaper) {
			my $label = $labels{$reference};
			my $date = getDate($label);
			my $record = $records{$label};
			if ($record->param("track") eq $FOCUS_GROUP_TRACK) {
				next;  # skip focus group submissions
			}
			my $authors = $record->param("authors");
			my $title = $record->param("title");
			my $token = Access::token($label);
			my $status = "";	 # "" or "disabled"
			my $trafficLights = Decision::trafficLights($reference);
			my $voted = Decision::userVote($votes, $user, $reference) ? "*" : "";
#			my $reviews = ($role eq "admin" || $role eq "pc" && $pcCanViewAll) ? 
#				reviewsForPaper($reference) : "";
			my $reviews = reviewsForPaper($reference);
			print <<END;
<tr>
	<td valign="top"><a href="?token=$token&action=download&label=$label" target=_blank>$reference</a>$voted</td>
	<td valign="top">$title <font size="-2" color="grey">$date</font></td>
	<td valign="top" width="40">$trafficLights</td>
	<td valign="top"><form method="post" target="_blank">
		<input type="hidden" name="action" value="vote"/>
		<input type="hidden" name="session" value="$session"/>
		<input type="hidden" name="reference" value="$reference"/>
		<input type="hidden" name="authors" value="$authors"/>
		<input type="hidden" name="review_role" value="Other PC"/>
		<input type="hidden" name="title" value="$title"/>
		<input type="submit" value="Vote" 
			style="position:relative" $status/>
		</form>
	</td>
</tr>
END
			# TODO: does this mean that shepherds cannot see reviews?
#			if ($role eq "admin" || $role eq "pc" && $pcCanViewAll) {
				print <<END;
<tr>
	<td/>
	<td>$reviews</td>
</tr>
END
#			}
		}
	}
	
	print "</table>\n";

	Format::createFooter();
}

sub handleVote {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired ($session, $sessionInfo). Please sign in first.");
		
	my ($user, $role) = $sessionInfo =~ /:(.+?):(.+)/;	
	Assert::assertTrue($user && $role, 
		"Session expired ($session, $sessionInfo). Please sign in first.");
	Assert::assertTrue($role eq "shepherd" || $role eq "pc" || $role eq "admin",
		"Only shepherds, PC members, and shepherds can perform this action.");

	my $reference = $q->param("reference");
	Format::createHeader("Vote", "Enter your decision on paper $reference", "js/validate.js", 1);	
	
	# TODO: show form to enter vote
	
	Format::startForm("post", "vote_submitted", "return checkVoteForm()");
	Format::createHidden("session", $q->param("session"));
	Format::createHidden("reference", $reference);
	Format::createHidden("review_role", $q->param("review_role"));
	
	my $authors = $q->param("authors");
	my $title = $q->param("title");
	
	my $reviews = Decision::getReviews($reference);
	my @reviewers = keys %$reviews;
	print <<END;
<h3>Submission</h3>
<dd>$authors<br/>
<b>$title</b></dd>

<h3>Reviews</h3>
<dd><p>All reviews that have been submitted</p></dd>
<dd><p><em>Note: "PC" is the vote by the supervising PC member, "Other PC" is the vote by another PC member</em>
<dd>
<table border="0" cellpadding="0">
END
	if ($#reviewers < 0) {
		print <<END;
	<tr><td>No reviews available</td></tr>
END
	}
	my $i = 1;
	my $j = $i-1;
	foreach $reviewer (@reviewers) {
		my $review = $reviews->{$reviewer};
		my $reviewRole = $review->{"review_role"};
		my $vote = $review->{"vote"};
		my $decision = voteDecisionToText($vote);
		print <<END;
	<tr>
		<td width="100" valign="top">$reviewRole:<br/>
END
		print <<END;
			<a href="mailto:$user">$reviewers[$j]</a>
END
		print <<END;
		</td>
		<td width="30">&nbsp;</td>
		<td valign="top"><b>$decision</b><br/>
		$review->{"reason"}<br/><br/></td>
	</tr>
END
		$i++;
		$j++;
	}
	print <<END;
	<tr><td colspan=3><hr/></td></tr>
</table>
</dd>
END
	
	Format::createRadioButtonsWithTitleOnOneLine("Your assessment", 
		"Please enter or update your assessment", "vote",
		"-1", "not assessed",
		"0", "reject",
		"1", "accept for writing group",
		"2", "accept for writer's workshop",
		"-1");
	Format::createTextBoxWithTitle("Reason", 
		"Please comment on the following: " .
		"Has the paper improved during shephering? " .
		"Has the author been responsive and open to shepherding? " .
		"Is this paper in a state which will benefit from a writers workshop?", 
		"reason", 60, 10);

	# TODO: should do something else than go to sign-in (eg close the window)

	Format::endForm("Vote");		
	print <<END;
<form>
<p><a href="javascript:window.close();">Close without submitting a vote</a></p>
</form> 
END
	Format::createFooter();
}

sub handleVoteSubmitted {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired. Please sign in first.");
		
	my ($user, $role) = $sessionInfo =~ /:(.+?):(.+)/;	
	Assert::assertTrue($user && $role, 
		"Session expired. Please sign in first.");

	my $vote = $q->param("vote");
	# -1: not assessed
	#  0: reject
	#  1: accept for writing group
	#  2: accept for writer's workshop
	Assert::assertTrue($vote >= -1 && $vote <= 2,
		"Oops, you forgot to enter a vote. Please go back to the review form.");
	
	Format::createHeader("Vote has been submitted", "Thank you", "js/validate.js", 1);
	Decision::saveVote($timestamp, $user, $q->param("review_role"),
		$q->param("reference"), $q->param("vote"), $q->param("reason"));
	my $reference = $q->param("reference");
	my $decision = voteDecisionToText($vote);
	my $reason = $q->param("reason");
	print <<END;
Thank you entering your review for paper $reference. Here is what we have recorded for you:
<dd><pre>
Reference: $reference
Vote: $decision
Reason: $reason
</pre>
</dd>
You can review and update your assessement from the shepherding site.

<form>
<p><input type=button value="Close" 
	onClick="javascript:window.close();"></p>
</form> 
END
	Format::createFooter();	
}

# TODO: not used -- moved to separate script (notify?)
sub handleStatus {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired. Please sign in first.");
		
	my $role = Review::authenticate($q->param("email"), $q->param("password"));
	unless ($role) {
		 	Audit::handleError("Please check that you entered the correct user name and password",
		 		0, "shepherd.cgi");
	}
	$q->param( "name" => Review::getReviewerName($q->param("email")) );
	Session::setUser($q->param("session"), $q->param("email"), $role);

	my $reference = $q->param("reference");
	Format::createHeader("Status", "Status of the reviews", "js/validate.js");	
	
	print <<END;
	<table>
		<tbody>
END
	# TODO: show list of papers and their review status
	my $currentTrack = -1;
	my %records = Records::getAllRecords(Records::listCurrent());
	foreach $label (sort { $records{$a}->param("track") . "_" . $records{$a}->param("reference") cmp 
		$records{$b}->param("track") . "_" . $records{$b}->param("reference") } keys %records) {
		my $record = $records{$label};
		my $reference = $record->param("reference");
		unless (Shepherd::status($reference) eq "reject" ||
        	$record->param("track") eq $FOCUS_GROUP_TRACK) {  
      		my $authors = Review::getAuthors($record);
			$authors =~ s|\r\n|, |g;

			my $contact_name = $record->param("contact_name");
			my $email = $record->param("contact_email");
			
			my $title = $record->param("title");
			my $fileName = $record->param("file_name");
			$fileName =~ s/\.\w+$//;
			
			my $track = $record->param("track");
			if ($currentTrack != $track) {
				# Format::createFreetext("<h3>" . $config->{"track_" . $track} . "</h3>");
				print <<END;
			<tr>
				<td colspan="4">
					<h3>$config->{"track_$track"}</h3>
				</td>
			</tr>
END
				$currentTrack = $track;
			}
			
			my $token = uri_escape(Access::token($label));
			my $tags = Review::getTags($record);
						
			print <<END;
		<tr>
			<td valign="top" width="3%" align="center">
			</td>
			<td valign="top" align="right" width="3%">
				<a href="?token=$token&action=download&label=$label">$reference</a>
			</td>
			<td valign="top" width="70%">
			 	$authors<!-- <br/>
			 	<a href="mailto:$email">$email</a> -->
			 	<br/>$title
			</td>
END

			# DONE: show shepherd and PC for papers that have been assigned
			if (Shepherd::status($reference) eq "assigned") {
				my %assignment = Shepherd::assignedTo($reference);
				my $pc_email = $assignment{"pc"};
				my $pc_name = Review::getReviewerName($pc_email);
				my $shepherd_email = $assignment{"shepherd"};
				my $shepherd_name = Review::getReviewerName($shepherd_email);
				print <<END;
			<td valign="top">
				PC member: <a href="mailto:$pc_email">$pc_name</a><br/>
				Shepherd: <a href="mailto:$shepherd_email">$shepherd_name</a>
			</td>
END

			print <<END;
		</tr>
END
			}
			

		}
	} 
	
	print <<END;
			</tbody>
	</table>
END
	
	Format::createFooter();
}

# need this as a proxy for modules that refer ::handleError
sub handleError {
	Audit::handleError(@_, 1);
}

# Utilities

sub checkCredentials {
	my $session = $q->param("session");
	Assert::assertTrue(Session::check($session), 
		"Session expired. Please sign in first.");
	my ($user, $role) = Session::getUserRole($q->param("session"));	
	Assert::assertTrue($user, "You are not logged in");
	Assert::assertTrue($role eq "shepherd" || $role eq "chair" || $role eq "pc" || $role eq "admin", 
		"You are not allowed to access this site");
	return $session;
}

sub showSharedMenu {
	my ($session) = @_;
	
	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END
}


# Mails

# MAIL 1
# Confirmation to shepherds
sub sendConfirmationOfSherpherdingBid {
	my ($email, $firstName, $papers) = @_;

	# DONE: send email to bidder with bids and password
	my $tmpFileName = Email::tmpFileName($timestamp, $firstName);
	open (MAIL, ">$tmpFileName");
	print MAIL <<END;
Dear $firstName,

thanks for volunteering as a shepherd for the following papers:

END

	foreach (sort split(/\n/, $papers)) {
		my ($priority, $reference, $timestamp) = split(/, /);
		my $record = Records::getRecord($timestamp . "_" . $reference);
		my $title = $record->param("title");
		print MAIL "\t$priority\t$title\n";
	}

	my $password = Review::getPassword($email);
	
	my $newAccountMessage = $newAccountCreated ? "We have created a new account for you. The user name is your email address and the password is \"$password\". If selected as a shepherd, you need this account to submit your shepherding recommendations." : "";
	
	print MAIL <<END;
	
Legend:
\t1\tI would like to shepherd this paper
\t2\tI could be convinced to shepherd this paper
\t3\tI am willing to shepherd this paper, but only if nobody else does
			
Your bid has been sent to the $CONFERENCE $PROGRAM_CHAIR_TITLE who will confirm them as soon as possible. 

Please keep in mind that there may be more then one volunteer for a specific paper. This is the reason why we cannot start shepherding immediately.


$newAccountMessage

Thanks for being patient,

$config->{"program_chair"}
$CONFERENCE $PROGRAM_CHAIR_TITLE
END
	close (MAIL);
	
	my $status = Email::send($email, "",
		"[$CONFERENCE] Shepherding bid confirmation", $tmpFileName);
	if ($config->{"debug"}) {
		print "Email: <pre>$status</pre>";
	} 
}

# MAIL 2
# Reminder to $PROGRAM_CHAIR_TITLE
sub notifyShepherdingBid {
	my ($shepherd, $email, $papers) = @_;
	my $tmpFileName = Email::tmpFileName($timestamp, "Allan");
	open (MAIL, ">$tmpFileName");
	print MAIL <<END;
Shepherd: $shepherd ($email)
END
	foreach (split(/\n/, $papers)) {
		my ($priority, $reference, $timestamp) = split(/, /);
		my $label = "${timestamp}_${reference}";
		# DONE: generate token that is different from the download token
		my $token = uri_escape(Access::token($email . "_" . $label));
		my ($reference) = $label =~ /_(\d+)$/;

		my  $reflectUrl = $config->{"reflect_url"} || $config->{"url"};
		print MAIL <<END;
		
Paper: $reference
Priority: $priority
Accept: $reflectUrl/shepherd.cgi?action=accept&email=$email&label=$label&token=$token
END
	}
	print MAIL <<END;
	
Click on the corresponding link to accept a bid. You will be asked to confirm, before the action takes effect.
END
	close (MAIL);
	
	my $chair_email = $config->{"program_chair_email"};
	my $status = Email::send($chair_email, "",
		"[$CONFERENCE] New shepherding bid", $tmpFileName);
	if ($config->{"debug"}) {
		print "Email: <pre>$status</pre>";
	} 
}

# MAIL 3
# To shepherd after reject
# NOTE: was not used during EuroPLoP 2008
sub rejectBid {
	my ($shepherd_email, $shepherd_name, $label) = @_;
	
	# DONE: lookup name of shepherd
	my $shepherd_name = Review::getReviewerName($shepherd_email);
	
	my $record = Records::getRecord($label);
	my $authors = Review::getAuthors($record);
	my $title = $record->param("title");
	my $reference = $record->param("reference");
	my %assignment = Shepherd::assignedTo($reference);
	
	my $assigned_shepherd_name = Review::getReviewerName($assignment{"shepherd"});
	my ($firstName) = $shepherd_name =~ /^(\w+)/;
	
	my $tmpFileName = Email::tmpFileName($timestamp, $firstName);
	open (MAIL, ">$tmpFileName");
	print MAIL <<END;
Dear $firstName,

thanks for volunteering as a shepherd for:

($reference)\t$authors
\t$title

The paper had more than one volunteering shepherd. After carefully balancing all forces, we decided to let $assigned_shepherd_name shepherd this paper.

If you have provided multiple preferences, we will try to assign one of the other papers to you. Otherwise, if you still have free shepherding capacities, we'd be happy to offer you one of the open papers:

$baseUrl/$script

Thanks again,

$config->{"program_chair"}
$CONFERENCE $PROGRAM_CHAIR_TITLE
END
	close (MAIL);
	
 	my $status = Email::send($shepherd_email, "",
		"[$CONFERENCE] Paper not available for shepherding", $tmpFileName);
	if ($config->{"debug"}) {
		print "Email: <pre>$status</pre>";
	} 
}

# MAIL 4
# To shepherd after accept
sub confirmBid {
	my ($shepherd_email, $shepherd_name, $label, $pc_email, $pc_name) = @_;
	
	# DONE: lookup name of shepherd
	my $shepherd_name = Review::getReviewerName($shepherd_email);

	my $record = Records::getRecord($label);
	my $authors = Review::getAuthors($record);
	my $title = $record->param("title");
	my $sheep_email = $record->param("contact_email");
	my $reference = $record->param("reference");
	
	my ($firstName) = $shepherd_name =~ /^(\w+)/;

	my $tmpFileName = Email::tmpFileName($timestamp, $firstName);
	open (MAIL, ">$tmpFileName");
	print MAIL <<END;
Dear $firstName,

we are happy to have you as a shepherd for:

$reference\t$authors
\t$title

As a next step, you should get in touch with your sheep ($sheep_email). Your assigned PC member is $pc_name ($pc_email). Please keep him/her in the loop in all communication with the sheep.

Thanks again,

$config->{"program_chair"}
$CONFERENCE $PROGRAM_CHAIR_TITLE
END
	close (MAIL);

	my $status = Email::send($shepherd_email, "$pc_email", 
		"[$CONFERENCE] Paper assigned for shepherding", $tmpFileName);
	if ($config->{"debug"}) {
		print "Email: <pre>$status</pre>";
	} 
}

# MAIL 5
# To sheep after accept
sub introduceSheepToShepherd {
	my ($shepherd_email, $shepherd_name, $label, $pc_email, $pc_name) = @_;
	
	my $record = Records::getRecord($label);
	my $authors = Review::getAuthors($record);
	my $title = $record->param("title");
	my $sheep_email = $record->param("contact_email");
	my $sheep_name = $record->param("contact_name");
	my $reference = $record->param("reference");
	
	my ($firstName) = $sheep_name =~ /^([^\s]+)/;
	my $password = getSubmitPassword($reference);
	
	my $tmpFileName = Email::tmpFileName($timestamp, $firstName);
	open (MAIL, ">$tmpFileName");
	print MAIL <<END;
Dear $firstName,

we are happy to inform you that your paper has been accepted for shepherding. We have assigned $shepherd_name ($shepherd_email) as a shepherd for your paper. During the next weeks, you will interact closely with your shepherd. He/she will read your paper, provide comments, ask questions, offer suggestions for improvement, ...

$pc_name ($pc_email) from the $CONFERENCE Programme Committee will observe your interaction with the shepherd. He/she can act as a third voice whenever you or your shepherd feel that there's a problem in the process. The PC member will also be one of the final reviewers for your paper. Please keep the PC member in the loop by cc-ing him/her to all mails exchanged with the shepherd.

As a reaction to the shepherd's comments, you will usually create a new version of your paper. Please ensure that you upload this new version to the $CONFERENCE submission system. Here's the access info again:

Reference: $reference
Password: $password

Please work hard with your shepherd to create the best possible quality until the final review due date, which is $config->{"second_draft_due_date"}.

$config->{"program_chair"}
$CONFERENCE $PROGRAM_CHAIR_TITLE
END
	close (MAIL);
	
	# TODO: send to sheep, and cc to shepherd and pc member
	my $status = Email::send($sheep_email, "$shepherd_email,$pc_email",
		"[$CONFERENCE] Paper accepted for shepherding", $tmpFileName);
	if ($config->{"debug"}) {
		print "Email: <pre>$status</pre>";
	} 
}


# Utilities

sub showReviewersOfPaper {
	my ($reference) = @_;
	print <<END;
<select name="pc_email"/>
END
	my @reviewers = Review::getProgramCommitteeMembers();
	my %isInitialReviewer = map { $_ => 1 } Review::getReviewersForPaper($reference);
	my %load = Shepherd::papersAssignedToSupervise();
	foreach $pc (@reviewers) {
		my $load = $load{$pc} || 0;
		if ($isInitialReviewer{$pc}) {
			print <<END;
	<option value="$pc">* $pc ($load)</option>
END
		} else {
			print <<END;
	<option value="$pc">$pc ($load)</option>
END
		}
	}	
	print <<END;
</select>	
END
}

sub getSubmitPassword {
	my ($reference) = @_;
	my $password = "";
	open (PASSWORD, "data/password.dat") ||
		handleError("Internal: could not check login");
	flock(PASSWORD, $LOCK);
	while (<PASSWORD>) {
		if (/^$reference, (\w+)/) {
			$password = $1; 
			break;
		}
	}
	flock(PASSWORD, $UNLOCK);
	close (PASSWORD);
	return $password;
}

sub showSavedBid {
	my ($preferences, $user, $reference) = @_;
	my $priority = $preferences->{$user}->{$reference}->{"priority"};
	if ($priority) {
		print "<font color=green>$priority</font>";
	} 
}

sub showBids {
	my ($reference) = @_;
	my $preferences = Shepherd::preferences();
	my @bids = keys %{$preferences->{$reference}};
	print "<h3>All bids for this paper</h3>";
	print "<p>The following table shows all bids with priority, bidder, and number of papers already assigned to the bidder:</p>\n";
	print "<p><table border=1 cellpadding=5>\n";
	print "<tr><th>Priority</th><th align=\"left\">Bidder</th><th>Number of papers</th></tr>\n";
	my %load = Shepherd::papersAssigned();
	foreach $bid (sort { $a->{"priority"} <=> $b->{"priority"} } @bids) {
		my $bidder = Review::getReviewerName($bid);
		my $priority = $preferences->{$reference}->{$bid}->{"priority"};
		my $load = $load{$bid} || 0;	# $bid is bidder's id
		print "<tr><td>$priority</td><td>$bidder</td><td>$load</td></tr>\n";
	}
	print "</table></p>\n";
}

sub voteDecisionToText {
	my ($vote) = @_;
	if ($vote eq "-1") {
		return "not assessed";
	} elsif ($vote eq "0") {
		return "reject";
	} elsif ($vote eq "1") {
		return "accept for writing group";
	} elsif ($vote eq "2") {
		return "accept for writer's workshop";
	} 
}

sub copyWithoutElements {
	my ($elem, @list) = @_;
	my @copyOfList;
	foreach $nextElem (@list) {
		unless ($nextElem eq $elem) {
			push (@copyOfList, $nextElem);
		}
	}
	return @copyOfList;
}

sub reviewsForPaper {
	my ($reference) = @_;
	my $reviews = Decision::getReviews($reference);
	my @reviewers = keys %$reviews;
	my $text = <<END;
<table border="0" cellpadding="0" width="100%" bgcolor="lightgrey">
END
	if ($#reviewers < 0) {
		$text .= <<END;
	<tr><td></td></tr>
END
	}
	my $i = 1;
	my $j = $i-1;
	foreach $reviewer (@reviewers) {
		my $review = $reviews->{$reviewer};
		my $reviewRole = $review->{"review_role"};
		my $vote = $review->{"vote"};
		my $decision = voteDecisionToText($vote);
		$text .= <<END;
	<tr>
		<td width="175" valign="top">$reviewRole:<br/>
END
		$text .= <<END;
			<a href="mailto:$user">$reviewers[$j]</a>
END
		$text .= <<END;
		</td>
		<td width="30">&nbsp;</td>
		<td valign="top"><b>$decision</b><br/>
		$review->{"reason"}<br/><br/></td>
	</tr>
END
		$i++;
		$j++;
	}
	$text .= <<END;
</table>
</dd>
END
	return $text;
}

sub getDate {
	my ($label) = @_;
	if ($label =~ /^(\d+)_(\d+)$/) {
		my $reference = $2;
		my $time = localtime($1);
		return $time;
		# TODO: single-digit days are not matched correctly
		# my ($dayOfWeek, $month, $day, $h, $m, $s, $year) =
		#	$time =~ /(\w+) (\w+) (\d+) (\d+):(\d+):(\d+) (\d+)/;
		# return "$month $day, $year";
	} else {
		return "no date";
	}
}

# TODO: refactor into library
# same code as used in schedule.cgi
sub lastUpdated {
	my ($reference) = @_;
	my $cutoff = timelocal(0, 0, 0, 10, 5-1, 2008);		# May 9, 2008
	my $time = lastUpdatedAtTime($reference);
	my $date = lastUpdatedOnDate($reference);
	if ($time < $cutoff) {
		return "<font color=red>$date</font>";
	} 
	return $date;
}

sub lastUpdatedAtTime {
	my ($reference) = @_;
	my ($time) = $labels{$reference} =~ /^(\d+)_/;
	return $time; 
}

sub lastUpdatedOnDate {
	my ($reference) = @_;
	my ($time) = $labels{$reference} =~ /^(\d+)_/;
	my $lastUpdated = localtime($time);
	my ($date) = $lastUpdated =~ /^\w+ (\w+\s+\d+)/;
	return $date; 
}

# Main dispatcher

my $action = $q->param("action") || "sign_in";
Format::sanitizeInput();
Audit::trace($action);
if ($action eq "sign_in") {
	handleSignIn();
} elsif ($action eq "submissions") {
	handleSubmissions();
} elsif ($action eq "selection") {
	handleSelection();
} elsif ($action eq "download") {
	handleDownload();
} elsif ($action eq "accept") {
	handleAccept();
} elsif ($action eq "reject") {
	handleReject();
} elsif ($action eq "accept_confirmed") {
	handleAcceptConfirmed();
} elsif ($action eq "reject_confirmed") {
	handleRejectConfirmed();
} elsif ($action eq "assignments") {
	handleAssignments();
} elsif ($action eq "shepherded_papers") {
	handleShepherdedPapers();
} elsif ($action eq "vote") {
	handleVote();
} elsif ($action eq "vote_submitted") {
	handleVoteSubmitted();
} elsif ($action eq "status") {
	handleStatus();
} else {
	Audit::handleError("No such action");
}