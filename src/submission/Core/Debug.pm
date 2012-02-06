package Debug;

use CGI;

# Debug functions

sub dumpParameters {
	print "<hr/>\n";
	print "<ul>\n";
	foreach $name ($::q->param()) {
		my $value = $::q->param($name);
		print "<li>$name: $value</li>\n";
	}
	print "</ul>\n";
	print "<hr/>\n";
}

sub dumpRecord {
	my ($record) = @_;
	print "<hr/>\n";
	print "<ul>\n";
	foreach $name (keys %$record) {
		my $value = $record->{$name};
		print "<li>$name: $value</li>\n";
	}
	print "</ul>\n";
	print "<hr/>\n";
}

sub printEnv {
	print "<hr/>\n";
	print "<tt>\n"; 
	foreach $key (sort keys(%ENV)) { 
		print "<li> $key = $ENV{$key}"; 
   	} 
	print "<tt/><hr/>\n";
}

1;