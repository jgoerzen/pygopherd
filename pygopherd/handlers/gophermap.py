import re
import stat

from pygopherd import gopherentry
from pygopherd.handlers.base import BaseHandler


class BuckGophermapHandler(BaseHandler):
    """Bucktooth selector handler.  Adheres to the specification
    at gopher://gopher.floodgap.com:70/0/buck/dbrowse%3Ffaquse%201"""

    def canhandlerequest(self):
        """We can handle the request if it's for a directory AND
        the directory has a gophermap file."""
        return self.statresult and (
            (
                stat.S_ISDIR(self.statresult[stat.ST_MODE])
                and self.vfs.isfile(self.getselector() + "/gophermap")
            )
            or (
                stat.S_ISREG(self.statresult[stat.ST_MODE])
                and self.getselector().endswith(".gophermap")
            )
        )

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            if (
                self.statresult
                and stat.S_ISREG(self.statresult[stat.ST_MODE])
                and self.getselector().endswith(".gophermap")
            ):
                self.entry.populatefromvfs(self.vfs, self.getselector())
            else:
                self.entry.populatefromfs(
                    self.getselector(), self.statresult, vfs=self.vfs
                )

        return self.entry

    def prepare(self):
        self.selectorbase = self.selector
        if self.selectorbase == "/":
            self.selectorbase = ""  # Avoid dup slashes

        if (
            self.getselector().endswith(".gophermap")
            and self.statresult
            and stat.S_ISREG(self.statresult[stat.ST_MODE])
        ):
            selector = self.getselector()
        else:
            selector = self.selectorbase + "/gophermap"

        self.entries = []

        selectorbase = self.selectorbase

        with self.vfs.open(selector, "rb") as rfile:
            while True:
                line = rfile.readline().decode(errors="surrogateescape")
                if not line:
                    break
                if re.search("\t", line):  # gophermap link
                    args = [arg.strip() for arg in line.split("\t")]

                    if len(args) < 2 or not len(args[1]):
                        args[1] = args[0][1:]  # Copy display string to selector

                    selector = args[1]
                    if selector[0] != "/" and selector[0:4] != "URL:":  # Relative link
                        selector = selectorbase + "/" + selector

                    entry = gopherentry.GopherEntry(selector, self.config)
                    entry.type = args[0][0]
                    entry.name = args[0][1:]

                    if len(args) >= 3 and len(args[2]):
                        entry.host = args[2]

                    if len(args) >= 4 and len(args[3]):
                        entry.port = int(args[3])

                    if entry.gethost() is None and entry.getport() is None:
                        # If we're using links on THIS server, try to fill
                        # it in for gopher+.
                        if self.vfs.exists(selector):
                            entry.populatefromvfs(self.vfs, selector)
                    self.entries.append(entry)
                else:  # Info line
                    line = line.strip()
                    self.entries.append(gopherentry.getinfoentry(line, self.config))

    def isdir(self):
        return True

    def getdirlist(self):
        return self.entries
