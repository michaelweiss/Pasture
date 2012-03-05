#!/usr/bin/perl -wT
use CGI;
use CGI::Carp qw( fatalsToBrowser );
use URI::Escape ('uri_escape');

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

our $q = new CGI;
our $timestamp = time();

our $script = "bids";

our $config = Serialize::getConfig();
our $WEBCHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $CONFERENCE_ID = $config->{"conference_id"};
our $CONFERENCE_WEBSITE = $config->{"conference_website"};
our $baseUrl = $config->{"url"};

my %titles;
my %status;	
my %assignedTo;

BEGIN {
	sub handleInternalError {
		my $error = shift;
		# DONE: log errors with error details
		addToErrorLog($error);
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

# show bids
sub handleBids {
	my $session = checkCredentials();
	my ($user, $role) = Session::getUserRole($session);	
	
	Format::createHeader("Bids", "", "js/validate.js");
	showSharedMenu($session);
	
	my %records = Records::getAllRecords(Records::listCurrent());
	my $numberOfRecords = scalar keys %records;
	%titles = getTitles(\%records);
	
	my $preferences = Shepherd::preferencesByUser();
	
	Format::createFreetext("Note: Move the mouse over the column heads to see title and track (in parentheses) of the submission by that number.");

	print <<END;
<style>
a {
  position: relative;
} 
a span {
  display: none;
}a:hover span {  position: absolute;  display: block;  background: #e0ffff;  border: 1px solid;
  left: -15em;
  width: 20em;
  height: 2.4em;
  font-style: normal;
  color: black;
  }
</style>
END

	print "<table border=1 cellspacing=1>\n";
	print "<tr>";
	print "<td>&nbsp;</td>";
	foreach $bid (1..$numberOfRecords) {
		$status{$bid} = Shepherd::status($bid);

		# TODO: show assignments with green background
		my %assignment = Shepherd::assignedTo($bid);
		if ($assignment{"shepherd"}) {
			$assignedTo{$bid} = $assignment{"shepherd"};
		}
		
		unless ($status{$bid} eq "rejected" || $status{$bid} eq "withdrawn" ||
			$titles{$bid} =~ "($config->{'focus_group_track'})") { 
			my $showBid = ($bid < 10) ? "&nbsp;$bid&nbsp;" : $bid;
			my $column = "<em>$showBid</em><span>$titles{$bid}</span>";
			if ($assignedTo{$bid}) {
				print "<td align=\"center\"><a href=\"#\">$column</a></td>";
			} else {
				print "<td align=\"center\" bgcolor=\"red\"><a href=\"#\">$column</a></td>";
			}
		}
	}
	print "</tr>";
	foreach $user (sort keys %$preferences) {
		showBidsForUser($preferences, $user, $numberOfRecords);
	}
	print "</table>\n";
	print "<br/>";
  
	Format::createFooter();
}

# Utilities

sub showBidsForUser {
	my ($preferences, $user, $numberOfRecords) = @_;
	my $name = Review::getReviewerName($user);
	print "<tr>\n";
	print "\t<td>$name</td>";
	foreach $bid (1..$numberOfRecords) {
		if ($status{$bid} eq "rejected" || $status{$bid} eq "withdrawn" ||
			$titles{$bid} =~ "($config->{'focus_group_track'})") {
			next;
		}
		if ($preferences->{$user}->{$bid}) {
			my $timestamp = $preferences->{$user}->{$bid}->{"timestamp"};
			my $priority = $preferences->{$user}->{$bid}->{"priority"};
			unless ($assignedTo{$bid} eq $user) {
				unless ($assignedTo{$bid}) {
					my $url = generateAcceptUrl($user, $timestamp, $bid);
					print "<td align=\"center\"><a href=$url target=_>$priority</a></td>";
				} else {
					print "<td align=\"center\">$priority</td>";
				}
			} else {
				print "<td align=\"center\" bgcolor=\"lightgreen\">$priority</td>";				
			}
		} else {
			print "<td>&nbsp;</td>";
		}
	}
	print "</tr>\n";
}

sub generateAcceptUrl {
	my ($user, $timestamp, $reference) = @_;
	my $label = $timestamp . "_" . $reference;
	my $token = Access::token($user . "_" . $label);
	return $config->{"url"} . 
		"/shepherd.cgi?action=accept&user=$user&label=$label&token=$token";
}

# DEBUG
sub showRawBidsForUser {
	my ($preferences, $user) = @_;
	# get the list of references the user has bid on
	my @bids = keys %{$preferences->{$user}};
	print "$user { ";
	foreach $bid (sort @bids) {
		my $priority = $preferences->{$user}->{$bid}->{"priority"};
		print "$bid => $priority, ";
	}
	print "}\n";
}

sub getTitles {
	my ($records) = @_;
	my %titles;
	foreach $label (keys %$records) {
		my $record = $records->{$label};
		my ($ref) = $label =~ /_(\d+)$/;
		$titles{$ref} = substr($record->param("title"), 0, 60) . "..." .
			" (" . $record->param("track") . ")";
	}
	return %titles;
}

sub getAuthorsAndTitles {
	my ($records) = @_;
	my %titles;
	foreach $label (keys %$records) {
		my $record = $records->{$label};
		my ($ref) = $label =~ /_(\d+)$/;
		$titles{$ref} = $record->param("contact_name") . ", " .
      $record->param("title");
	}
	return %titles;
}

sub numberOfBidders {
	my ($preferences, $user, $numberOfRecords) = @_;
	my %numberOfBidders;
	foreach $bid (1..$numberOfRecords) {
		if ($preferences->{$user}->{$bid}) {
			$numberOfBidders{$bid}++;
		}
	}
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

sub checkCredentials {
	my $session = $q->param("session");
	Assert::assertTrue(Session::check($session), 
		"Session expired. Please sign in first.");
	my ($user, $role) = Session::getUserRole($q->param("session"));	
	Assert::assertTrue($user, "You are not logged in");
	Assert::assertTrue($role eq "chair" || $role eq "admin", 
		"You are not allowed to access this site");
	return $session;
}

sub showSharedMenu {
	my ($session) = @_;
	
	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END
}

# Main dispatcher

my $action = $q->param("action") || "bids";
Format::sanitizeInput();
Audit::trace($action);
if ($action eq "bids") {
	handleBids();
} elsif ($action eq "export") {
	handleExport();
} else {
	Audit::handleError("No such action");
}

