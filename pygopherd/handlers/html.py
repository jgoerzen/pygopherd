# pygopherd -- Gopher-based protocol server in Python
# module: Special handling of HTML files
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from handlers.file import FileHandler
from HTMLParser import HTMLParser
import SocketServer
import re
import os, stat, os.path, mimetypes, protocols, gopherentry, mimetypes
import handlers, handlers.base, htmlentitydefs
from gopherentry import GopherEntry


###########################################################################
# HTML File Handler
# Sets the name of a file if it's HTML.
###########################################################################
class HTMLTitleParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.titlestr = ""
        self.readingtitle = 0
        self.gotcompletetitle = 0
        
    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.readingtitle = 1

    def handle_endtag(self, tag):
        if tag == 'title':
            self.gotcompletetitle = 1
            self.readingtitle = 0
        
    def handle_data(self, data):
        if self.readingtitle:
            self.titlestr += data

    def handle_entityref(self, name):
        """Handle things like &amp; or &gt; or &lt;.  If it's not in
        the dictionary, ignore it."""
        if self.readingtitle and htmlentitydefs.entitydefs.has_key(name):
            self.titlestr += htmlentitydefs.entitydefs[name]

class HTMLFileTitleHandler(FileHandler):
    """This class will set the title of a HTML document based on the
    HTML title.  It is a clone of the UMN gsfindhtmltitle function."""
    def canhandlerequest(self):
        if FileHandler.canhandlerequest(self):
            mimetype, encoding = mimetypes.guess_type(self.selector)
            return mimetype == 'text/html'
        else:
            return 0

    def getentry(self):
        # Start with the entry from the parent.
        entry = FileHandler.getentry(self)
        parser = HTMLTitleParser()
        file = open(self.getfspath(), "rt")
        try:
            while not parser.gotcompletetitle:
                line = file.readline()
                if not line:
                    break
                parser.feed(line)
            parser.close()
        except HTMLParser.HTMLParseError:
            # Parse error?  Stop parsing, go to here.  We can still
            # return a title if the parse error happened after we got
            # the title.
            pass

        file.close()
        # OK, we've parsed the file and exited because of either an EOF
        # or a complete title (or error).  Now, figure out what happened.

        if parser.gotcompletetitle:
            # Convert all whitespace sequences to a single space.
            # Removes newlines, tabs, etc.  Good for presentation
            # and for security.
            title = re.sub('[\s]+', ' ', parser.titlestr)
            entry.setname(title)
        return entry

