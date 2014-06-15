<?php
// configuration data
$config = parse_config();
$web_chair_email = $config["web_chair_email"];

$debug = $config["debug"];

// TODO: extract shepherd and pc and include in email

// form data
$email = $_POST['email'];
$cc = $_POST['cc'];
$subject = $_POST['subject'];
$body = $_POST['body'];

if (preg_match("/^data\/mail\/tmp_(\d*)_(\w+).txt$/", $body) == 0) {
	echo "Incorrect email path";
} else {
	$fh = fopen($body, 'r');	// read from a temporary file
								// TODO: remove file
	if ($fh == false) {
		echo "No such email";
	} else {
		$message = fread($fh, fileSize($body));
		fclose($fh);
		
		if ($debug) {
			// settings for testing
			$to = $web_chair_email;
			$headers = "From: " . $web_chair_email . "\r\n" .
				"Reply-To: " . $web_chair_email . "\r\n" .
		    	"X-Mailer: PHP/" . phpversion();
		} else {	
			// settings for actual use
			$to = $email;
			$headers = "From: " . $web_chair_email . "\r\n" .
				"CC: " . $cc . "," . $web_chair_email . "\r\n" .
				"Reply-To: " . $web_chair_email . "\r\n" .
				"X-Mailer: PHP/" . phpversion();
		}
		
		$status = mail($to, $subject, $message, $headers);
		if ($status) {
			echo "Email sent";
		} else {
			echo "Could not send email";
		}
	}
}

function parse_config() {
	$file = fopen("data/config.dat", "rb");
	while (!feof($file) ) {
		$line = explode('=', chop(fgets($file)));	// remove trailing newline
		$config[$line[0]] = $line[1];
	}
	fclose($file);
	return $config;
}
?>
