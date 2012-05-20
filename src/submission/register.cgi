#!/usr/bin/perl -wT
use CGI;
use CGI::Carp qw( fatalsToBrowser );
use URI::Escape ('uri_escape');

our $debug = 0;

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
use Core::Audit;
use Core::Register;
use Core::User;
use Core::Contact;

our $q = new CGI;
our $timestamp = time();

our $script = "register";

our $mode = "register";

our $config = Serialize::getConfig();

our $WEBCHAIR = $config->{"web_chair"};
our $WEBCHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $CONFERENCE_ID = $config->{"conference_id"};
our $CONFERENCE_WEBSITE = $config->{"conference_website"};
our $CONFERENCE_CHAIR = $config->{"conference_chair"};
our $baseUrl = $config->{"url"};

$Format::TEMPLATE = "data/html/header_registration.html";

BEGIN {
	CGI::Carp::set_message( \&Audit::handleUnexpectedError );
}


# Handlers

sub handleSignIn {
	Format::createHeader("Registration > Sign in", "", "js/validate.js");
		
	Format::startForm("post", $mode, "return checkRegistrationForm(this)", "");
	Format::createHidden("session", Session::create(Session::uniqueId(), $timestamp));

	if ($config->{"registration_closed"}) {
		Format::createFreetext("<font color=red><b>Sorry, but registration for $CONFERENCE is now closed.</b></font>");
		Format::createFooter();
		return;
	}
	
	# TODO: disable participant log in, if registration is not yet open
	
	print <<END;
<p>Welcome to the registration page for $CONFERENCE. When you register, an account will be created that allows you to update your registration. Note for authors, shepherds, and PC members: this will be your existing account.</p> 

<p>The early registration fee is $config->{"early_registration_fee"} euro. After  $config->{"early_registration_date"}, the fee will be $config->{"late_registration_fee"} euro. A reduced fee applies to accompanying participants and children. Please <a href="mailto:hotel\@kloster-irsee.de?subject=EuroPLoP%202011">contact Kloster Irsee</a> directly for special arrangements.</p>

<table cellspacing="0" cellpadding="0">
	<tr height="5"></tr>
	<tr>
		<td valign="top"><input name="status" type="radio" value="new" checked/></td>
		<td width="5"></td>
		<td valign="top">
			<table cellpadding="0" cellspacing="0">
				<tr>
					<td>New registration</td>
				</tr>
			</table>
		</td>
	</tr>
	<tr>
		<td height="5"></td>
	</tr>
	<tr>
		<td valign="top"><input name="status" type="radio" value = "existing"/></td>
		<td width="5"></td>
		<td valign="top">
			<table cellpadding="0" cellspacing="0">
				<tr>
					<td>No, my email address is:</td>
					<td width="10"></td>
					<td><input name="email" type="text"/></td>
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

	Format::endForm("Sign in");
	Format::createFooter();
}


sub handleRegistration {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired. Please sign in first.");

	# DONE: retrieve saved state only when user is properly logged in
	# otherwise they could access a profile with email only
	my $q_saved = new CGI();
			
	my $role;
	# DONE: augmented to use password if one is supplied in order to prevent unintended
	# registration as a new participant
	# TODO: should really change radio button when password is entered using a script
	# TODO: what I should really do, however, is not to rely on the user providing the correct
	# input ("new" choice), but check whether such a user already exists in
	# the database
	if ($q->param("status") eq "new" && !$q->param("password")) {
		$role = "participant";
	} else {
		my $author = checkAuthorPassword($q->param("email"), $q->param("password")); 
		my $reviewer = checkReviewerPassword($q->param("email"), $q->param("password"));
		$role = $author ? $author : $reviewer;
		unless ($role) {
		 	Audit::handleError("Please check that you entered the correct user name and password",
		 		0, "$script.cgi");
		}
		$q->param( "name" => Register::getName($q->param("email")) );
		Register::loadRegistration($q->param("email"), $q_saved);
	}
	Session::setUser($q->param("session"), $q->param("email"), $role);
		
	# DONE: only in test version
	if ($debug) {
		# Format::createFreetext("You are logged on as <b>$role</b>");
	}
	
	Format::createHeader("Registration", "Registration", "js/validate.js", 1);	
	
	Format::createFreetext("Mandatory entries are indicated with a (*).");
	
	Format::startForm("post", "registration_submitted", "return checkRegistrationForm(this)");
	Format::createHidden("session", $q->param("session"));
	
	Format::createTextWithTitle("Personal information", 
		"Full name *", "name", 60, $q_saved->param("name") || $q->param("name"));
	Format::createTextWithTitle("", 
		"Affiliation", "affiliation", 60, $q_saved->param("affiliation"));

	# DONE: ask for street, city, state, zip or postal code, country
	Format::createTextWithTitle("", 
		"Address Line 1", "address_line_1", 60, $q_saved->param("address_line_1"));
	Format::createTextWithTitle("", 
		"Address Line 2", "address_line_2", 60, $q_saved->param("address_line_2"));
	Format::createTextWithTitle("", 
		"City", "city", 60, $q_saved->param("city"));
	Format::createTextWithTitle("", 
		"State/Province/Region", "state", 60, $q_saved->param("state"));
	Format::createTextWithTitle("", 
		"Postal code/ZIP", "postal_code", 60, $q_saved->param("postal_code"));
	Format::createTextWithTitle("", 
		"Country *", "country", 60, $q_saved->param("country"));

	Format::createTextWithTitle("", 
		"Email *", "email", 60, $q_saved->param("email") || $q->param("email"));
	Format::createTextWithTitle("",
		"Phone", "phone", 60, $q_saved->param("phone"));

	Format::createRadioButtonsWithTitleOnOneLine("", 
		"Gender *", "gender",
		"male", "Male",
		"female", "Female",
		$q_saved->param("gender"));
			
	Format::createTextAreaWithTitle("", 
		"Alternative billing address for invoice", "billing_address", 50, 6, $q_saved->param("billing_address"));

	Format::createRadioButtonsWithTitleOnOneLine("Registration information", 
		"Author", "author",
		"yes", "Yes",
		"no", "No",
		$q_saved->param("author") || "no");
	Format::createRadioButtonsWithTitleOnOneLine("", 
		"Focus group leader", "focus_group_leader",
		"yes", "Yes",
		"no", "No",
		$q_saved->param("focus_group_leader") || "no");	
		
	Format::createRadioButtonsWithTitleOnOneLine("", 
		"Room", "room",
		"single", "Single",
		"double", "Double",
		$q_saved->param("room") || "single");	
		
	# TODO: add info that by sharing a room you save 60 Euros
	Format::createTextWithTitle("", 
		"If double room, who is your room mate? *", "room_mate", 60,
		$q_saved->param("room_mate"));	

	# DONE: total number of participants (using drop box)
	Format::createMenuWithTitle("", 
		"Total number of participants", "participants",
		"1", "1",
		"2", "2",
		"3", "3",
		"4", "4",
		"5", "5",
		"6", "6",
		"7", "7",
		"8", "8",
		"9", "9",
		$q_saved->param("participants") || "1");
	
	# DONE: of which how many are children
	Format::createMenuWithTitle("", 
		"Number of children under six", "children",
		"0", "0",
		"1", "1",
		"2", "2",
		"3", "3",
		"4", "4",
		"5", "5",
		"6", "6",
		"7", "7",
		"8", "8",
		"9", "9",
		$q_saved->param("children") || "0");
		
	# DONE: number of people who prefer vegetarian food 
	Format::createMenuWithTitle("", 
		"Number of people who prefer vegetarian food", "vegetarian",
		"0", "0",
		"1", "1",
		"2", "2",
		"3", "3",
		"4", "4",
		"5", "5",
		"6", "6",
		"7", "7",
		"8", "8",
		"9", "9",
		$q_saved->param("vegetarian") || "0");
		
	# TODO: get actual fee from Allan
	# TODO: make date of early bird configurable
	my $rate = $config->{"early_registration_open"} ? 
		$config->{"early_registration_fee"} : $config->{"late_registration_fee"};
	Format::createRadioButtonsWithTitleOnOneLine("", 
		"Fee (early registration ends on ". $config->{"early_registration_date"} . ")", "fee",
		$config->{"early_registration_fee"}, 
			$config->{"early_registration_fee"} . " Euro (early registration)",
		$config->{"late_registration_fee"}, 
			$config->{"late_registration_fee"} . " Euro (late registration)",
		$q_saved->param("fee") || $rate);

	# DONE: if George, automatically add two pillows
	my $comments;
	if ($q->param("email") =~ /georgeplatts/) {
		$comments = "Two pillows, please";
	}
	Format::createTextAreaWithTitle("", 
		"Anything else we should know?", "comments", 50, 6, 
		$q_saved->param("comments") || $comments);

	# Workshops
	# DONE: select workshop (A-E)
	# DONE: select focus group
		
	# DONE: credit card information
	Format::createTextWithTitle("Credit card information", 
		"<p><em>For security reasons, print out a copy of the next page, write in your credit card number including the verification code, and then fax it to Kloster Irsee. The FAX number can be found on the registration confirmation. Your registration will not be complete unless the FAX is received. Please ensure that the credit card is valid and that it covers the total payment. Do not enter your credit card number here.</em></p>" .
		"Name on credit card * &nbsp; (please <b>don't</b> enter your card number)", "name_on_card", 60, $q_saved->param("name_on_card"));
	Format::createRadioButtonsWithTitleOnOneLine("", 
		"Card type *", "card_type",
		"Visa", "Visa",
		"MasterCard", "MasterCard",
		"American Express", "American Express",
		$q_saved->param("card_type"));

	Format::createFreetext("Once you register, you will receive a confirmation email with this information.");

	Format::endForm("Register");
	
	Format::createFooter();
}


sub handleRegistrationSubmitted {
	my $session = $q->param("session");
	my $sessionInfo = Session::check($session);
	Assert::assertTrue($sessionInfo, 
		"Session expired. Please sign in first.");
			
#	my ($user, $role) = $sessionInfo =~ /:(.+?):(.+)/;	
#	Assert::assertTrue($user && $role, 
#		"Session expired. Please sign in first.");

	# DONE: save registration info
	# DONE: save in any case, even if the form was incomplete
	Register::saveRegistration($timestamp, $q);
	
	Assert::assertNotEmpty("name", "Oops. Please enter your name");
	Assert::assertNotEmpty("country", "Oops. Please enter your country");
	Assert::assertNotEmpty("email", "Oops. Please enter your email");
	Assert::assertNotEmpty("gender", "Oops. Please indicate your gender");
	if ($q->param("room") eq "double") {
		Assert::assertNotEmpty("room_mate", "You chose a double room. Please enter the name of a room mate");
	}
	Assert::assertNotEmpty("name_on_card", "Oops. We need the name on your credit card");
	Assert::assertNotEmpty("card_type", "Oops. Please choose the type of your card");
		
	my $fee = $q->param("fee");
	
	my $fullName = $q->param("name");
	my $address = $q->param("address_line_1");
	if ($q->param("address_line_2")) {
		$address .= ", " . $q->param("address_line_2");
	}
	my $cityAndState = $q->param("city") . ", " . 
		$q->param("state") . " " . $q->param("postal_code");
	my $country = $q->param("country");
	my $affiliation = $q->param("affiliation");
	my $phone = $q->param("phone");
	my $email = $q->param("email");		# should be same as $user?
	
	my $billing_address = $q->param("billing_address");
	$billing_address =~ s/\r\n/, /g;
	
	my $participants = $q->param("participants");
	my $children = $q->param("children");
	my $vegetarian = $q->param("vegetarian");
	
	my $nameOnCard = $q->param("name_on_card");
	my $cardType = $q->param("card_type");
	
	
	Format::createHeaderNoStyle("Registration Confirmation and Fax Form", 
		" ", "js/validate.js", 1);
	
	# DONE: only in test version
	if ($debug) {
		# Format::createFreetext("You are logged on as <b>$role</b>");
	}

	# DONE: move to newer form, with:
	# 1) billing address?
	# 2) Payment information in the credit card form
	# 3) Number of participants/children
	
	print <<END;
	<div align="center">
  <center>
  <table cellSpacing="10" cellPadding="10" width="600" border="10" style="border-collapse: collapse" bordercolor="#111111" height="764">
    <tr>
      <td height="265">To: Kloster Irsee <br>
      Schwäbisches Tagungs- und Bildungszentrum <br>
      Klosterring 4 <br>
      87660 Irsee <br>
          Fax: +49 / 8341 / 742-78
          <h1><font size="+2">$CONFERENCE<br>
            Registration and Credit-Card Payment</font></h1>
      <p>Be sure to enter your Credit Card Number before faxing.
          <p>Please accept my payment of <b>$fee Euro</b> per person as registration fee
            for $CONFERENCE (reductions may apply to accompanying participants and children).<br>
 </td>
    </tr>
    <tr>
      <td height="438"><center>
<table border="1" width=500 cellpadding="2" cellspacing="0" style="border-collapse: collapse" bordercolor="#111111">
<tr>
    <td align=left width=168><b> Full Name:</b></td>
                <td align=left width=332>$fullName</td>
</tr>
<tr>
    <td align=left width=168><b>Address:</b></td>
                <td align=left width=332>$address</td>
</tr>
<tr>
    <td align=left width=168><b>City, State &amp; Zipcode</b></td>
                <td align=left width=332>$cityAndState</td>
</tr>
<tr>
    <td align=left width=168><b>Country:</b></td>
                <td align=left width=332>$country</td>
</tr>
<tr>
    <td align=left width=168><b>Organization:</b></td>
                <td align=left width=332>$affiliation</td>
</tr>
<tr>
    <td align=left width=168><b>Billing Address:</b></td>
                <td align=left width=332>$billing_address</td>
</tr>
<tr>
    <td align=left width=168><b> Phone/Fax Number:</b></td>
                <td align=left width=332>$phone</td>
</tr>
<tr>
    <td align=left width=168><b> Email:</b></td>
                <td align=left width=332>$email</td>
</tr>
<tr>
    <td align=left width=168><b> Number of participants:</b></td>
                <td align=left width=332>$participants (incl. $children child/ren under six,  and $vegetarian vegetarian/s)</td>
</tr>
</table>
<br>
<table border="1" width=500 cellpadding="2" cellspacing="0" style="border-collapse: collapse" bordercolor="#111111" height="165">
<tr>
    <td align=left width=494 colspan="6" height="22"><b><font size="4">Credit Card
      Information
      </font></b></td>
</tr>
<tr>
    <td align=left width=104><b>Name on Card:</b></td>
                <td align=left colspan="5" width="420">$nameOnCard</td>
</tr>
<tr>
    <td align=left width=104><b>Credit Card Type:</b></td>
                <td align=left width="84">$cardType</td>
    <td align=left width=85> <b>Exp Date:</b> </td>
                <td align=left width="85">&nbsp; </td>
                <td align=left width=85> <b>Card Code:</b></td>            
                <td align=left width="85">&nbsp; </td>
</tr>
<tr>
    <td align=left width=104><b>Credit Card Number:</b></td>
    <td align=left colspan="5" width="420">&nbsp;</td>
</tr>
</table>
<p>&nbsp;</p>
<table cellSpacing="0" cols="2" cellPadding="0" width="500" border="0">
  <tr>
    <td><b>Date:</b></td>
    <td><b>Signature:</b></td>
  </tr>
</table>
      </center>
      </td>
    </tr>
  </table>
  </center>
</div>
<br/>

<!-- This script and many more are available free online at -->
<!-- The JavaScript Source!! http://javascript.internet.com -->

<script type="text/javascript">
if (window.print) {
	document.write('<center><form>'
	+ '<input type=button name=print value="Print" '
	+ 'onClick="javascript:window.print()"></form></center>');
}
</script>
END

	# TODO: send confirmation message with password (if new participant)
	# TODO: send registration message to Irsee, and the conference chairs
		
	# DONE: If new participant, create password and store it
	my $password = "";
	if ($role eq "participant" &&
		!Register::getParticipantPassword($user)) {
    	 $password = Password::generatePassword(6);
    	 Register::logParticipantPassword($user, $password);
    	 
    	 # DONE: use only during test
    	 if ($debug) {
    	 	Format::createFreetext("<hr/>Created new account with password: $password<hr/>");
    	 }
	}
	
	sendConfirmationOfRegistration($user, $fullName, $password);
	notifyRegistration($user, $fullName);

	# Format::createFooter();  
}


sub handleSendPcLogin {
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
		my $status = Review::sendPasswordForEmail($q->param("email"));
		if ($config->{"debug"}) {
			Format::createHeader("Password help", "", "");
			print "Email: <pre>$status</pre>";
			Format::createFooter();
		} else {
			handleSignIn();
		}

	}
}


# need this as a proxy for modules that refer ::handleError
sub handleError {
	Audit::handleError(@_, 1);
}


# Mails

# MAIL 0
# Send password for new accounts
sub NOT_USED_sendNewAccountInformation {
	my ($email, $name, $password) = @_;
	my ($firstName) = $name =~ /^(\w+)/;

	# DONE: send email to participant with and password
	my $tmpFileName = Email::tmpFileName($timestamp, $firstName);
	open (MAIL, ">$tmpFileName");
	print MAIL <<END;
We have created a new account for you. The user name is your mail address and the password is $password. You can log in and update your information any time.

Best regards,
Till Schümmer
Programme Chair of EuroPLoP 2008
END
	close (MAIL);
	
	# TODO: during initial test, don't actually send mail
	my $mail = Email::send($email, "",
		"[$CONFERENCE] New account", $tmpFileName);
	if ($debug) {
		print "<hr/><pre>$mail</pre>\n";
	}
}

# MAIL 1
# Confirmation to participants
sub sendConfirmationOfRegistration {
	my ($email, $name, $password) = @_;
	my ($firstName) = $name =~ /^(\w+)/;

	# DONE: send email to participant with registration info
	my $tmpFileName = Email::tmpFileName($timestamp, $firstName);
	open (MAIL, ">$tmpFileName");
	print MAIL <<END;
Dear $firstName,
thanks for registering for $CONFERENCE. Here is the information you submitted:

END

#	foreach $field (@Register::fields) {
#		print MAIL "\t$field=" . $q->param($field) , "\n";
#	}

	my $fee = $q->param("fee");
	
	my $fullName = $q->param("name");
	my $address = $q->param("address_line_1");
	if ($q->param("address_line_2")) {
		$address .= ", " . $q->param("address_line_2");
	}
	my $cityAndState = $q->param("city") . ", " . 
		$q->param("state") . " " . $q->param("postal_code");
	my $country = $q->param("country");
	my $affiliation = $q->param("affiliation");
	my $phone = $q->param("phone");
	my $email = $q->param("email");		# should be same as $user?
	
	my $billing_address = $q->param("billing_address");
	$billing_address =~ s/\r\n/, /g;
	
	my $author = $q->param("author");
	my $focus_group_leader = $q->param("focus_group_leader");
	
	my $room = $q->param("room");
	my $room_mate = $q->param("room_mate");
	
	my $participants = $q->param("participants");
	my $children = $q->param("children");
	my $vegetarian = $q->param("vegetarian");
	
	my $nameOnCard = $q->param("name_on_card");
	my $cardType = $q->param("card_type");

	print MAIL <<END;
$fullName
$affiliation
$address
$cityAndState
$country

$phone
$email

Alternative billing address: $billing_address

Author: $author
Focus group leader: $focus_group_leader

You booked a $room room for $participants adult(s) and $children child(ren).
END
	
	if ($room eq "double") {
		print MAIL <<END;
Room mate: $room_mate
END
	}
	
	print MAIL <<END;
We have registered vegetarian meals for $vegetarian participant(s).

Additional notes: $comments

You will pay by $cardType issued to $nameOnCard.

Total fee per person: $fee Euro (reductions may apply to accompanying participants and children: children 0-5 are free, children 6-14 pay a reduced fee)
END

	if ($password) {
		print MAIL <<END;
		
We have created a new account for you. The user name is your mail address and the password is $password. You can log in and update your information any time.
END
	}
	print MAIL <<END;

You can log in and update your information any time, if you need to make any corrections.

Don't forget to fax in your payment information.

Thanks,
$CONFERENCE_CHAIR
Conference Chair of $CONFERENCE
END
	close (MAIL);
	
	# TODO: during initial test, don't actually send mail
	my $mail = Email::send($email, "",
		"[$CONFERENCE] Registration confirmation", $tmpFileName);
	if ($debug) {
		print "<hr/><pre>$mail</pre>\n";
	}
}

# MAIL 2
# Reminder to conference chair
sub notifyRegistration {
	my ($email, $name) = @_;
	# TODO: get conference chair's name
	my $tmpFileName = Email::tmpFileName($timestamp, "Michael");
	open (MAIL, ">$tmpFileName");
		
	print MAIL <<END;
$name has just registered for $CONFERENCE. Here are the registration details: 
	
END

	my $time = localtime($timestamp);
	my ($dayOfWeek, $month, $day, $h, $m, $s, $year) =
	$time =~ /(\w+) (\w+) (\d+) (\d+):(\d+):(\d+) (\d+)/;
#	print MAIL "\tdate=$time\n";

#	foreach $field (@Register::fields) {
#		print MAIL "\t$field=" . $q->param($field) , "\n";
#	}

	my $fee = $q->param("fee");
	
	my $fullName = $q->param("name");
	my $address = $q->param("address_line_1");
	if ($q->param("address_line_2")) {
		$address .= ", " . $q->param("address_line_2");
	}
	my $cityAndState = $q->param("city") . ", " . 
		$q->param("state") . " " . $q->param("postal_code");
	my $country = $q->param("country");
	my $affiliation = $q->param("affiliation");
	my $phone = $q->param("phone");
	my $email = $q->param("email");		# should be same as $user?
	
	my $billing_address = $q->param("billing_address");
	$billing_address =~ s/\r\n/, /g;
	
	my $author = $q->param("author");
	my $focus_group_leader = $q->param("focus_group_leader");
	
	my $room = $q->param("room");
	my $room_mate = $q->param("room_mate");
	
	my $participants = $q->param("participants");
	my $children = $q->param("children");
	my $vegetarian = $q->param("vegetarian");
	
	my $nameOnCard = $q->param("name_on_card");
	my $cardType = $q->param("card_type");

	print MAIL <<END;
$fullName
$affiliation
$address
$cityAndState
$country

$phone
$email

Alternative billing address: $billing_address

Author: $author
Focus group leader: $focus_group_leader

You booked a $room room for $participants adult(s) and $children child(ren).
END
	
	if ($room eq "double") {
		print MAIL <<END;
Room mate: $room_mate
END
	}
	
	print MAIL <<END;
We have registered vegetarian meals for $vegetarian participant(s).

Additional notes: $comments

You will pay by $cardType issued to $nameOnCard.

Total fee per person: $fee Euro (reductions may apply to accompanying participants and children: children 0-5 are free, children 6-14 pay a reduced fee)
END
	close (MAIL);
	
	# TODO: confirm reduced fee for children 6-14
	
	my $chair_email = "$config->{conference_chair_email},$config->{program_chair_email}";
	
	# TODO: disable during initial testing
	my $mail = Email::send($chair_email, "",
		"[$CONFERENCE] Registration", $tmpFileName);
	if ($debug) {
		print "<hr/><pre>$mail</pre>\n";
	}
}

# Send forgotten password to email address
sub sendForgottenPassword {
	my ($email, $name) = @_;
	my ($firstName) = $name =~ /^(\w+)/;
	unless ($firstName) {
		$firstName = "Forgot";
	}

	# DONE: send email to participant with and password
	my $tmpFileName = Email::tmpFileName($timestamp, $firstName);
	open (MAIL, ">$tmpFileName");
	print MAIL <<END;
We have retrieved your password. You can login using:

END

print <<END;

Best regards,
$WEB_CHAIR
Web Chair of $CONFERENCE
END
	close (MAIL);
	
	# TODO: during initial test, don't actually send mail
	my $mail = Email::send($email, "",
		"[$CONFERENCE] Forgotten password", $tmpFileName);
	if ($debug) {
		print "<hr/><pre>$mail</pre>\n";
	}
}


# Utilities

sub checkAuthorPassword {
	my ($user, $password) = @_;
	if (Password::checkPassword(0, $user, $password)) {
		return "author";
	}
	return "";
}

sub checkReviewerPassword {
	my ($user, $password) = @_;
	return Review::authenticate($user, $password);
}

# Main dispatcher

my $action = $q->param("action") || "sign_in";
Format::sanitizeInput();
Audit::trace($action);
if ($action eq "sign_in") {
	handleSignIn();
} elsif ($action eq "register") {
	handleRegistration();
} elsif ($action eq "registration_submitted") {
	handleRegistrationSubmitted();
} else {
	Audit::handleError("No such action");
}