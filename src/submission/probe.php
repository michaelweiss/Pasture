<?php
echo "<p>OK</p>";

# $path = exec("which perl");
# echo "<p>perl lives at $path</p>";

# $path = exec("ls -l /etc/apache2/apache2.conf");
# echo "<p>httpd.conf is at $path</p>";

# $conf = file_get_contents("/etc/apache2/apache2.conf");
# echo "<pre>$conf</pre>";

exec("ls -l /etc/apache2/sites-available/ >/tmp/sites");
$sites = file_get_contents("/tmp/sites");
echo "<pre>$sites</pre>";

# $conf = file_get_contents("/etc/apache2/sites-available/test.hillside.net.conf");
# echo "<pre>$conf</pre>";
?>