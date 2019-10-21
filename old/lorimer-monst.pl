#!/usr/bin/perl

use warnings;
use DBI;

my $dsn = "DBI:mysql:database=nh;host=localhost";
my $dbh = DBI->connect($dsn,"derek","");

open(LOG,"/home/derek/dev/nethack/src/monst.c") or die "No es bueno: $!\n";

# brute force the whole logfile into the table

my $difficulty = 0;
my $speed = 0;
my $ac = 0;
my $mr = 0;
my $align = 0;
my $symbol = '';
my $name = '';

my $workstr = '';
my $not_looking = 1;
my $entry_found = 0;
my $mname = '';
my $count = 0;

my @resistances = ("MR_FIRE","MR_COLD","MR_SLEEP","MR_DISINT","MR_ELEC","MR_POISON",
							"MR_ACID","MR_STONE");

# clear it all out first
$query = "delete from monst";
$dbh->do($query); 

$| = 1;
print "Imported ";

while (<LOG>) {

	$work = $_;
	$count++;

	# trim off the header explanation
	next if ($count < 90);

	# if we aren't looking and we don't see an open tag, move on
	if ($not_looking && ($work !~ /MON\(/)) {
		next;
	}
	$not_looking = 0;		# well, we're looking now

	# we grab this here so the whitespace filter
	# doesn't trash things like 'gel cube', etc.
	if ($work =~ /MON\(\"(.*)\",/) {
		$mname = $1;
	}

	chomp $work;
	$work =~ s/\t//g;		# flush the tabs and newlines
	$work =~ s/\s//g;		# ...and all whitespace
	$workstr .= $work;

	# we know the end of each array looks like ),
	# so don't bother counting ( until you see that
	if ($work =~ /\),$/) {
		my $openparens = 0;
		my $position = index($workstr,'(',0);
		while ($position > -1) {
			$openparens++;
			$position = index($workstr,'(',++$position);
		}
		my $closeparens = 0;
		$position = index($workstr,')',0);
		while ($position > -1) {
			$closeparens++;
			$position = index($workstr,')',++$position);
		}
		if ($openparens > 0 && $openparens == $closeparens) {
			$entry_found = 1;
		}
	}

	if ($entry_found) {
		$entry_found = 0;
		$not_looking = 1;
		study $workstr;

		($symbol) = $workstr =~ /MON\(.*?,(.*?),/;

		$workstr =~ /LVL\(([-\d]+),([-\d]+),([-\d]+),([-\d]+),([-\d\w_]+)\),/;
		$difficulty = $1;
		$speed = $2;
		$ac = $3;
		$mr = $4;
		$align = $5;

		my ($freqwork) = $workstr =~ /LVL\(.*?\),(.*?),/;
		#if ($freqwork =~ /G_NOGEN|G_UNIQ/) {
			$frequency = 0;
		#} else {
			if ($freqwork =~ /(\d)/) {
				$frequency = $1;
			}
		#}

		my $peaceful = $workstr =~ /M2_PEACEFUL/;
		my $hostile = $workstr =~ /M2_HOSTILE/;
		my $see_invis = $workstr =~ /M1_SEE_INVIS/;
		my $infravision = $workstr =~ /M3_INFRAVISION/;

		# replace sizeofs with 0 for $segments and incidentally trim parens
		$workstr =~ s/sizeof\(.*?\)/0/;

		my ($sizework,$resiststr,$conveystr) = $workstr =~ /SIZ\((.*?)\),(.*?),(.*?),/;
		my ($weight,$nutrition,$segments) = $sizework =~ /([\w\d]+),(\d+),([\w\d]+)/;

		# bitfield the resistances in merrily
		my $resists = 0;
		my $conveys = 0;
		for (my $j = 0;$j < $#resistances; $j++) {
			if ($resiststr =~ /$resistances[$j]/) { $resists += (1 << $j); }
			if ($conveystr =~ /$resistances[$j]/) { $conveys += (1 << $j); }
		}

		# all the constants from permonst.h and monst.c must go here
		if ($weight eq "WT_HUMAN") { $weight = 1450; }
		if ($weight eq "WT_ELF") { $weight = 800; }
		if ($weight eq "WT_DRAGON") { $weight = 4500; }

		if ($align eq 'A_NONE') { $align = 0; }		# Rodney filter
		$query = "INSERT INTO monst VALUES (";
		$query .= "'$mname',";
		$query .= "'$symbol',";
		$query .= "$difficulty,";
		$query .= "$speed,";
		$query .= "$ac,";
		$query .= "$mr,";
		$query .= "$align,";
		$query .= "$frequency,";
		$query .= "0,'','','','','','',";
		$query .= "$weight,";
		$query .= "$nutrition,";
		$query .= "$segments,";
		$query .= "0,0,";
		$query .= "$resists,";
		$query .= "$conveys,";
		$query .= "0,0,";
		$query .= $infravision ? "TRUE," : "FALSE,";
		$query .= $see_invis ? "TRUE," : "FALSE,";
		$query .= $peaceful ? "TRUE," : "FALSE,";
		$query .= $hostile ? "TRUE," : "FALSE,";
		$query .= "0)";
		$dbh->do($query);

		print "$mname, ";
		$mname = $difficulty = $speed = $ac = $mr = $align = $name = $symbol = 0;
		$workstr = "";
	}

}

print "\n\n";

exit;