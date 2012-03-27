package Records;

use lib '.';
use CGI;

sub getRecord {
	my ($name) = @_;
	open FILE, "data/records/$name" ||
    	::handleError("Internal: could not read submission record");
    my $q_saved = new CGI(FILE);
    close FILE;
    return $q_saved;
}

sub getAllRecords {
	my (%names) = @_;
	my %records;
	foreach $label (values %names) {
		$records{$label} = getRecord($label);
	}
	return %records;
}

sub list {
    opendir DIR, "data/records" ||
    	::handleError("Internal: could not search submission records");
	my @records = grep(/\d+/, readdir DIR);
    closedir DIR;	
    return sort @records;
}

sub listCurrent {
	my @records = list();
	my %cur;
	foreach (@records) {
		if (/_(\d+)$/) {		# record name ends in reference
			$cur{$1} = $_;		# will overwrite previous versions
		}
	}
	return %cur;				# contains current versions
}

sub listPrevious {
	my @records = list();
	my %cur;
	my %pre;
	foreach (@records) {
		if (/_(\d+)$/) {
			$pre{$1} = $cur{$1};
			$cur{$1} = $_;
		}
	}
	return %pre;
}

sub listAllVersions {
	my ($reference) = @_;
	my @records = list();
	my @versions;
	foreach (@records) {
		if (/_$reference$/) {		# record name ends in reference
			push (@versions, $_);
		}
	}
	return @versions;
}


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

1;