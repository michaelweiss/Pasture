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
use Core::Review;

our $q = new CGI;
our $timestamp = time();

our $script = "screen.cgi";

our $config = Serialize::getConfig();
our $WEB_CHAIR_EMAIL = $config->{"web_chair_email"};
our $WEB_CHAIR = $config->{"web_chair"};
our $CONFERENCE = $config->{"conference"};
our $CONFERENCE_ID = $config->{"conference_id"};
our $baseUrl = $config->{"url"};

BEGIN {
	sub handleInternalError {
		my $error = shift;
		my $q = new CGI;
		print $q->start_html(-title => "Error"),
			$q->h1("Internal error:"),
			$q->pre($error),
			$q->p("Please report the error to the conference web chair <a href=\"mailto:$WEB_CHAIR_EMAIL\">$WEB_CHAIR_EMAIL</a>."),
			$q->end_html;
	}
	CGI::Carp::set_message( \&handleInternalError );
}

# Handlers

sub handleSubmissions {
	my $session = checkCredentials();
	my ($user, $role) = Session::getUserRole($session);	
		
	# if vote, user has decided on a rank
	# if only reason, user has not assessed but wants like their current reason stored
	if ($q->param("vote") || $q->param("reason")) {
		Screen::saveVote($timestamp, $user, 
			$q->param("reference"), $q->param("vote"), $q->param("reason"));
	}
	my $votes = Screen::votes();
	
	Format::createHeader("Screen > Submissions", "", "js/validate.js");	
	
	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END
	
	# changed votes to format suggested by allan:
	# 1 - I'm glad this paper was submitted, it's a joy!
	# 2 - Good ideas in this paper, more work to do.
	# 3 - Not ready yet, the paper needs a strong shepherd.
	# 4 - There's a high risk that this paper wastes a shepherd's time.
	#
	# replaced following:
	# <tr><td><img border="0" src="$baseUrl/images/vote.png"/></a></td><td><em>average-vote</em> pre-sheperding vote &nbsp; (1:strong reject, 2:reject, 3:neutral, 4:accept, 5:strong accept)</td></tr>
	#
	# with:
	#
	# <tr><td><img border="0" src="$baseUrl/images/vote.png"/></a></td><td><em>average-vote</em> pre-sheperding vote &nbsp; (1:it's a joy, 2:good ideas, 3:strong shepherd needed, 4:high risk)</td></tr>
	
	print <<END;
	<h4>Legend</h4>
		<table>
			<tr><td><img border="0" src="$baseUrl/images/comment.png"/></td><td><em>number-of-votes</em> votes (<em>your-vote</em>)</td></tr>
			<tr><td><img border="0" src="$baseUrl/images/vote.png"/></a></td><td><em>average-vote</em> pre-sheperding vote &nbsp; (1:it's a joy, 2:good ideas, 3:strong shepherd needed, 4:high risk)</td></tr>
			<tr><td>(-)</td><td>not available</td></tr>
		</table>
		
	<h4>Instructions</h4>
	<ul>
		<li>Click on the number next to the author name to download the paper.</li>
		<li>Click on the <img border="0" src="$baseUrl/images/comment.png"/> icon to submit your review for a paper.</li>
	</ul>
END

	my $currentTrack = -1;
	# DONE: only show records that a user is allowed to see
	# DONE: based on list of assignments
	my %records = Records::getAllRecords(Records::listCurrent());
	foreach $label (
		sort { $records{$a}->param("track") <=> $records{$b}->param("track") }
			sort { $records{$a}->param("reference") <=> $records{$b}->param("reference") } 
				keys %records) {
		my $record = $records{$label};
		if (canSeeRecord($user, $role, $label)) {		
			my $reference = $record->param("reference");
			
			my $authors = getAuthors($record);
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
			my $tags = getTags($record);
			
			my $numberOfVotes = numberOfVotes($votes, $reference);
			# TODO: use a css class instead
			my $color = ($numberOfVotes < 3) ? "red" : "";
			my $userVote = userVote($votes, $user, $reference) || "-";
			my $averageVote = averageVote($votes, $reference) || "(-)";
			print <<END;
	<table border="0" cellpadding="2" cellspacing="10" width="100%">
		<tbody>
		<tr>
			<td valign="top" width="3%"><div align="right">
				<a href="?token=$token&action=download&label=$label">$reference</a>
			</td>
			<td valign="top">
			 	$authors<br/>
			 	<a href="mailto:$email">$email</a>
			</td>
		</tr>
		<tr>
			<td valign="top" width="3%"></td>
			<td valign="top" width="97%">
				<p><b>$title</b></p>
				<p><font size="-1" color="grey">$comments</font></p>
				$abstract
			</td>
		</tr>
		<tr>
			<td valign="top"></td>
			<td>Tags: $tags</td>
		</tr>
		<tr>
			<td valign="top"></td>
			<td><form method="post">
				<input type="hidden" name="action" value="vote"/>
				<input type="hidden" name="session" value="$session"/>
				<input type="hidden" name="reference" value="$reference"/>
				<input type="hidden" name="authors" value="$authors"/>
				<input type="hidden" name="title" value="$title"/>
				<font color="$color">
				<input type="image" src="$baseUrl/images/comment.png"/> $numberOfVotes votes ($userVote) 
				&nbsp; | &nbsp;
				<image border="0" src="$baseUrl/images/vote.png"/></a>&nbsp; $averageVote pre-sheperding vote &nbsp; (1:it's a joy, 2:good ideas, 3:strong shepherd needed, 4:high risk)
				</font>
				</form>
			</td>
		</tr>
		</tbody>
	</table>
END
		}
	} 

	Format::createFooter();
}

sub handleVote {
	my $session = checkCredentials();
	my ($user, $role) = Session::getUserRole($session);	

	my $reference = $q->param("reference");
	Format::createHeader("Screen > Vote", "", "js/validate.js");	
	
	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END

	Format::startForm("post", "submissions", "return checkVoteForm()");
	Format::createHidden("session", $q->param("session"));
	Format::createHidden("reference", $reference);
	
	my $authors = $q->param("authors");
	my $title = $q->param("title");
	
	my $reviews = Screen::getReviews($reference);
	my @reviewers = keys %$reviews;
	print <<END;
<h3>Submission</h3>
<dd>$authors, <b>$title</b></dd>

<h3>Reviews</h3>
<p>All reviews that have been submitted</p>
<table border="1" cellspacing="0">
END
	if ($#reviewers < 0) {
		print <<END;
	<tr><td colspan="2">No reviews available</td></tr>
END
	}
	my $you = "0";
	my $i = 1;
	my $j = $i-1;
	foreach $reviewer (@reviewers) {
		my $review = $reviews->{$reviewer};
		print <<END;
	<tr>
		<td valign="top" width="100">Reviewer $i:<br/>
END
		if ($role eq "admin") {
			print <<END;
			<a href="mailto:$user">$reviewers[$j]</a>
END
		} elsif ($reviewers[$j] eq $user) {
			print <<END;
			<b>YOU</b>
END
		}
		# remember user's vote
		if ($reviewers[$j] eq $user) {
			$you = $review->{"vote"};
		}
		print <<END;
		</td>
		<td valign="top">Vote: <b>$review->{"vote"}</b><br/>
		$review->{"reason"}<br/><br/></td>
	</tr>
END
		$i++;
		$j++;
	}
	
	# replaced:
	# 1:strong reject, 2:reject, 3:neutral, 4:accept, 5:strong accept
	# with:
	# 1 - I'm glad this paper was submitted, it’s a joy!
	# 2 - Good ideas in this paper, more work to do.
	# 3 - Not ready yet, the paper needs a strong shepherd.
	# 4 - There's a high risk that this paper wastes a shepherd's time.

	print <<END;
	<tr>
		<td valign="top">Scale:</td>
		<td>
		1: I'm glad this paper was submitted, it's a joy!<br/>
		2: Good ideas in this paper, more work to do.<br/>
		3: Not ready yet, the paper needs a strong shepherd.<br/>
		4: There's a high risk that this paper wastes a shepherd's time.<br/>
		</td>

	</tr>
</table>
END
	Format::createRadioButtonsWithTitleOnOneLine("Your assessment", 
		"Please enter or update your assessment", "vote",
		"0", "not assessed",
		"1", "it's a joy",
		"2", "good ideas",
		"3", "strong shepherd needed",
		"4", "high risk",
		$you);
		# $q_saved->param("vote") || "1");
	Format::createTextBoxWithTitle("Reason", 
		"Why did you vote like that? (will be stored even if you are not ready to assess)", "reason", 70, 5);

	Format::endForm("Vote");	# TODO: should do something else than go to sign-in
	Format::createFooter();
}

sub handleSignOut {
	my $session = checkCredentials();
	my ($user, $role) = Session::getUserRole($session);	

	Session::invalidate($session);
	
	Format::createHeader("Screen > Thanks", "", "js/validate.js");
	Format::createFooter();
}

# TODO: refactor to a core package
sub handleDownload {
	# DONE: check that this is a valid session id
	# DONE: use token-based authentication instead (not user-based)
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
		my $record = Records::getRecord($label);
		my $fileName = $record->param("file_name");
		my ($type) = $fileName =~ /\.(\w+)$/;
		if ($type eq "pdf") {
			print $::q->header(-type => "application/pdf",
				-attachment => $fileName);
		} elsif ($type eq "doc") {
			print $::q->header(-type => "application/msword",
				-attachment => $fileName);
		} else {
			handleError("file type not supported");
		}
		open FILE, "papers/$fileName";
		while (<FILE>) {
			print;
		}
		close FILE;
	}
}

sub handleError {
	my ($error) = @_;
	# DONE: log errors with error details
	Audit::addToErrorLog($error);
	Format::createHeader("Screen > Error");
	my $uriEncodedError = uri_escape($error);
	print <<END;
<p><b style="color:red">$error</b></p>
<p><input type=button value="Back to form" onClick="history.go(-1)"/></p>
END
	Format::createFooter();
	exit(0);
}

# Browsing

sub browseSubmissionsByTrack {
	Format::startForm("post", "submissions");
	Format::createHidden("session", $q->param("session"));
	Format::createRadioButtonsWithTitle("Browse submissions by track?", 
		"Select the desired track", "track",
		"1", $config->{"track_1"},
		"2", $config->{"track_2"},
		"3", $config->{"track_3"},
		"0", "Show me the submissions to <b>all</b> tracks",
		"0");
	Format::endForm("View");
}

sub browseSubmissionsByTag {
	# creates a tagcloud that allows users to select tag and browse
	# only those submission that contain the tag
	Format::startForm("post", "submissions");
	Format::createHidden("session", $q->param("session"));
	Format::createHidden("track", "9");
	Format::createHidden("tag", "");
	print <<END;
<h3>Browse submissions by tag?</h3>
<script language="javascript" type="text/javascript">
function selectedTag(tag) {
	document.forms[1].tag.value = tag;
	document.forms[1].submit();
}
</script>
<dd>
END
	Tags::ensureTagDatabase();
	Tags::tagcloud();											
	print <<END;
</dd>

</form>
END
}

# Utilities

sub checkCredentials {
	my $session = $q->param("session");
	Assert::assertTrue(Session::check($session), 
		"Session expired. Please sign in first.");
	my ($user, $role) = Session::getUserRole($q->param("session"));	
	Assert::assertTrue($user, "You are not logged in");
	Assert::assertTrue($role eq "chair" || $role eq "pc" || $role eq "admin", 
		"You are not allowed to access this site");
	return $session;
}

# TODO: make more efficient by computing once only
sub canSeeRecord {
	my ($user, $role, $label) = @_;
	if ($config->{"pc_can_screen_all"}) {
		return 1; 			# if pc_can_screen_all, allow all pc to see all records
	}
	if ($role eq "admin") {
		return 1;			# admin/chair can see all
	}
	my @submissions = Screen::getAssignments($user);
	$label =~ /_(\d+)/;		# get reference from record name (format: timestamp_reference)
	my $ref = $1;
	foreach $submission (@submissions) {
		if ($submission eq $ref) {
			return 1;		# in list of assigned submissions
		}
	}
	return 0;
}

sub getAuthors {
	my ($record) = @_;
	my $byline = $record->param("authors");
	@authors = split(/\r\n/, $byline);
	foreach (@authors) {
		s/,.+//;
	}
	$byline = join(", ", @authors);
	return $byline;
}

sub numberOfVotes {
	my ($votes, $reference) = @_;
	my @users = values %{$votes->{$reference}};
	my $n = 0;
	foreach $user (@users) {
		if ($user->{"vote"}) { $n++ };	# if vote ne "not assessed"
	}
	return $n;
}
	
sub userVote {
	my ($votes, $user, $reference) = @_;
	my $reviews = $votes->{$reference};
	if ($reviews) {
		$review = $reviews->{$user};
		if ($review) {
			return $review->{"vote"};
		}
	}
	return 0;
}

sub averageVote {
	my ($votes, $reference) = @_;
	my @users = values %{$votes->{$reference}};
	my $sum = 0;
	my $n = 0;
	foreach $user (@users) {
		$sum += $user->{"vote"};
		if ($user->{"vote"}) { $n++ };	# if vote ne "not assessed"
	}
	if ($n == 0) {
		return 0;
	}
	return int(10*$sum/$n)/10;
}

sub getTags {
	my ($record) = @_;
	my $tags = $record->param("tags");
	@tags = split(/\s*\r\n/, $tags);
	my @normalizedTags;
	foreach (@tags) {
		$_ = Tags::_normalize($_);
		if ($_) {
			push @normalizedTags, $_;
		}
	}
	$tags = join(", ", @normalizedTags);
	return $tags;
}

sub containsTag {
	my ($record, $tag) = @_;
	my $tags = $record->param("tags");
	my @tags = split(/\s*\r\n/, $tags);
	my @normalizedTags;
	foreach (@tags) {
		$_ = Tags::_normalize($_);
		if ($_) {
			push @normalizedTags, $_;
		}
	}
	foreach (@normalizedTags) {
		if (/$tag/) {
			return 1;
		}
	}
	return 0;
}

sub abstractContainsTag {
	my ($record, $tag) = @_;
	my $abstract = $record->param("abstract");
	return $abstract =~ $tag;
}

# Main dispatcher

my $action = $q->param("action") || "submissions";
Format::sanitizeInput();
Audit::trace($action);
if ($action eq "submissions") {
	handleSubmissions();
} elsif ($action eq "vote") {
	handleVote();
} elsif ($action eq "sign_out") {
	handleSignOut();
} elsif ($action eq "download") {
	handleDownload();
} else {
	handleError("No such action");
}