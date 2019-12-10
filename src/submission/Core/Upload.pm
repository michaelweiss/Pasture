package Upload;

use lib '.';
use Core::Serialize;

my $UPLOAD_DIR = "papers";				# TODO: move to a "safe" location

$CGI::POST_MAX = 20 * 1024 * 1024;		# Limit uploads to 20 MB

my $MAX_DIR_SIZE = 250 * 1024 * 1024;	# Maximum upload directory size. Limit total uploads to 250 MB
my $MAX_OPEN_TRIES = 100;				# Number of times we attempt create a unique filename
	
# Create directory for submitted papers, if one does not exist
unless (-e "papers") {
	mkdir("papers", 0755) || 
		Audit::handleError("Cannot create papers directory");
}
									
sub save {
	my ($path) = @_;

	# check file type
	
	# DONE: relax by checking for extension of file (to deal with browsers
	# that don't set the correct content type)

#	NOTE: Used this code previously to check content type
#	my $info = $::q->uploadInfo($path);
#	unless ($info->{"Content-Type"} =~ /application\/(pdf|msword)/) {
#		::handleError("Can only upload PDF or Word documents: " + $path);
# 	}

	$path =~ /(\.\w+)$/ || ::handleError("Bad file extension");
	my $fileExtension = $1;	
	unless ($fileExtension eq ".doc" || $fileExtension eq ".docx" || $fileExtension eq ".pdf" ||
		$fileExtension eq ".txt" ||		# 09-02-12 mw added support for .txt files
		$fileExtension eq ".zip") {		# 09-05-19 mw added support for .zip files
		::handleError("Can only upload PDF, Word, and text documents or ZIP files: " . $path);
	}

#	print "<p>path: $path</p>";
#	print "<p>length: $ENV{CONTENT_LENGTH}</p>";
	
	# DONE: check directory size
	if (directorySize($UPLOAD_DIR) + $ENV{CONTENT_LENGTH} > $MAX_DIR_SIZE) {
		::handleError("Upload directory is full. Please inform $::WEBCHAIR_EMAIL.");
	}
	
	# DONE: create a reference for a new submission
	unless ($::q->param("reference")) {
		$::q->param("reference" => Serialize::getReference());
	}

	# DONE: construct file name from reference
	unless ($::q->param("reference") =~ /(\d+)/) {
		::handleError("Bad reference");
	}
	my $reference = $1;
	my $fileName = $reference . $fileExtension;
	
	# get file handle
	my $fh = $::q->upload("paper") ||
		::handle("Could not obtain file handle: $h");
	unless ($fh) {
		::handleError("Invalid file");
	}
	my $size = fileSize($fh);
#	print "<p>File size: $size</p>";

	# DONE: find unique file name
	# DONE: replace sysopen with open (which works), and check for existing file names with -e
	# TODO: protect against race condition (-e, other process: -e, both open same file)
	# MOVE: if one version in .doc, the other in .pdf they are not treated as separate versions,
	# because currently I am only checking for existence of $ref.$type, whereas I should check for
	# $ref.ANY (ANY = any of the allowed formats)
	my $version;
	while (-e "$UPLOAD_DIR/$fileName") {
		if ($fileName =~ /(.+\.)(\d*)(\.\w+)$/) {
			$version = $2 + 1;
			$fileName = $1 . $version . $3;
			if ($version >= $MAX_OPEN_TRIES) {
				::handleError("Unable to save your file: $fileName");
			}
		} else {
			$fileName =~ s/(\.\w+)$/\.1$1/;
			$unique = 1;
		}
	}
		
	# DONE: write contents to output file
	binmode FILE;
	open FILE, ">papers/$fileName" ||
		::handleError("Unable to save your file: $fileName");
	while (<$fh>) {
		print FILE;
	}
	close FILE;

	my @status = ($fileName, $size, $version);
	return @status;
}

# Utilities

sub directorySize {
	my ($directory) = @_;
	my $total = 0;
	open DIR, $directory || die $!;
	while (readdir DIR) {
		$total += -s "$directory/$_";
	}
	return $total;
}

sub fileSize {
	my ($fh) = @_;
	seek($fh, 0, 2);					# move position to end of file
	my $size = tell($fh);
	seek($fh, 0, 0);					# reset position
	return $size;
}

# Debug

sub tmpFileName {
	# uses private API of CGI.pm
	my ($path) = @_;
	my $fileName = $::q->tmpFileName($path);
	print "<p>Save: $fileName</p>";
}

sub copyTmpFile {
	# uses private API of CGI.pm
	my ($path, $to) = @_;
	my $fileName = $::q->tmpFileName($path);
	copy($from, $to);
}

sub uploadInfo {
	my ($path) = @_;
	::dumpRecord($::q->uploadInfo($path));
}

1;
