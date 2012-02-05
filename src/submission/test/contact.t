#!/usr/bin/perl

use Core::Contact;

sub setup {
	unlink("data/contacts.dat");
}

sub testCreateContact {
	print "testCreateContact\n";
	Contact::saveContact("bob", "bob\@email.com");
	my %contact = Contact::loadContact("bob");
	$contact{"email"} eq "bob\@email.com" || die "email does not match: " . $contact{"email"};
}

sub testUpdateContact {
	print "testUpdateContact\n";
	Contact::saveContact("bob", "bob\@newemail.com");
	my %contact = Contact::loadContact("bob");
	$contact{"email"} eq "bob\@newemail.com" || die "email does not match: " . $contact{"email"};
}

sub testAllContacts {
	print "testAllContacts\n";
	Contact::saveContact("bob", "bob\@email.com");
	Contact::saveContact("alice", "alice\@email.com");
	Contact::saveContact("sue", "sue\@email.com");
	my @contacts = Contact::loadAllContacts();
	$#contacts == 3-1 || die "array does not have 3 elements: " . @contacts;
}

setup();
testCreateContact();
testUpdateContact();

setup();
testAllContacts();
