#!/usr/bin/perl -wT
use CGI;
use CGI::Carp qw( fatalsToBrowser );
use URI::Escape ('uri_escape');

use lib '.';
use Core::Format;
use Core::Serialize;
use Core::Serialize::Records;
use Core::Session;
use Core::Password;
use Core::Access;
use Core::Tags;
use Core::Assert;
use Core::Screen;
use Core::Review;

use Core::Shepherd;

our $q = new CGI;
our $timestamp = time();

our $script = "screen.cgi";

our $config = Serialize::getConfig();
our $WEB_CHAIR_EMAIL = $config->{"web_chair_email"};
our $WEB_CHAIR = $config->{"web_chair"};
our $CONFERENCE = $config->{"conference"};
our $CONFERENCE_ID = $config->{"conference_id"};
our $baseUrl = $config->{"url"};

my $currentTrack = -1;

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

# handle request to view initial screening list
sub handleSubmissions {
	my $session = checkCredentials();
	my ($user, $role) = Session::getUserRole($session);	
		
	saveVoteWhenUpdated($user);
		
	Format::createHeader("Screen > Submissions", "", "js/validate.js");	
	showSharedMenu($session);
	
	showSubmissionsInstructions();
	
	my %records = Records::getAllRecords(Records::listCurrent());
	foreach $label (
		sort { $records{$a}->param("track") <=> $records{$b}->param("track") }
			sort { $records{$a}->param("reference") <=> $records{$b}->param("reference") } 
				keys %records) {
		my $record = $records{$label};	
		if (canSeeRecord($user, $role, $label)) {	
			showVoteCollector($session, $user, $record, $label);
		}
	} 

	Format::createFooter();
}

sub saveVoteWhenUpdated {
	my ($user) = @_;
	
	# if vote, user has decided on a rank
	# if only reason, user has not assessed but wants like their current reason stored
	if ($q->param("vote") || $q->param("reason")) {
		Screen::saveVote($timestamp, $user, 
			$q->param("reference"), $q->param("vote"), $q->param("reason"));
	}
	
}

sub showSubmissionsInstructions {
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
		<li>Click on the "Vote" button to submit your review for a paper.</li>
	</ul>
END
}

sub showVoteCollector {
	my ($session, $user, $record, $label) = @_;
	
	my $track = $record->param("track");
	if ($currentTrack != $track) {
		Format::createFreetext("<h3>" . $config->{"track_" . $track} . "</h3>");
		$currentTrack = $track;
	}
			
	print <<END;
	<table border="0" cellpadding="2" cellspacing="10" width="100%">
		<tbody>
END
	
	showReferenceAuthorsEmail($record, $label);
	showTitleCommentsAbstract($record);
	showTags($record);
	showVoteForm($session, $user, $record);
	
	print <<END;
		</tbody>
	</table>
END
}

sub showReferenceAuthorsEmail {
	my ($record, $label) = @_;

	my $reference = $record->param("reference");
	my $token = uri_escape(Access::token($label));
	my $authors = getAuthors($record);
	my $email = $record->param("contact_email");
						
	print <<END;
		<tr>
			<td valign="top" width="3%"><div align="right">
				<a href="?token=$token&action=download&label=$label">$reference</a>
			</td>
			<td valign="top">
			 	$authors<br/>
			 	<a href="mailto:$email">$email</a>
			</td>
		</tr>
END
}

sub showStatusReferenceTitle {
	my ($session, $record) = @_;

	my $reference = $record->param("reference");
	my $token = uri_escape(Access::token($label));
	my $title = $record->param("title");

	my $status = Shepherd::status($reference);
	$status = "NA" unless ($status);				

	print <<END;
		<tr>
			<td valign="top" width="3%"><div align="right">
				<a href="?token=$token&action=download&label=$label">$reference</a>
			</td>
			<td valign="top" with="87%">
				<p>$title</p>
			</td>
		</tr>
END
}

sub showStatus {
	my ($session, $record) = @_;
	my $reference = $record->param("reference");

	my $status = Shepherd::status($reference);
	$status = "NA" unless ($status);				

	print <<END;
		<tr>
			<td valign="top" width="3%">
			</td>
			<td valign="top" width="87%">
				<em>$status</em>
				(change to:
END

	print <<END unless ($status eq "rejected");
					<em><a href="?action=status&update=rejected&session=$session&reference=$reference" style="color: red">rejected</a></em>
END
	print <<END unless ($status eq "withdrawn");
					<em><a href="?action=status&update=withdrawn&session=$session&reference=$reference" style="color: blue">withdrawn</a></em>
END
	print <<END unless ($status eq "NA");
					<em><a href="?action=status&update=NA&session=$session&reference=$reference" style="color: green">NA</a></em>
END

	print <<END;
				)
			</td>
		</tr>
END
}

sub showTitleCommentsAbstract {
	my ($record) = @_;

	my $title = $record->param("title");
	my $comments = $record->param("comments");
	my $abstract = $record->param("abstract");
						
	print <<END;
		<tr>
			<td valign="top" width="3%"></td>
			<td valign="top" width="97%">
				<p><b>$title</b></p>
				<p><font size="-1" color="grey">$comments</font></p>
				$abstract
			</td>
		</tr>
END
}

sub showTags {
	my ($record) = @_;
	
	my $tags = getTags($record);
							
	print <<END;
		<tr>
			<td valign="top"></td>
			<td>Tags: $tags</td>
		</tr>
END
}

sub showVoteForm {
	my ($session, $user, $record) = @_;
	
	my $reference = $record->param("reference");
	my $authors = getAuthors($record);
	my $title = $record->param("title");
	my $votes = Screen::votes();
	my $numberOfVotes = numberOfVotes($votes, $reference);
	my $color = ($numberOfVotes < 3) ? "red" : "";
	my $userVote = userVote($votes, $user, $reference) || "-";
	my $averageVote = averageVote($votes, $reference) || "(-)";
								
	print <<END;
		<tr>
			<td valign="top"></td>
			<td><form method="post">
				<input type="hidden" name="action" value="vote"/>
				<input type="hidden" name="session" value="$session"/>
				<input type="hidden" name="reference" value="$reference"/>
				<input type="hidden" name="authors" value="$authors"/>
				<input type="hidden" name="title" value="$title"/>
				<font color="$color">
				<input type="submit" value="Vote"> <img src="$baseUrl/images/comment.png"/> $numberOfVotes votes ($userVote) 
				&nbsp; | &nbsp;
				<image border="0" src="$baseUrl/images/vote.png"/></a>&nbsp; $averageVote pre-sheperding vote &nbsp; (1:it's a joy, 2:good ideas, 3:strong shepherd needed, 4:high risk)
				</font>
				</form>
			</td>
		</tr>
END

# seems that <input type="image" ...> is not working in all browsers
# had to replace it with <input type="submit" value="vote">
}

# handle request to enter a vote
sub handleVote {
	my $session = checkCredentials();
	my ($user, $role) = Session::getUserRole($session);	

	my $reference = $q->param("reference");
	Format::createHeader("Screen > Vote", "", "js/validate.js");	
	showSharedMenu($session);

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
	my $reason = "";
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
			$reason = $review->{"reason"};
		}
		my $formattedReason = $review->{"reason"};
		$formattedReason =~ s/\n/<br\/>/g;
		print <<END;
		</td>
		<td valign="top">Vote: <b>$review->{"vote"}</b><br/>
		$formattedReason<br/><br/></td>
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

	my $template = template($reason);
	Format::createTextBoxWithTitle("Reason", 
		"Why did you vote like that? (this will be stored even if you are not ready to assess)"
		. instructionsForTemplate(), 
		"reason", 70, 10, $template);

	Format::endForm("Vote");	# TODO: should do something else than go to sign-in
	Format::createFooter();
}

# Returns either a template text or the existing reason
sub template {
	my ($reason) = @_;
	my $template = "";
	if ($reason eq "") {
		$template = <<"END";
A. Rate the maturity of the paper

B. Rate the relevance of the topic to $CONFERENCE

C. Rate the suitability for ACM

D. Explain your ratings above
END
	} else {
		$template = $reason;
	}
	return $template;
}

sub instructionsForTemplate {
	my $instructions = <<"END";
	<div>
<br/><em>
A. Rate the maturity of the paper on a scale from 1-5<br/>
1 The paper only consists of an abstract and many TODO sections<br/>
5 The paper is complete and mature: no TODO sections, no important sections missing, patterns are well elaborated<br/>
<br/>
B. Rate the relevance of the topic to $CONFERENCE on a scale from 1-5<br/>
1 The paper has nothing to do with patterns, or it appears to be some scientific paper written in pattern format<br/>
5 The paper contains many connecting patterns or connects to existing patterns, covers a meta-pattern topic, or the application of existing patterns<br/>
<br/>
C. Rate the suitability for ACM on a scale from 1-5<br/>
1 If ACM knew we were going to publish this paper in the digital library, we would never be able to publish with them again<br/>
5 The topic is highly relevant for ACM (related to computer science)
</em><br/><br/>
	</div>
END
	return $instructions;
	# Format::createFreetext($instructions);
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
		} elsif ($type eq "doc" || $type eq "docx") {
			print $::q->header(-type => "application/msword",
				-attachment => $fileName);
		} elsif ($type eq "txt") {
			print $::q->header(-type => "text/plain",
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

sub handleStatus {
	my $session = checkCredentials();
	my ($user, $role) = Session::getUserRole($session);	

	Assert::assertTrue($role eq "admin", "Need to be logged in as admin");

	Format::createHeader("Screen > Status", "", "js/validate.js");
	showSharedMenu($session);

	if ($q->param("update")) {
		my $status = $q->param("update");
		my $reference = $q->param("reference");
		Format::createFreetext("The status of submission $reference has been changed to <em>$status</em>.");
		Shepherd::changeStatus($timestamp, $reference, $status);
	} 

	print <<END;
	<p>
	<em>The status of all papers is shown below. To change the status of a paper click on one of the labels below the paper title.</em><br>
	<em>Note: <b>No</b> email is sent to the authors when you change the status of a submission.</em>
	</p>
END

	my %records = Records::getAllRecords(Records::listCurrent());
	foreach $label (
		sort { $records{$a}->param("track") <=> $records{$b}->param("track") }
			sort { $records{$a}->param("reference") <=> $records{$b}->param("reference") } 
				keys %records) {
		my $record = $records{$label};	
		if (canSeeRecord($user, $role, $label)) {	
			showStatusUpdater($session, $user, $record, $label);
		}
	} 

	Format::createFooter();
}

sub showStatusUpdater {
	my ($session, $user, $record, $label) = @_;
	
	my $track = $record->param("track");
	if ($currentTrack != $track) {
		Format::createFreetext("<h3>" . $config->{"track_" . $track} . "</h3>");
		$currentTrack = $track;
	}
			
	print <<END;
	<table border="0" cellpadding="2" cellspacing="10" width="100%">
		<tbody>
END
	
	showStatusReferenceTitle($session, $record);
	showStatus($session, $record);
	
	print <<END;
		</tbody>
	</table>
END
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

sub showSharedMenu {
	my ($session) = @_;
	
	print <<END;
	<p>[ <a href="gate.cgi?action=menu&session=$session">Menu</a> ]</p>
END
}

# TODO: make more efficient by computing once only
sub canSeeRecord {
	my ($user, $role, $label) = @_;
	if ($config->{"pc_can_screen_all"}) {
		return 1; 			# if pc_can_screen_all, allow all pc to see all records
	}
	# if ($role eq "admin") {
	if (Role::hasRole($user, $CONFERENCE_ID, "admin")) {
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
	$byline =~ s|\r\n|, |g;		# TODO: check if still needed
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
} elsif ($action eq "status") {
	handleStatus();
} else {
	handleError("No such action");
}
