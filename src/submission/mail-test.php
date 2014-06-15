<?php
	// configuration data
	$config = parse_config();
	$conference = $config["conference"];
	$program_chair_email = $config["program_chair_email"];
	$conference_chair_email = $config["conference_chair_email"];
	$web_chair_email = $config["web_chair_email"];
	$url = $config["url"];	

	// create email
	$to = $web_chair_email;
	$subject = "test";
	$message = "Welcome to " . $conference;
	$headers = "From: " .  $web_chair_email . "\r\n" . 
		"CC: " . $program_chair_email;
	
	// send email
	$status = mail($to, $subject, $message, $headers);
	if ($status) {
		echo "Email sent to: ", $to;
	} else {
		echo "Could not send email";
	}

	function parse_config() {
		$file = fopen("data/config.dat", "rb");
		while (!feof($file) ) {
			$line = explode('=', chop(fgets($file)));
			$config[$line[0]] = $line[1];
			/* echo $line[0], " ", $line[1], "<br>"; */
		}
		fclose($file);
		return $config;
	}
?>