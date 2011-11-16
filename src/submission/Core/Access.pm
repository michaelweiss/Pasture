package Access;

use Digest::SHA1;

use lib '.';
use Core::Serialize;

my $config = Serialize::getConfig();

sub token {
	my ($label) = @_;
	my $token = Digest::SHA1::sha1_hex($config->{"secret"}, $label);
	return $token;
}

sub check {
	my ($token, $label) = @_;
	return $token eq Digest::SHA1::sha1_hex($config->{"secret"}, $label);
}
 