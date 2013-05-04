#!/usr/bin/perl -wT
use CGI;
use CGI::Carp qw( fatalsToBrowser );
use URI::Escape ('uri_escape');

use lib '.';
use Core::Assert;
use Core::Audit;
use Core::Format;
use Core::Serialize;
use Core::Serialize::Records;
use Core::Email;
use Core::Session;
use Core::Password;
use Core::Access;
use Core::Shepherd;
use Core::Review;
use Core::Register;
use Core::Role;
use Core::Contact;
use Core::Debug;

my $LOCK = 2;
my $UNLOCK = 8;

our $q = new CGI;
our $timestamp = time();

our $script = "admin.cgi";

our $config = Serialize::getConfig();
our $WEBCHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $CONFERENCE_ID = $config->{"conference_id"};
our $baseUrl = $config->{"url"};
our $NUMBER_OF_TRACKS = $config->{"focus_group_track"};

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

sub handleMenu {
	my $session = checkCredentials();
	my ($user, $role) = Session::getUserRole($session);

	Format::createHeader("Admin > Menu");

	print <<END;
	<div id="widebox">
	<p>Here is what you can do:</p>

	<ul>
		<li><a href="$script?action=view_submissions&session=$session">View submissions</a></li>
		<li><a href="$script?action=authors&session=$session">View authors</a></li>
		<li><a href="$script?action=pc&session=$session">View PC members</a></li>
		<li><a href="$script?action=shepherds&session=$session">View shepherds</a></li>
	<!--
		<li><a href="admin.cgi?action=participants&session=$session">View participants</a></li>
		<li><a href="admin.cgi?action=participants&session=$session&format=csv">View participants as CSV list</a></li>
	-->
	</ul>
END

	# TODO: put this code into a shared library
	print <<END;
	<ul>
		<li>Change role to:
END

	my @roles = Role::getRoles($user, $CONFERENCE_ID);
	foreach (@roles) {
		unless ($_ eq $role) {
			print " <a href=\"$baseUrl/gate.cgi?action=change_role&session=$session&role=$_\">$_</a>";
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

sub handleViewSubmissions {
	my $session = checkCredentials();

	Format::createHeader("Admin > Submissions");

	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	# form to view submissions to a given track
	Format::startForm("post", "submissions");
	Format::createHidden("session", $q->param("session"));

	print <<END;
	<div id="widebox">
END

	my @tracks;
	for (my $i = 1; $i <= $NUMBER_OF_TRACKS; $i++) {
		push(@tracks, $i);
		push(@tracks, $config->{"track_" . $i});
	}
	Format::createRadioButtonsWithTitle("View submissions to which track?",
		"Desired track, or all", "track", @tracks,
		"0", "All",
		"0");

	Format::createCheckboxesWithTitleOnOneLine("Apply filters",
		"Select all filters that are applicable", "filter",
		"current", "Only current versions",
		"csv", "Export as CSV list",
		"tags", "Show keywords",
#		"other", "Do something else",
		"current"
	);
	Format::endForm("View");

	print <<END;
	</div>
END

	Format::createFooter();
}

sub handleSubmissions {
	my $session = checkCredentials();

	my ($track) = $q->param("track") =~ /(\d+)/;

	Format::createHeader("Admin > Submissions", "", "js/tablesort.js");

	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	Format::createFreetext("<h2>" . $config->{"track_" . $track} . "</h2>");

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

	Format::createFooter();
}

sub handleAuthors {
	my $session = checkCredentials();

	Format::createHeader("Admin > Authors");

	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	my @records;
	@records = Records::listCurrent();

	my $emails;

	print <<END;
	<div id="widebox">
		<p>
			<table>
END

	# TODO: use submission list to compute list of authors, and move to submissions module

	# DONE: keep track of which authors have been listed already
	my %authors;

	foreach $label (sort @records) {
		if ($label =~ /^(\d+)_(\d+)$/) {
			my $reference = $2;
			unless (Shepherd::status($reference) eq "rejected" ||
					Shepherd::status($reference) eq "withdrawn") {
				my $record = getRecord($label);
				my $contactName = $record->param("contact_name");
				my $contactEmail = $record->param("contact_email");
				unless ($authors{$contactEmail}) {
					unless ($emails) {
						$emails = $contactEmail;
					} else {
						$emails .= "," . $contactEmail;
					}
					print <<END;
	<tr>
		<td>$contactName</td>
		<td width="10"></td>
		<td><a href="mailto:$contactEmail">$contactEmail</a></td>
	</tr>
END
					# remember that author has already been shown
					$authors{$contactEmail} = 1;
				}
			}
		}
	}
	print <<END;
			</table>
		</p>
	</div>

	<p><a href="mailto:$emails">Send email to all authors</a></p>
END

	Format::createFooter();
}

# handle request to list PC members
sub handlePc {
	my $session = checkCredentials();

	Format::createHeader("Admin > PC");

	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	print <<END;
	<div id="widebox">
		<p>
			<table>
END

	# gather list of pc names and emails
	my %emails;
	my @members = Review::getProgramCommitteeMembers();
	foreach my $user (@members) {
		my $name = Review::getReviewerName($user);
		my $email = Review::getReviewerEmail($user);
		$emails{$name} = $email;
	}

	# show sorted list of pc member names and emails
	my $emails;
	foreach my $name (sort keys %emails) {
		unless ($emails) {
			$emails = $emails{$name};
		} else {
			$emails .= "," . $emails{$name};
		}
		print <<END;
	<tr>
		<td>$name</td>
		<td width="10"></td>
		<td><a href="mailto:$emails{$name}">$emails{$name}</a></td>
	</tr>
END
	}

	print <<END;
			</table>
		</p>
	</div>

	<p><a href="mailto:$emails">Send email to all PC members</a></p>
END

	print <<END;
	<p>
		<a href="$script?action=add_role&role=pc&session=$session">Add a new PC member</a><br/>
		<a href="$script?action=remove_role&role=pc&session=$session">Remove a PC member</a><br/>
		<a href="$script?action=assignments&role=admin&session=$session">Edit screening assignments</a>
	</p>
END

	Format::createFooter();
}

sub handleAddRole {
	my $session = checkCredentials();

	Format::createHeader("Admin > Add Role");

	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	my $role = $q->param("role");
	if ($role eq "pc") {
		if ($q->param("new_user")) {
			my $user = $q->param("new_user");
			unless (Role::hasRole($user, $CONFERENCE_ID, "pc")) {
				Role::addRole($user, $CONFERENCE_ID, "pc");
			}
		}
		print <<END;
	<form>
	<p>To add a new PC member, select a user on the right and click "<<".</p>
	<p><table>
		<tr>
			<th>PC</th>
			<th></th>
			<th>Users</th>
		<tr>
		<tr><td>
	<select name="old_user" multiple="false" size="12">
END

		my @members = Review::getProgramCommitteeMembers();
		foreach my $user (@members) {
			my $name = Review::getReviewerName($user);
			print <<END;
		<option name="old_user" value="$user"/> $name ($user)
END
		}

		print <<END;
	</select>
		</td><td>
		<input type="hidden" name="session" value="$session">
		<input type="hidden" name="action" value="add_role">
		<input type="hidden" name="role" value="$role">
		<input type="submit" value="<<">
		</td><td>
	<select name="new_user" multiple="false" size="12">
END

		my @contacts = Contact::loadAllContacts();
		foreach my $user (@contacts) {
			unless (Role::hasRole($user, $CONFERENCE_ID, $role)) {
				my $name = Review::getReviewerName($user);
				print <<END;
		<option name="new_user" value="$user"/> $name ($user)
END
			}
		}

		print <<END;
	</select></td>
		</tr>
	</table></p>
	</form>
END
	} else {
		print <<END;
	<p>Role not yet supported.</p>
END
	}

	Format::createFooter();
}

sub handleRemoveRole {
	my $session = checkCredentials();

	Format::createHeader("Admin > Remove Role");

	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	my $role = $q->param("role");
	if ($role eq "pc") {
		if ($q->param("old_user")) {
			my $user = $q->param("old_user");
			if (Role::hasRole($user, $CONFERENCE_ID, "pc")) {
				Role::removeRole($user, $CONFERENCE_ID, "pc");
			}
		}
		print <<END;
	<form>
	<p>To remove a PC member, select a user on the left and click ">>".</p>
	<p><table>
		<tr>
			<th>PC</th>
			<th></th>
			<th>Users</th>
		<tr>
		<tr><td>
	<select name="old_user" multiple="false" size="12">
END

		my @members = Review::getProgramCommitteeMembers();
		foreach my $user (@members) {
			my $name = Review::getReviewerName($user);
			print <<END;
		<option name="old_user" value="$user"/> $name ($user)
END
		}

		print <<END;
	</select>
		</td><td>
		<input type="hidden" name="session" value="$session">
		<input type="hidden" name="action" value="remove_role">
		<input type="hidden" name="role" value="$role">
		<input type="submit" value=">>">
		</td><td>
	<select name="new_user" multiple="false" size="12">
END

		my @contacts = Contact::loadAllContacts();
		foreach my $user (@contacts) {
			unless (Role::hasRole($user, $CONFERENCE_ID, $role)) {
				my $name = Review::getReviewerName($user);
				print <<END;
		<option name="new_user" value="$user"/> $name ($user)
END
			}
		}

		print <<END;
	</select></td>
		</tr>
	</table></p>
	</form>
END
	} else {
		print <<END;
	<p>Role not yet supported.</p>
END
	}

	Format::createFooter();
}

# handle request to edit assignments
sub handleAssignments {
	my $session = checkCredentials();

	Format::createHeader("Admin > Screening assignments");

	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	my @pcMembers = Review::getProgramCommitteeMembers();
	if ($q->param("status") eq "updated") {
		updateAssignments(@pcMembers);
	}
	showAssignmentsEditor($session, @pcMembers);

	Format::createFooter();
}

sub updateAssignments {
	my @pcMembers = @_;
	foreach $reviewer (@pcMembers) {
		# Still a proof of concept, not the final tool
		# TODO: make number of papers assigned to each PC configurable
		# TODO: support wildcard "*" to assign all papers
		# TODO: should really check that parameters are numbers
		foreach my $i (0..9) {
			my $paper = $q->param("$reviewer.$i");
			if ($paper) {
				Assign::assignPaper($reviewer, $paper);
			}
		}
	}
	Assign::saveAssignments();
}

sub showAssignmentsEditor {
	my ($session, @pcMembers) = @_;

	print <<END;
	<div id="widebox">
	<form method="POST">
	<p><table>
END

	foreach $reviewer (@pcMembers) {
		showAssignmentsForOneReviewer($reviewer);
	}

	print <<END;
	</table></p>
	<input type="hidden" name="session" value="$session">
	<input type="hidden" name="action" value="assignments">
	<input type="hidden" name="status" value="updated">
	<input type="submit" value="Update">
	</form>
	</div>
END
}

sub showAssignmentsForOneReviewer {
	my ($reviewer) = @_;
	my $name = Review::getReviewerName($reviewer);
		print <<END;
		<tr>
			<td>$name</td>
			<td width="10">
END
		my @assignments = Assign::getAssignmentsForReviewer($reviewer);
		foreach my $i (0..9) {
			my $paper = $assignments[$i];
			print <<END;
			<td><input name="$reviewer.$i" type="text" size="1" value="$paper"></td>
END
			$i++;
		}
		print <<END;
		</tr>
END
}

# handle request to view shepherds
sub handleShepherds {
	my $session = checkCredentials();

	Format::createHeader("Admin > Shepherds");

	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	my $assignments = Shepherd::assignments();
	my $emails;

	print <<END;
	<div id="widebox">
		<p>
			<table>
END

	foreach $assignment (values %$assignments) {
		# TODO: assignments linked to users, not emails
		my $user = $assignment->{"shepherd"};
		my $email = Review::getReviewerEmail($user);
		unless ($emails) {
			$emails = $email;
		} else {
			$emails .= "," . $email;
		}
		my $name = Review::getReviewerName($user);
		print <<END;
	<tr>
		<td>$name</td>
		<td width="10"></td>
		<td>$email</td>
	</tr>
END
	}

	print <<END;
			</table>
		</p>
	</div>

	<p><a href="mailto:$emails">Send email to all shepherds</a></p>
END

	Format::createFooter();
}

sub handleParticipants {
	my $session = checkCredentials();

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
	# TODO: implement session timeout

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
	my $session = checkCredentials();

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
	Audit::addToErrorLog($error);
	Format::createHeader("Error");
	my $uriEncodedError = uri_escape($error);
	print <<END;
<p><b style="color:red">$error</b></p>
<p><input type=button value="Back to form" onClick="history.go(-1)"/></p>
END
	Format::createFooter();
	exit(0);
}

# Utilities

sub checkCredentials {
	my $session = $q->param("session");
	Assert::assertTrue(Session::check($session),
		"Session expired. Please sign in first.");
	my ($user, $role) = Session::getUserRole($q->param("session"));
	Assert::assertTrue($user, "You are not logged in");
	Assert::assertTrue($role eq "admin",
		"You must be an admin user to access this site");
	return $session;
}

sub listOfRecords {
	opendir DIR, "data/records" ||
    	::handleError("Internal: could not search submission records");
	@records = readdir DIR;
    closedir DIR;
    return @records;
}

sub getRecord {
	my ($name) = @_;
	open FILE, "data/records/$name" ||
    	handleError("Internal: could not read submission record");
    my $q_saved = new CGI(FILE);
    close FILE;
    return $q_saved;
}

# Main dispatcher

my $action = $q->param("action") || "menu";
Format::sanitizeInput();
Audit::trace($action);
if ($action eq "menu") {
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
} elsif ($action eq "add_role") {
	handleAddRole();
} elsif ($action eq "remove_role") {
	handleRemoveRole();
} elsif ($action eq "assignments") {
	handleAssignments();
} elsif ($action eq "participants") {
	handleParticipants();
} elsif ($action eq "shepherds") {
	handleShepherds();
} else {
	handleError("No such action");
}