#!/usr/bin/perl

use Core::Assign;
use Core::Screen;

my %assignments = Assign::loadAssignments();
my %votes = %{Screen::votes()};

print "Review status:\n";
showReviewStatus();

print "\n";

print "Review assignments:\n";
showReviewersForEachPaper();

sub showReviewStatus {
  foreach $reviewer (reviewers()) {
    print "$reviewer";
    foreach $reference (papersAssignedToReviewer($reviewer)) {
      print ", $reference ";
      if (hasReviewed($reviewer, $reference)) {
        print "(done)";
      } else {
        print "(missing)";
      }
    }
    print "\n";
  }
}

sub reviewers {
  return sort keys %assignments;
}

sub papersAssignedToReviewer {
    my ($reviewer) = @_;
    return @{$assignments{$reviewer}};
}

sub hasReviewed {
  my ($reviewer, $reference) = @_;
  return exists($votes{$reference}->{$reviewer})
}

sub showReviewersForEachPaper {
  foreach $reference (references()) {
    print "$reference";
    foreach $reviewer (reviewersForPaper($reference)) {
      print ", $reviewer";
    }
    print "\n";
  }
}

sub references {
  return sort { $a <=> $b } keys %votes;
}

sub reviewersForPaper {
  my ($reference) = @_;
  return sort keys %{$votes{$reference}};
}