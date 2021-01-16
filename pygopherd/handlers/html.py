import html.entities
import html.parser
import mimetypes
import re

from pygopherd.handlers.file import FileHandler


class HTMLTitleParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.titlestr = ""
        self.readingtitle = 0
        self.gotcompletetitle = 0

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.readingtitle = 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.gotcompletetitle = 1
            self.readingtitle = 0

    def handle_data(self, data):
        if self.readingtitle:
            self.titlestr += data

    def handle_entityref(self, name):
        """Handle things like &amp; or &gt; or &lt;.  If it's not in
        the dictionary, ignore it."""
        if self.readingtitle and name in html.entities.entitydefs:
            self.titlestr += html.entities.entitydefs[name]


class HTMLFileTitleHandler(FileHandler):
    """This class will set the title of a HTML document based on the
    HTML title.  It is a clone of the UMN gsfindhtmltitle function."""

    def canhandlerequest(self):
        if FileHandler.canhandlerequest(self):
            mimetype, encoding = mimetypes.guess_type(self.selector)
            return mimetype == "text/html"
        else:
            return False

    def getentry(self):
        # Start with the entry from the parent.
        entry = FileHandler.getentry(self)
        parser = HTMLTitleParser()

        with self.vfs.open(self.getselector(), "rb") as fp:
            while not parser.gotcompletetitle:
                line = fp.readline()
                if not line:
                    break
                # The PY3 HTML parser doesn't handle surrogateescape
                parser.feed(line.decode(errors="replace"))
            parser.close()

        # OK, we've parsed the file and exited because of either an EOF
        # or a complete title (or error).  Now, figure out what happened.

        if parser.gotcompletetitle:
            # Convert all whitespace sequences to a single space.
            # Removes newlines, tabs, etc.  Good for presentation
            # and for security.
            title = re.sub(r"[\s]+", " ", parser.titlestr)
            entry.setname(title)
        return entry
