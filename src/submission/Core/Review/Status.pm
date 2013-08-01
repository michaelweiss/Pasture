package Status;

use CGI;

use lib '.';
use Core::Assign;
use Core::Screen;
use Core::Audit;

my %assignments = Assign::loadAssignments();
my %votes = %{Screen::votes()};

sub createReport {
  print "<h2>Review status</h2>\n";
  showReviewStatus();

  print "<h2>Review by</h2>\n";
  showReviewersForEachPaper();
}

sub showReviewStatus {
  print "<table border='0'><tbody>\n";
  foreach $reviewer (reviewers()) {
    print "<tr>";
    print "<td>$reviewer</td><td width='20'></td><td>";
    foreach $reference (papersAssignedToReviewer($reviewer)) {
      if (hasReviewed($reviewer, $reference)) {
        print "<span style='color: green'>$reference</span>";
      } else {
        print "<span style='color: red'>$reference</span>";
      }
      print " &nbsp; ";
    }
    print "</td></tr>\n";
  }
  print "</tbody></table>\n";
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
  print "<table border='0'><tbody>\n";
  foreach $reference (references()) {
    print "<tr>";
    print "<td>$reference</td><td width='20'></td><td>";
    foreach $reviewer (reviewersForPaper($reference)) {
      print "$reviewer &nbsp; ";
    }
    print "</td></tr>\n";
  }
  print "</tbody></table>\n";
}

sub references {
  return sort { $a <=> $b } keys %votes;
}

sub reviewersForPaper {
  my ($reference) = @_;
  return sort keys %{$votes{$reference}};
}

1;