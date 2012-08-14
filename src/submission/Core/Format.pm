package Format;

our $TEMPLATE = "data/html/header.html";

sub createHeader {
	my ($title, $body_title, $validate, $no_framecheck) = @_;
	createHeaderWithTemplate($TEMPLATE, $title, $body_title, $validate, $no_framecheck);	
}

sub createHeaderWithTemplate {
	# DONE: ignore framecheck
	my ($template, $title, $body_title, $validate, $no_framecheck) = @_;
	print $::q->header("text/html");
	print applyTemplate($template, {
		title => $title,
	});	
	if ($body_title) {
		print $::q->h1($body_title);
	} else {
		print $::q->h1($title);
	}
}

sub applyTemplate {
	my ($template, $attributes) = @_;
	my $page = "";
	open (TEMPLATE, "<$template") ||
		# must use handleUnexpectedError, as handleError invokes createHeader
		Audit::handleUnexpectedError("Can't find template: $template");
	while (<TEMPLATE>) {
		s/\$(\w[\w\d]*)/$attributes->{$1}/gi;
		$page .= $_;
	}
	close (TEMPLATE);
	return $page;
}

sub createFooter {
	createFooterWithTemplate("data/html/footer.html");
}

sub createFooterWithTemplate {
	my ($template) = @_;
	print applyTemplate($template);
}

sub startForm {
	my ($method, $action, $validate, $target) = @_;
	print <<END;
<form method="$method" onSubmit="$validate" target=$target>
END
	if ($action) {
		print <<END;
<input name="action" type="hidden" value="$action"/>
END
	}
}

sub startMultiPartForm {
	my ($method, $action, $validate) = @_;
	print <<END;
<form method="$method" enctype="multipart/form-data" onSubmit="$validate">
<input name="action" type="hidden" value="$action"/>
END
}

sub endForm {
	my ($submit, $cancel) = @_;
	if ($cancel) {
		print <<END;
<p><input type="submit" value="$submit"/> <input type="reset" value="$cancel"/></p>
</form>
END
	} else {
		print <<END;
<p><input type="submit" value="$submit"/></p>
</form>
END
	}
}

sub createAction {
	my ($condition, $url, $action, $reason) = @_;
	if ($condition) {
		print <<END;
<li><a href="$url">$action</a></li>
END
	} else {
		print <<END;
<li>$action ($reason)</li>
END
	}
}

sub createText {
	my ($label, $name, $size, $default) = @_;
	unless ($default) {
	print <<END;
<p>$label: <input name="$name" type="text"/ size="$size"></p>
END
	} else {
	print <<END;
<p>$label: <input name="$name" type="text"/ size="$size" value="$default"></p>
END
	}
}

sub createTextWithTitle {
	my ($title, $label, $name, $size, $default) = @_;
	if ($title) {
		print <<END;
<h3>$title</h3>
END
	}
	unless ($default) {
	print <<END;
<p><dd>$label</dd></p>
<p><dd><input name="$name" type="text"/ size="$size"></dd></p>
END
	} else {
	print <<END;
<p><dd>$label</dd></p>
<p><dd><input name="$name" type="text"/ size="$size" value="$default"></dd></p>
END
	}
}

sub createTextBoxWithTitle {
    my ($title, $label, $name, $size, $height, $default) = @_;
    if ($title) {
        print <<END;
<h3>$title</h3>
END
    }
    unless ($default) {
    print <<END;
<p><dd>$label</dd></p>
<p><dd>
<textarea name="$name" cols="$size" rows="$height"></textarea>
</dd></p>
END
    } else {
    print <<END;
<p><dd>$label</dd></p>
<p><dd>
<textarea name="$name" cols="$size" rows="$height">$default</textarea>
</dd></p>
END
    }
}

sub createPassword {
	my ($label, $name, $size) = @_;
	print <<END;
<p>$label: <input name="$name" type="password"/ size="$size"></p>
END
}

sub createPasswordWithTitle {
	my ($title, $label, $name, $size) = @_;
	if ($title) {
		print <<END;
<h3>$title</h3>
END
	}
	print <<END;
<p><dd>$label:</dd></p>
<p><dd><input name="$name" type="password"/ size="$size"></dd></p>
END
}

sub createTextArea {
	my ($label, $name, $cols, $rows, $default) = @_;
	print <<END;
<p>$label:<br/>
<textarea name="$name" cols="$cols" rows="$rows">$default</textarea></p>
END
}

sub createTextAreaWithTitle {
	my ($title, $label, $name, $cols, $rows, $default) = @_;
	print <<END;
<h3>$title</h3>
<p><dd>$label</dd></p>
<p><dd><textarea name="$name" cols="$cols" rows="$rows">$default</textarea></dd></p>
END
}

sub createRadioButton {
	my ($name, $value, $label, $checked) = @_; 
	if ($checked) {
	print <<END;
<p><input name="$name" type="radio" value="$value" checked/> $label</p>
END
	} else {
	print <<END;
<p><input name="$name" type="radio" value="$value"/> $label</p>
END
	}
}

sub createRadioButtonsWithTitle {
	my ($title, $label, $name, @values) = @_;
	print <<END;
<h3>$title</h3>
<p><dd>$label</dd></p>
END
	my $checked = $values[-1] unless ($#values % 2);	
	for ($i=0; $i<$#values; $i+=2) {
		# DONE: why is checked radio button not checked?
		if ($values[$i] eq $checked) {
			print <<END;
<p><dd><input name="$name" type="radio" value="$values[$i]" checked/> $values[$i+1]</dd></p>
END
		} else {
			print <<END;
<p><dd><input name="$name" type="radio" value="$values[$i]"/> $values[$i+1]</dd></p>
END
		}
	}
}

sub createRadioButtonsWithTitleOnOneLine {
	my ($title, $label, $name, @values) = @_;
	print <<END;
<h3>$title</h3>
<p><dd>$label</dd></p>
<p><dd>
END
	my $checked = $values[-1] unless ($#values % 2);	
	for ($i=0; $i<$#values; $i+=2) {
		# DONE: why is checked radio button not checked?
		if ($values[$i] eq $checked) {
			print <<END;
<input name="$name" type="radio" value="$values[$i]" checked/> $values[$i+1] &nbsp;
END
		} else {
			print <<END;
<input name="$name" type="radio" value="$values[$i]"/> $values[$i+1] &nbsp;
END
		}
	}
	print <<END;
</dd></p>
END
}

sub createMenuWithTitle {
	my ($title, $label, $name, @values) = @_;
	print <<END;
<h3>$title</h3>
<p><dd>$label</dd></p>
<dd><select name="$name">
END
	my $checked = $values[-1] unless ($#values % 2);	
	for ($i=0; $i<$#values; $i+=2) {
		# DONE: why is checked radio button not checked?
		if ($values[$i] eq $checked) {
			print <<END;
	<option name="$name" value="$values[$i]" selected/> $values[$i+1]
END
		} else {
			print <<END;
	<option name="$name" type="radio" value="$values[$i]"/> $values[$i+1]
END
		}
	}
	print <<END;
</select></dd>
END
}

sub createCheckboxWithTitle {
	my ($title, $label, $name, @values) = @_;
	print <<END;
<h3>$title</h3>
<p><dd>$label</dd></p>
END
	my $checked = $values[-1] unless ($#values % 2);	
	for ($i=0; $i<$#values; $i+=2) {
		if ($values[$i] eq $checked) {
			print <<END;
<p><dd><input name="$name" type="checkbox" value="$values[$i]" checked/> $values[$i+1]</dd></p>
END
		} else {
			print <<END;
<p><dd><input name="$name" type="checkbox" value="$values[$i]"/> $values[$i+1]</dd></p>
END
		}
	}
}

sub createCheckboxesWithTitleOnOneLine {
	my ($title, $label, $name, @values) = @_;
	print <<END;
<h3>$title</h3>
<p><dd>$label</dd></p>
<p><dd>
END
	my $checked = $values[-1] unless ($#values % 2);	
	for ($i=0; $i<$#values; $i+=2) {
		if ($values[$i] eq $checked) {
			print <<END;
<input name="$name" type="checkbox" value="$values[$i]" checked/> $values[$i+1] &nbsp;
END
		} else {
			print <<END;
<input name="$name" type="checkbox" value="$values[$i]"/> $values[$i+1] &nbsp;
END
		}
	}
	print <<END;
</dd></p>
END
}

sub createFileUpload {
	my ($title, $label, $name, $size) = @_;
	print <<END;
<h3>$title</h3>
<p><dd>$label</dd></p>
<p><dd><input name="$name" type="file" size="$size"/></dd></p>
END
}

sub createFreetext {
	my ($label) = @_;
	print <<END;
<p>$label</p>
END
}

sub createHidden {
	my ($name, $value) = @_;
	print <<END;
<input name="$name" type="hidden" value="$value"/>
END
}

# trim leading and trailing blanks from query parameters
# this seemingly simple task requires heavy lifting, eg using -overrides
sub sanitizeInput {
	# using -override parameters is described in perldoc:
	# http://perldoc.perl.org/CGI.html#SETTING-THE-VALUE(S)-OF-A-NAMED-PARAMETER%3a
	my ($name, $value);
	foreach $name ($::q->param()) {
		my @trimmedValues = 
			map { trim($_) } $::q->param($name);
		$::q->param(-name => $name, 
			-values => \@trimmedValues);
	}	
}

sub trim {
	my $s = shift;
	$s =~ s/^\s+//;
	$s =~ s/\s+$//;
	return $s;

}

# ----- >8 ------

sub createHeader_ {
	# DONE: ignore framecheck
	my ($title, $body_title, $validate, $no_framecheck) = @_;
	print $::q->header("text/html");
	unless ($validate) {
		# TODO: read html header from template instead
		print $::q->start_html(-title => $title, 
			-style =>  "../style.css",
		);
	} else {
		# TODO: read html header from template instead
		print $::q->start_html(-title => $title, 
			-style => "../style.css",
			-script => [
				{ 
					-language => "JavaScript", 
					-src => $validate 
				},
			],
		);
	}
	if ($body_title) {
		print $::q->h1($body_title);
	} else {
		print $::q->h1($title);
	}
}

sub createHeaderNoStyle {
	# DONE: ignore framecheck
	my ($title, $body_title, $validate, $no_framecheck) = @_;
	print $::q->header("text/html");
	unless ($validate) {
		print $::q->start_html(-title => $title, 
		);
	} else {
		print $::q->start_html(-title => $title, 
			-script => [
				{ 
					-language => "JavaScript", 
					-src => $validate 
				},
			],
		);
	}
	if ($body_title) {
		print $::q->h1($body_title);
	} else {
		print $::q->h1($title);
	}
}

sub createFooter_ {
	print $::q->end_html();
}

sub dumpParams {
	print "<pre>\n";
	my ($name, $value);
	foreach $name ($::q->param()) {
		print "$name: ";
		my @values = $::q->param($name);
		print "[ ", join(' ', @values), " ]\n";
		foreach $value ($::q->param($name)) {
			print "  $value\n";
		}
	}
	print "</pre>\n";
}

# ----- >8 ------

1;
