#!/usr/bin/perl

use Core::Review;
use Core::Role;
use Core::Contact;
use Core::User;

sub setup {
	unlink("data/roles.dat");
	unlink("data/contacts.dat");
	unlink("data/users.dat");
}

sub testAddPcMember {
	print "testAddPcMember\n";
	Role::addRole("bob", "europlop2012", "author");
	Role::addRole("bob", "europlop2012", "pc");
	
	my @roles = Role::getRoles("bob", "europlop2012");
	$roles[0] eq "author" || die "roles does not match: " . $roles[0];
	$roles[1] eq "pc" || die "roles does not match: " . $roles[1];
	
	Role::hasRole("bob", "europlop2012", "author") || 
		die "user should have role author";
	Role::hasRole("bob", "europlop2012", "pc") || 
		die "user should have role pc";
}

sub testHowToGetAllPcMembers {
	print "testHowToGetAllPcMembers\n";
	Role::addRole("alice", "europlop2012", "pc");
	Role::addRole("bob", "europlop2012", "pc");
	Role::addRole("carl", "europlop2012", "pc");
	
	my @users = Role::getUsersInRole("europlop2012", "pc");
	$users[0] eq "alice" || die "users.0 does not match: " . $users[0];
	$users[1] eq "bob" || die "users.1 does not match: " . $users[1];
	$users[2] eq "carl" || die "users.2 does not match: " . $users[2];
}

sub testGetProgramCommitteeMembers {
	print "testGetProgramCommitteeMembers\n";
	Role::addRole("alice", "europlop2012", "pc");
	Role::addRole("bob", "europlop2012", "pc");
	Role::addRole("carl", "europlop2012", "pc");
	
	my @users = Review::getProgramCommitteeMembers("europlop2012");
	$users[0] eq "alice" || die "users.0 does not match: " . $users[0];
	$users[1] eq "bob" || die "users.1 does not match: " . $users[1];
	$users[2] eq "carl" || die "users.2 does not match: " . $users[2];
}

sub testGetPcMemberInformation {
	print "testGetPcMemberInformation\n";
	Role::addRole("alice", "europlop2012", "pc");
	Contact::saveContact("alice", "alice\@email.com");
	User::saveUser("alice", "Alice", "Carroll", "Red Queen Systems", "UK");

	my $email = Review::getReviewerEmail("alice");
	$email eq "alice\@email.com" || die "email does not match: " . $email;
	
	my $name = Review::getReviewerName("alice");
	$name eq "Alice Carroll" || die "name does not match: " . $name;
}

setup();
testAddPcMember();

setup();
testHowToGetAllPcMembers();

setup();
testGetProgramCommitteeMembers();

setup();
testGetPcMemberInformation();
