<?php
// configuration data
$config = parse_ini_file("data/config.dat");
$conference = $config["conference"];
$program_chair_email = $config["program_chair_email"];
$conference_chair_email = $config["conference_chair_email"];
$web_chair_email = $config["web_chair_email"];
$url = $config["url"];

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
								// TODO: remove file	if ($fh == false) {
		echo "No such email";
	} else {		$message = fread($fh, fileSize($body));		fclose($fh);
		
		if ($debug) {
			// settings for testing
			$to = $web_chair_email;
			$headers = 'From: ' . $web_chair_email . "\r\n" .
		    	'X-Mailer: PHP/' . phpversion();
		} else {	
			// settings for actual use
			$to = $email;
			if ($cc == $program_chair_email) {
				// can happen if program chair is track chair
				$cc = "";
			}
			if ($to == $program_chair_email) {
				// only send one email to program chair
				$cc = "$conference_chair_email" . "," . $cc;
			} else {
				$cc = "$program_chair_email" . "," . $conference_chair_email . "," . $cc;
			}
			$headers = 'From: ' . $program_chair_email . "\r\n" .
				'CC: ' . $cc . "\r\n" .
				'Reply-To: ' . $program_chair_email . "," . $conference_chair_email . "\r\n" .
				'BCC: ' . $web_chair_email . "\r\n" .
				'X-Mailer: PHP/' . phpversion();
		}
		
		$status = mail($to, $subject, "$message", $headers);
		if ($status) {
			echo "Email sent";
		} else {
			echo "Could not send email";
		}
	}
}
?>
