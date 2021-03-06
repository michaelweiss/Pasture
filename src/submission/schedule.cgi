#!/usr/bin/perl -wT
use CGI;
use CGI::Carp qw( fatalsToBrowser );
use URI::Escape ('uri_escape');
use Time::Local;

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
use Core::Audit;
use Core::Review;
use Core::Shepherd;
use Core::Decision;
use Core::Schedule;

our $q = new CGI;
our $timestamp = time();

our $script = "schedule.cgi";

# General initialization

our $config = Serialize::getConfig();
our $WEBCHAIR_EMAIL = $config->{"web_chair_email"};
our $CONFERENCE = $config->{"conference"};
our $CONFERENCE_ID = $config->{"conference_id"};
our $CONFERENCE_WEBSITE = $config->{"conference_website"};
our $baseUrl = $config->{"url"};

BEGIN {
	CGI::Carp::set_message( \&Audit::handleUnexpectedError );
}

# Only show schedule if this flag is set
my $SCHEDULE_OPEN = $config->{"schedule_open"};

# Handlers

sub handleWorkshops {
	Format::createHeader("Schedule > Workshops", "", "");
	
	my %records = Records::getAllRecords(Records::listCurrent());
	my %recordsByRef;
	foreach $label (keys %records) {
		$recordsByRef{$records{$label}->param("reference")} = $records{$label};
	}

	# get the list of papers from a csv file
	# my @papers = Schedule::getScheduledPapersFromFile();
	my @papers = Schedule::getScheduledPapers();
	
	# output the papers in the order: workshops first, then writing groups
	my $label = 'A';
	my $order = 1;
	my $currentWorkshop;
	print "<p>The papers have been assigned to workshops. Note that papers prefixed with a * have been assigned to an onsite shepherding group. Their content will still change during the conference.</p><br/>\n";

	foreach (@papers) {
		# trim extra spaces (several situations as follows)
		s/ ,/,/g;
		s/ ",/",/g;
						
		# get the information about the next paper
		# my ($workshop, $theme, $reference, $authors, $title, $email, $updateReceived) = Schedule::csvToList($_);
		# my ($reference, $email, $_registered, $title, $decision, $_type, $workshop, $_alt, $shepherd, $pc) = Schedule::csvToList($_);
		# my ($reference, $_name, $title, $decision, $_type, $workshop, 
		#	$shepherd, $pc, $tags) = Schedule::csvToList($_);
		my ($reference, $workshop, $_name, $decision) = Schedule::csvToList($_);
		unless (0) {	# filter condition: NA here
			# TODO: writing group if stars surround the reference
			# detect writing group status and extract reference from label
			my $inWritingGroup = ($decision eq "WG") ? 1 : 0;
			
			# write entry for this paper
			if ($label && $order) {
				# if this is the first paper in the workshop, create a preamble
				unless ($currentWorkshop eq $workshop) {
					if ($currentWorkshop) {
						print "</ul><br/>\n";
						$label++;	# advance label (A, B, ...)
					}
					my $workshopLeader = unicode($config->{lc "workshop_${label}_leader"});
					my $workshopName = unicode($config->{lc "workshop_${label}_name"});
					
					my $archive = $config->{lc "workshop_${label}_name"} . ".zip";
				    $archive =~ s/\s//g;
				    
					# todo: need to rename link to zip file?
					# todo: can we create the zip file automatically (cpan?)
					print <<END;
<h2>Writers' Workshop $label &#8211; $workshopName</h2>
<p>Download all workshop papers: <!-- <a href="/europlop/workshops/$archive">$archive</a> --> $archive<br>
<b>Workshop Leader:</b> $workshopLeader</p>
<p><b>Papers:</b></p>
END
					print "<ul>\n";
					$currentWorkshop = $workshop;
					$order = 1;
				}
				
				my $record = $recordsByRef{$reference};
				if ($record) {
					$authors = Review::getAuthors($record);
				} else {
					$authors = "NA";
				}
				my $authors = unicode($authors);
				
				my $title = unicode($record->param("title"));
				print "\t<li>";
				if ($inWritingGroup) {
					print "*";
				}
				print "$label$order: $authors, ", downloadLink($reference, $title), 
					" <font	size='-2' color='grey'>(updated on ", lastUpdated($reference), ")</font> </li>\n";
				if ($inWritingGroup) {
					$writingGroup{"$label-$order"} = $_;
				}
				$order++;
			}
		}
	}
	
	# output the papers in the writing group
	if ($currentWorkshop) {
		print "</ul><br/>\n";
	}
	
	Format::createFooter();
}

sub handleDblp {
	print $q->header("text/html");;
	
	my %records = Records::getAllRecords(Records::listCurrent());
	my %recordsByRef;
	foreach $label (keys %records) {
		$recordsByRef{$records{$label}->param("reference")} = $records{$label};
	}

	# get the list of papers from a csv file
	my @papers = Schedule::getScheduledPapers();
	
	# output the papers in the order: workshops first, then writing groups
	my $label = 'A';
	my $order = 1;
	my $currentWorkshop;

	foreach (@papers) {
		# trim extra spaces (several situations as follows)
		s/ ,/,/g;
		s/ ",/",/g;
						
		# get the information about the next paper
		# my ($workshop, $theme, $reference, $authors, $title, $email, $updateReceived) = Schedule::csvToList($_);
		# my ($reference, $email, $_registered, $title, $decision, $_type, $workshop, $_alt, $shepherd, $pc) = Schedule::csvToList($_);
		# my ($reference, $_name, $title, $decision, $_type, $workshop, 
		#	$shepherd, $pc, $tags) = Schedule::csvToList($_);
		my ($reference, $workshop, $_name, $decision) = Schedule::csvToList($_);
		unless (0) {	# filter condition: NA here
			# TODO: writing group if stars surround the reference
			# detect writing group status and extract reference from label
			my $inWritingGroup = ($decision eq "WG") ? 1 : 0;
			
			# write entry for this paper
			if ($label && $order) {
				# if this is the first paper in the workshop, create a preamble
				unless ($currentWorkshop eq $workshop) {
					if ($currentWorkshop) {
						print "</ul>\n";
						$label++;	# advance label (A, B, ...)
					}
					my $workshopLeader = unicode($config->{lc "workshop_${label}_leader"});
					my $workshopName = unicode($config->{lc "workshop_${label}_name"});
					
					my $archive = $config->{lc "workshop_${label}_name"} . ".zip";
				    $archive =~ s/\s//g;
				    
					# todo: need to rename link to zip file?
					# todo: can we create the zip file automatically (cpan?)
					print <<END;
<h2>Writers' Workshop $label: $workshopName</h2>
END
					print "<ul>\n";
					$currentWorkshop = $workshop;
					$order = 1;
				}
				
				my $record = $recordsByRef{$reference};
				if ($record) {
					$authors = Review::getAuthors($record);
				} else {
					$authors = "NA";
				}
				my $authors = unicode($authors);
				my @authors = split(',\s*', $authors);
				
				my $title = unicode($record->param("title"));
				print "<li>";
				my $first = 1;
				foreach $author (@authors) {
					unless ($first) {
						print "\n";
					} else {
						$first = 0;
					}
					print "$author";
				}
				print ":\n";
				print "$title.\n";
				print "$order\n";
				print "<ee>", downloadLink($reference, $title), "</ee>\n";
				print "</li>\n";
				$order++;
			}
		}
	}
	
	# output the papers in the writing group
	if ($currentWorkshop) {
		print "</ul>\n\n";
	}
}

# Utilities

sub unicode {
	my ($text) = @_;
	# source: http://ahinea.com/en/tech/perl-unicode-pack-unpack-hack.html
	$text =~ s/“/"/g;
	$text =~ s/”/"/g;
	return pack "U0C*", unpack "C*", $text;
}

my %labels = Records::listCurrent();
sub downloadLink {
	my ($reference, $title) = @_;
	my $label = $labels{$reference};
	my $token = Access::token($label);
	return "<a href=\"shepherd.cgi?token=$token&action=download&label=$label\" target=_blank>$title</a>";
}

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

my $action = $q->param("action") || "workshops";
Format::sanitizeInput();
Audit::trace($action);
if ($action eq "workshops") {
	handleWorkshops();
} elsif ($action eq "dblp") {
	handleDblp();
} else {
	Audit::handleError("No such action");
}