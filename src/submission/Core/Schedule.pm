package Schedule;

use CGI;
use LWP;
use URI;

use lib '.';
use Core::Audit;

our $config = Serialize::getConfig();

# URL of CSV file that contains the workshop assignments
my $WORKSHOPS_URL = $config->{"workshops_url"};

=pod
Fetch the list of scheduled papers.
=cut

sub getScheduledPapers {
	getScheduledPapersFromFile();	
}

=pod
Fetch the list of scheduled papers from the Google spreadsheet.
=cut

# DONE: fix problem where each record in the CSV is split into two lines due to a newline in
# a string (so the line is actually split in to, and even Text::CSV can't help

sub getScheduledPapersFromGoogleDocs {
	my $browser = LWP::UserAgent->new();
	my @lines = split(/\n/, $browser->get($WORKSHOPS_URL)->content());
	my $recordLine = 1;
	my $paper = "";
	foreach (@lines) {
		if ($recordLine == 1) {
			$paper = $_;
			$recordLine = 2;
		} else {
			$paper .= $_;
			$recordLine = 1;
			# kludge: this paper should really have been removed from the spreadsheet
			unless ($paper =~ /^WG-S6/) {
				push (@papers, $paper);
			}
		}
	}	
	return @papers;
}

=pod
Fetch the list of scheduled papers from a spreadsheet
=cut

sub getScheduledPapersFromSpreadsheet {
	open(PAPERS, $config->{"workshops_spreadsheet"}) ||
		Audit::handleError("Cannot read workshop assignments");
	my $first = 1;
	my @papers;
	while (<PAPERS>) {
		unless ($first) {
			push (@papers, $_);
		} else {
			$first = 0;		# ignore column headers
		}
	}
	close(PAPERS);
	return @papers;
}

=pod
Fetch the list of scheduled papers from file with following format:
A) Business and Organization: 1, 7, 11, 19,  40, *37*
B) Software: 16, 20, 21, 22, 30, *18*
...
=cut

sub getScheduledPapersFromFile {
	open(PAPERS, $config->{"workshops_spreadsheet"}) ||
	Audit::handleError("Cannot read workshop assignments");
	my @papers;
	while (<PAPERS>) {
		chomp;
		my ($lhs, $rhs) = split(/:/);
#		print "lhs: $lhs\n";
#		print "rhs: $rhs\n";
		my ($workshop, $workshopName) = $lhs =~ /(\w)\) (.+)/;
#		print "workshop: $workshop\n";
#		print "workshop name: $workshopName\n";
		my $reference;
		foreach $reference (split(/, /, $rhs)) {
			if ($reference =~ /\*(\d+)\*/) {
				$reference = $1;
#				print "* reference: $reference\n";
				$decision = "WG";
			} else {
				$reference =~ s/ //g;
#				print "  reference: $reference\n";
				$decision = "WW";
			}
			push (@papers, "$reference,$workshop,$workshopName,$decision");
		}
	}
	close(PAPERS);
	return @papers;
}

=pod
Convert csv to list
=cut

sub csvToList {
	my ($text) = @_;
	# source: http://codesnippets.joyent.com/posts/show/18
	my @new  = ();
    push(@new, $+) while $text =~ m{
        # the first part groups the phrase inside the quotes.
        "([^\"\\]*(?:\\.[^\"\\]*)*)",?
           |  ([^,]+),?
           | ,
       }gx;
   	push(@new, undef) if substr($text, -1, 1) eq ',';
   	return @new;
}

1;
