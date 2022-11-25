# Copyright (C) 2002, 2003 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
clean:
	-python2.3 setup.py clean --all
	-rm -f `find . -name "*~"`
	-rm -f `find . -name "*.pyc"`
	-rm -f `find . -name "*.pygc"`
	-rm -f `find . -name "*.class"`
	-rm -f `find . -name "*.bak"`
	-rm -f `find . -name ".cache*"`
	-rm -f *.log *.aux *.dvi *.out *.jtex jadetex.cfg
	-find . -name auth -exec rm -vf {}/password {}/username \;
	-rm -rf build

changelog:
	git log -M -C --find-copies-harder --name-status > ChangeLog

docs: doc/pygopherd.8 doc/pygopherd.ps \
	doc/pygopherd.pdf doc/pygopherd.txt

doc/pygopherd.8: doc/pygopherd.sgml doc/book.sgml
	docbook2man doc/book.sgml
	docbook2man doc/book.sgml
	-rm manpage.links manpage.refs
	mv pygopherd.8 doc

#doc/pygopherd.html: doc/pygopherd.sgml
#	docbook2html -u doc/pygopherd.sgml
#	mv pygopherd.html doc

doc/pygopherd.html: doc/pygopherd.sgml doc/book.sgml
	docbook2html doc/book.sgml
	mv doc/pygopherd-html/pygopherd.html doc/pygopherd.html
	rm -r doc/pygopherd-html

#doc/pygopherd.ps: doc/pygopherd.8
#	man -t -l doc/pygopherd.8 > doc/pygopherd.ps

doc/pygopherd.ps: doc/pygopherd.sgml doc/book.sgml doc/manpage.sgml
	docbook2ps \
		doc/book.sgml
	mv book.ps doc/pygopherd.ps

doc/pygopherd.pdf: doc/pygopherd.ps
	ps2pdf doc/pygopherd.ps
	mv pygopherd.pdf doc

doc/pygopherd.txt:
	groff -Tascii -man doc/pygopherd.8 | sed $$'s/.\b//g' > doc/pygopherd.txt
