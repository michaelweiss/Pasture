package Tags;

use lib '.';
use Core::Format;
use Core::Serialize;
use Core::Serialize::Records;

my @stopWords = ("the", "do", "would", "it", "is", "not");

# Add a tag to the tag database
sub add {
	my ($tag) = @_;
	my @tags = split(/,/, $tag);
	foreach (@tags) {
		addSingleTag($_);
	}
}
	
sub addSingleTag {
	my ($tag) = @_;
	$tag = _normalize($tag);
	unless ($tag) {
		return;		# if tag is empty
	}
	_lock("data", "tags");
	my %tags;
	dbmopen(%tags, "data/tags", 0666) ||
		::handleError("Internal: cannot open tag database");
	$tags{$tag}++;
	dbmclose(%tags);
	_unlock("data", "tags");
}

# Remove a tag from the tag database 
sub removeAll {
	my ($tag) = @_;
	$tag = _normalize($tag);
	_lock("data", "tags");
	my %tags;
	dbmopen(%tags, "data/tags", 0666) ||
		::handleError("Internal: cannot open tag database");
	# delete removes all occurrences
	delete $tags{$tag};
	dbmclose(%tags);
	_unlock("data", "tags");
}

sub remove {
	my ($tag) = @_;
	$tag = _normalize($tag);
	_lock("data", "tags");
	my %tags;
	dbmopen(%tags, "data/tags", 0666) ||
		::handleError("Internal: cannot open tag database");
	unless (--$tags{$tag} > 0) {
		delete $tags{$tag};
	}
	dbmclose(%tags);
	_unlock("data", "tags");
}

# Return a hash with the most frequent tags
sub tags {
	my ($length) = @_;		# if specified, only show the top most frequent tags
	_lock("data", "tags");
	my %tags;
	dbmopen(%tags, "data/tags", 0666) ||
		::handleError("Internal: cannot open tag database");
	my @keys;
	if ($length > 0) {
		@keys = sort {$tags{$b} <=> $tags{$a}} keys %tags;
		@keys = @keys[0..$length-1];
	} else {
		@keys = keys %tags;
	}
	my %copy;
	foreach $tag (@keys) {
		$copy{$tag} = $tags{$tag};
	}
	dbmclose(%tags);
	_unlock("data", "tags");
	return %copy;
}

# Check if database exists
sub existsTagDatabase {
	return (-e "data/tags.db" || -e "data/tags.pag" || -e "data/tags.dir");
}

# Ensure tag database exists, populate it if necessary
sub ensureTagDatabase {
	unless (existsTagDatabase()) {
		populate();
	}
}

# Populate database from scratch
sub populate {
	# TODO: clear tag database
	my %records = Records::listCurrent();
	foreach $ref (keys %records) {
		my $name = $records{$ref};
		my $record = Records::load($name);
		addTags($record);
	}
}

sub addTags {
	my ($record) = @_;
	my $tags = $record->param("tags");
	foreach $tag (split(/\n/, $tags)) {
		Tags::add($tag);
	}
}

sub addTagsFromAbstract {
	my ($record) = @_;
	my $tags = $record->param("abstract");
	foreach $tag (split(/ /, $tags)) {
		Tags::add($tag);
	}
}

# Create a tagcloud using logarithmic mapping of frequencies (assumes that 
# you define classes tagcloud_[0..9] somewhere in a stylesheet)
sub tagcloud {
	my ($length) = @_;		# if specified, only show the top most frequent tags
	my $min = $max = -1;
	my %tags = tags($length);
	foreach $tag (keys %tags) {
		if ($min == -1) {
			$min = $tags{$tag};
			$max = $min;
		} elsif ($min > $tags{$tag}) {
			$min = $tags{$tag};
		} elsif ($max < $tags{$tag}) {
			$max = $tags{$tag};
		}
	}
	# skip if no tags in tag database
	if ($min <= 0 || $max <= 0) {
		print <<END;
<div id="tagcloud"></div>
END
		return;
	}
	$min = log($min);
	$max = log($max);
	
	print <<END;
<div id="tagcloud">
END
	foreach $tag (sort keys %tags) {
		my $size = _size($min, $max, $tags{$tag});
		print <<END;
<a class="tagcloud_$size" href="javascript:selectedTag('$tag')">$tag</a> &nbsp;
END
	}
	print <<END;
</div>
END
}

# Subservient functions

# Returns a value in the range 0..9, where 0 is assigned to tags with the
# lowest frequency, and 9 to tags with the highest frequency
sub _size {
	my ($min, $max, $value) = @_;
	if ($max == $min) {
		return 9;	# if width of range is 0, return maximum rank
	}
	$value = log($value);
	return int(9*($value-$min)/($max-$min));
}

# Utilities

# Obtain a lock on a resource (file, database, ...)
sub _lock {
	my ($directory, $resource) = @_;
	open(LOCK, ">$directory/$resource.lock");
	flock(LOCK, $LOCK);
}

# Release a lock on a resource acquired by _lock()
sub _unlock {
	my ($directory, $resource) = @_;
	unlink("$directory/$resource.lock");
}

# Normalize tag
# Includes: remove extraneous spaces and convert to lower case
sub _normalize {
	my ($tag) = @_;
	$tag = Format::trim($tag);
	$tag = lc $tag;
	if ($tag =~ /example would/m ||
		$tag =~ /do not/m) {
		return "";
	}
	return $tag;
}

1;
