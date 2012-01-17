#!/usr/bin/perl -wT
use CGI;
use CGI::Carp qw( fatalsToBrowser );
use URI::Escape ('uri_escape');

use lib '.';
use Core::Assert;
use Core::Format;
use Core::Serialize;
use Core::Serialize::Records;
use Core::Email;
use Core::Session;
use Core::Password;
use Core::Access;
use Core::Shepherd;
use Core::Review;
# use Core::Register;

my $LOCK = 2;
my $UNLOCK = 8;

our $q = new CGI;
our $timestamp = time();

our $script = "admin.cgi";

our $config = Serialize::getConfig();
our $WEBCHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $baseUrl = $config->{"url"};

BEGIN {
	sub handleInternalError {
		my $error = shift;
		# DONE: log errors with error details
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
	Format::createHeader("Admin > Sign in");
	
	my $disabled = $config->{"shepherd_submission_open"} || 
		$config->{"shepherding_open"} ? "" : "disabled";
		
#	print <<END;
#<h3>Log in as</h3>
#<p>
#<input name="role" type="radio" value="author" 
#	onClick="document.location='$baseUrl/submit.cgi'"/> Author &nbsp;
#<input name="role" type="radio" value="shepherd"
#	onClick="document.location='$baseUrl/shepherd.cgi'" $disabled/> Shepherd &nbsp;
#<input name="role" type="radio" value="pc" 
#	onClick="document.location='$baseUrl/screen.cgi'"/> PC Member (Screening) &nbsp;
#<input name="role" type="radio" value="admin" checked
#	onClick="document.location='$baseUrl/admin.cgi'"/> Chair &nbsp;
#<input name="role" type="radio" value="participant"
#	onClick="document.location='$baseUrl/register.cgi'"/> Participant
#</p>
#END

	Format::startForm("post", "menu");
	Format::createHidden("session", Session::create(Session::uniqueId(), $timestamp));
		
	# Format::createTextWithTitle("Sign in", "My user name is", "user", 20);
	# Format::createPasswordWithTitle("", "My password is", "password", 20);
	
	print <<END;
			<p>You need an administrator password to access this part of the site.</p>
			
			<table cellpadding="0" cellspacing="5">
				<tr>
					<td>Admin user name:</td>
					<td width="10"></td>
					<td><input name="user" type="text"/></td>
				</tr><tr>
					<td>Password:</td>
					<td width="10"></td>
					<td><input name="password" type="password"/></td>
				</tr>
			</table>
END
	
	# DONE: replace "review page" by ...

	Format::endForm("Sign in");
	Format::createFooter();
}

sub handleMenu {
	# DONE: check that this is a valid session id
	Assert::assertTrue(Session::check($q->param("session")), 
		"Session expired. Please sign in first.");
		
	my ($user, $role) = Session::getUserRole($q->param("session"));	
	unless ($user && $role) {
		# TODO: what you really want to is use the generalized access control
		# mechanism that works with all roles, not just admin
		Assert::assertTrue(checkPassword($q->param("user"), $q->param("password")),
			"Please check that you entered the correct user name and password");
		# using roles now: checkPassword only passes administrators
		$user = $q->param("user");
		$role = "admin";
		Session::setUser($q->param("session"), $user, $role);
	}
	Assert::assertTrue($role eq "admin",
		"You must be an admin user to access this site");

	Format::createHeader("Admin > Menu");
	
	my $session = $q->param("session");
	print <<END;
	<ul>
		<li><a href="$script?action=view_submissions&session=$session">View submissions</a></li>
		<li><a href="$script?action=authors&session=$session">View authors</a></li>
		<li><a href="$script?action=pc&session=$session">View PC members</a></li>
		<li><a href="$script?action=shepherds&session=$session">View shepherds</a></li>
		<li><a href="admin.cgi?action=participants&session=$session">View participants</a></li>
		<li><a href="admin.cgi?action=participants&session=$session&format=csv">View participants as CSV list</a></li>
	</ul>
END
	
	Format::createFooter();
}

sub handleViewSubmissions {	
	Assert::assertTrue(Session::check($q->param("session")), 
		"Session expired. Please sign in first.");
	my ($user, $role) = Session::getUserRole($q->param("session"));	
	Assert::assertTrue($role eq "admin",
		"You must be an admin user to access this site");
		
	Format::createHeader("Admin > Submissions");
	
	# form to view submissions to a given track
	Format::startForm("post", "submissions");
	Format::createHidden("session", $q->param("session"));
	
	Format::createRadioButtonsWithTitle("View submissions to which track?", 
		"Desired track, or all", "track",
		"1", $config->{"track_1"},
		"2", $config->{"track_2"},
		"3", $config->{"track_3"},
		"0", "All",
		"0");
		
	Format::createCheckboxesWithTitleOnOneLine("Apply filters", 
		"Select all filters that are applicable", "filter",
		"current", "Show current versions",
		"csv", "Export to .csv format",
		"tags", "Show keywords (only in .csv)",
#		"other", "Do something else",
		"current"
	);
	Format::endForm("View");
	
	Format::createFooter();
}

sub handleSubmissions {
	# DONE: check that this is a valid session id
	Assert::assertTrue(Session::check($q->param("session")), 
		"Session expired. Please sign in first.");
	my ($user, $role) = Session::getUserRole($q->param("session"));	
	Assert::assertTrue($role eq "admin",
		"You must be an admin user to access this site");

	my ($track) = $q->param("track") =~ /(\d+)/;
	
	Format::createHeader("Admin > Submissions", "", "js/tablesort.js");
	
	Format::createFreetext("<h2>" . $config->{"track_" . $track} . "</h2>");
	
	Format::startForm("post", "menu");
	Format::createHidden("session", $q->param("session"));
	
	my %filters = map { $_ => 1 } $q->param("filter");

	my @records;
	unless ($filters{"current"}) {
		@records = Records::list();
	} else {
		@records = Records::listCurrent();
	}
	
	unless ($filters{"csv"}) {
		print <<END;
<table border="1" cellspacing="0" width="100%" onClick="sortColumn(event)">
<thead>
	<tr bgcolor="buttonface">
		<td width="200" type="Date"><b>Time</b></td>
		<td width="20" type="Number"><b>#</b></form></td>
		<td width="200" type="Name"><b>Authors</b></td>
		<td><b>Submission</b></td>
	</tr>
</thead>
<tbody>
END
	} else {
#		print "<pre>\n";
	}
	
	foreach $label (sort @records) {
		if ($label =~ /^(\d+)_(\d+)$/) {
			my $reference = $2;
			my $time = localtime($1);
			my ($dayOfWeek, $month, $day, $h, $m, $s, $year) =
				$time =~ /(\w+) (\w+) (\d+) (\d+):(\d+):(\d+) (\d+)/;
			my $record = getRecord($label);
			if ($track eq $record->param("track") 		# show a specific track
				|| $track eq "0") {						# show all tracks
				my $authors = $record->param("authors");
				my $title = $record->param("title");
				my $abstract = $record->param("abstract");
				my $referenceAndVersion = 
					$record->param("file_name");
				$referenceAndVersion =~ s/\.\w+$//;
				unless ($referenceAndVersion) {
					$referenceAndVersion = $reference;		# for legacy records (testing)
				}
				my $tags = $record->param("tags");
			# TODO: download through POST to avoid bookmarking page
				my $token = uri_escape(Access::token($label));
				unless ($filters{"csv"}) {
					$authors =~ s|\n|<br/>|g;
#					print <<END;
#	<tr>
#		<td valign="top">$month $day, $year<br/>
#			$h:$m:$s</td>
					print <<END;
	<tr>
		<td valign="top">$time</td>
		<td valign="top">$referenceAndVersion</td>
		<td valign="top">$authors</td>
		<td valign="top"><b><a href="shepherd.cgi?token=$token&action=download&label=$label">$title</a></b><br/>
			$abstract</td>
	</tr>
END
				} else {
					$authors =~ s|\n|, |g;
					if ($filters{"tags"}) {
						$tags = ", \"$tags\"";
					}
					print <<END;
$referenceAndVersion, "$authors", "$title"$tags<br/>
END
				}
			}
		}
	} 
	
	unless ($filters{"csv"}) {
		print <<END;
</tbody>
</table>
END
	} else {
#		print "</pre>\n";
	}
	
	Format::endForm("Menu");
	Format::createFooter();
}

sub handleAuthors {	
	Assert::assertTrue(Session::check($q->param("session")), 
		"Session expired. Please sign in first.");
	my ($user, $role) = Session::getUserRole($q->param("session"));	
	Assert::assertTrue($role eq "admin",
		"You must be an admin user to access this site");
		
	Format::createHeader("Admin > Authors");
	
	Format::startForm("post", "menu");
	Format::createHidden("session", $q->param("session"));

	my @records;
	@records = Records::listCurrent();

	my $emails;
	
	print "<table>\n";
	foreach $label (sort @records) {
		if ($label =~ /^(\d+)_(\d+)$/) {
			my $reference = $2;
			unless (Shepherd::status($reference) eq "reject" ||
				Shepherd::status($reference) eq "withdrawn") {
				my $record = getRecord($label);
				my $contactName = $record->param("contact_name");
				my $contactEmail = $record->param("contact_email");		
				unless ($emails) {
					$emails = $contactEmail;
				} else {
					$emails .= "," . $contactEmail;
				}	
				print <<END;
	<tr>
		<td>$contactName</td>
		<td width="10"></td>
		<td>$contactEmail</td>
	</tr>
END
			}
		}
	}
	print "</table>\n";
	
	print <<END;
	<p><a href="mailto:$emails">Send email to all authors</a></p>
END
	
	Format::endForm("Menu");

	Format::createFooter();
}

sub handlePc {	
	Assert::assertTrue(Session::check($q->param("session")), 
		"Session expired. Please sign in first.");
	my ($user, $role) = Session::getUserRole($q->param("session"));	
	Assert::assertTrue($role eq "admin",
		"You must be an admin user to access this site");
		
	Format::createHeader("Admin > PC");
	
	Format::startForm("post", "menu");
	Format::createHidden("session", $q->param("session"));

	my @pcMembers = Review::getProgramCommitteeMembers();
	my $emails;	

	print "<table>\n";
	foreach $email (@pcMembers) {
		unless ($emails) {
			$emails = $email;
		} else {
			$emails .= "," . $email;
		}
		my $name = Review::getReviewerName($email);
		print <<END;
	<tr>
		<td>$name</td>
		<td width="10"></td>
		<td>$email</td>
	</tr>
END
	}
	print "</table>\n";
	
	print <<END;
	<p><a href="mailto:$emails">Send email to all PC members</a></p>
END
	
	Format::endForm("Menu");

	Format::createFooter();
}

sub handleShepherds {	
	Assert::assertTrue(Session::check($q->param("session")), 
		"Session expired. Please sign in first.");
	my ($user, $role) = Session::getUserRole($q->param("session"));	
	Assert::assertTrue($role eq "admin",
		"You must be an admin user to access this site");
		
	Format::createHeader("Admin > Shepherds");
	
	Format::startForm("post", "menu");
	Format::createHidden("session", $q->param("session"));

	my $assignments = Shepherd::assignments();
	my $emails;	

	print "<table>\n";
	foreach $assignment (values %$assignments) {
		my $email = $assignment->{"shepherd"}; 
		unless ($emails) {
			$emails = $email;
		} else {
			$emails .= "," . $email;
		}
		my $name = Review::getReviewerName($email);
		print <<END;
	<tr>
		<td>$name</td>
		<td width="10"></td>
		<td>$email</td>
	</tr>
END
	}
	print "</table>\n";
	
	print <<END;
	<p><a href="mailto:$emails">Send email to all shepherds</a></p>
END
	
	Format::endForm("Menu");

	Format::createFooter();
}

sub handleParticipants {	
	Assert::assertTrue(Session::check($q->param("session")), 
		"Session expired. Please sign in first.");
	my ($user, $role) = Session::getUserRole($q->param("session"));	
	Assert::assertTrue($role eq "admin",
		"You must be an admin user to access this site");
		
	Format::createHeader("Admin > Participants");
	
	Format::startForm("post", "menu");
	Format::createHidden("session", $q->param("session"));
	
		unless ($q->param("format") eq "csv") {
	my %participants;
	%participants = Register::getAllRegistrations();

	my $emails;
	print "<table>\n";
	foreach $email (sort keys %participants) {
		my $name = $participants{$email}->[2];
		my $organization = $participants{$email}->[3];
		my $country = $participants{$email}->[9];
		unless ($emails) {
			$emails = $email;
		} else {
			$emails .= "," . $email;
		}	
		print <<END;
	<tr>
		<td width="150">$name</td>
		<td width="10"></td>
		<td>$organization</td>
		<td width="10"></td>
		<td>$country</td>
		<td width="10"></td>
		<td>$email</td>
	</tr>
END
	}
	print "</table>\n";
	
	print <<END;
	<p><a href="mailto:$emails">Send email to all participants</a></p>
END
		} else {
	# provide link to csv list of participants
	my @participants = Register::getAllRegistrationsAsCsvList();
	
	foreach $participant (@participants) {
		print <<END;
	$participant<br/>
END
	}
		}
	
	Format::endForm("Menu");

	Format::createFooter();
}

sub handleDownload {
	# DONE: check that this is a valid session id
	# TODO: implement session timeout
#	Assert::assertTrue(Session::check($q->param("session")), 
#		"Session expired. Please <a href=\"$baseUrl/$script\">sign in</a> first.");

	my ($label) = $q->param("label") =~ /^(\d+_\d+)$/;
#	Assert::assertTrue(Access::check($q->param("token"), $label),
#		"You are not allowed to access the requested document.");
	my $token = Access::token($label);
	unless ($token eq $q->param("token")) {
		print $q->start_html("Error"),
			$q->h1("Error"),
			$q->p("You are not allowed to access the requested document."),
			$q->end_html();
	} else {
		my $record = getRecord($label);
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

sub handleLog {
	# DONE: check that this is a valid session id
#	Assert::assertTrue(Session::check($q->param("session")), 
#		"Session expired. Please <a href=\"$baseUrl/$script\">sign in</a> first.");
	
	Format::createHeader("Log", "", "js/tablesort.js");

	Format::startForm("post", "menu");
	Format::createHidden("session", Session::create(Session::uniqueId(), $timestamp));

	print <<END;
<table border="1" cellspacing="0" onClick="sortColumn(event)">
<thead>
	<tr bgcolor="buttonface">
		<td width="100" type="HostAddress"><b>Host</b></td>
		<td width="200" type="Date"><b>Time</b></form></td>
		<td><b>Action</b></td>
	</tr>
</thead>
<tbody>
END
	open(LOG, "data/log.dat") ||
		handleError("Could not access log");
	flock(LOG, $LOCK);
	while (<LOG>) {
		/(.+?), (\d+?), (.+)/;
		my $host = $1;
		my $time = localtime($2);
		my $action = $3;
		my ($dayOfWeek, $month, $day, $h, $m, $s, $year) =
			$time =~ /(\w+) (\w+) (\d+) (\d+):(\d+):(\d+) (\d+)/;		
#		print <<END;
#	<tr>
#		<td valign="top">$host</td>
#		<td valign="top">$month $day, $year $h:$m:$s</td>
		print <<END;
	<tr>
		<td valign="top">$host</td>
		<td valign="top">$time</td>
		<td valign="top">$action</td>
	</tr>
END
	}
	flock(LOG, $UNLOCK);
	close(LOG);
	print <<END;
</tbody>
</table>
END
	Format::endForm("Back");
	Format::createFooter();
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

# Audit

sub trace {
	my ($action) = @_;
	my $remote_host = $q->remote_host();
	open(LOG, ">>data/log.dat") ||
		handleError("Could not log action: $ip, $timestamp, $action");
	flock(LOG, $LOCK);
	print LOG "$remote_host, $timestamp, review.$action\n";
	flock(LOG, $UNLOCK);
	close(LOG);
}

sub addToErrorLog {
	my ($error) = @_;
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

# Utilities

sub listOfRecords {
	opendir DIR, "data/records" ||
    	::handleError("Internal: could not search submission records");
	@records = readdir DIR;
    closedir DIR;
    return @records;
}

sub checkPassword {
	my ($user, $password) = @_;
	if ($user eq "europlop") {
		if ($password eq $config->{"admin_password"}) {
			return 1;
		}
	}
	return 0;
}

sub getRecord {
	my ($name) = @_;
	open FILE, "data/records/$name" ||
    	handleError("Internal: could not read submission record");
    my $q_saved = new CGI(FILE);
    close FILE;
    return $q_saved;
}

# TODO: align with submit.cgi#dumpRecord
sub dumpRecord {
	my ($q) = @_;
	print "<hr/>\n";
	print "<ul>\n";
	foreach $name ($q->param()) {
		my $value = $q->param($name);
		print "<li>$name: $value</li>\n";
	}
	print "</ul>\n";
	print "<hr/>\n";
}

# Main dispatcher

my $action = $q->param("action") || "sign_in";
Format::sanitizeInput();
trace($action);
if ($action eq "sign_in") {
	handleSignIn();
} elsif ($action eq "menu") {
	handleMenu();
} elsif ($action eq "view_submissions") {
	handleViewSubmissions();
} elsif ($action eq "submissions") {
	handleSubmissions();
} elsif ($action eq "log") {
	handleLog();
} elsif ($action eq "authors") {
	handleAuthors();
} elsif ($action eq "pc") {
	handlePc();
} elsif ($action eq "participants") {
	handleParticipants();
} elsif ($action eq "shepherds") {
	handleShepherds();
} else {
	handleError("No such action");
}