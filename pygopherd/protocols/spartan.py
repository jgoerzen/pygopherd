import re
import typing
import urllib.error
import urllib.parse
import urllib.request

from pygopherd import GopherExceptions
from pygopherd.protocols.base import BaseGopherProtocol


class SpartanProtocol(BaseGopherProtocol):
    """
    Spartan is a simple, niche TCP protocol developed by yours truly :)

    This protocol class borrows components from both HTTP and Gemini.

    Reference: gemini://spartan.mozz.us/specification.gmi
    """

    def canhandlerequest(self):
        if self.check_tls():
            return False

        # The request line must be ASCII encoded
        try:
            self.request.encode("ascii")
        except UnicodeEncodeError:
            return False

        # Three non-empty parts, with the third part being an integer >= 0.
        parts = self.request.strip().split(" ")
        return len(parts) == 3 and all(parts) and parts[2].isdigit()

    def handle(self):
        host, path, content_length = self.request.strip().split(" ")

        self.selector = urllib.parse.unquote(path, errors="surrogateescape")

        content_length = int(content_length)
        if content_length:
            data = self.rfile.read(content_length)
            self.searchrequest = data.decode(errors="surrogateescape")

        try:
            handler = self.gethandler()
            self.log(handler)
            self.entry = handler.getentry()
            handler.prepare()
        except GopherExceptions.FileNotFound as e:
            self.write_status(4, str(e))
            return
        except IOError as e:
            GopherExceptions.log(e, self, None)
            self.write_status(5, e[1])
            return

        if handler.isdir():
            self.write_status(2, "text/gemini")
            self.writedir(self.entry, handler.getdirlist())
        else:
            mimetype = self.adjust_mimetype(self.entry.getmimetype())
            self.write_status(2, mimetype)
            self.handler.write(self.wfile)

    def write_status(self, code: int, meta: str) -> None:
        self.wfile.write(f"{code} {meta}\r\n".encode(errors="backslashreplace"))

    def adjust_mimetype(self, mimetype: typing.Optional[str]) -> str:
        if mimetype is None:
            return "text/plain"
        if mimetype == "application/gopher-menu":
            return "text/gemini"
        return mimetype

    def renderobjinfo(self, entry):
        if re.match("(/|)URL:", entry.getselector()):
            # It's a plain URL.  Make it that.
            url = re.match("(/|)URL:(.+)$", entry.getselector()).group(2)
        elif (not entry.gethost()) and (not entry.getport()):
            # It's a link to our own server.  Make it as such.  (relative)
            selector = entry.getselector().encode(errors="surrogateescape")
            url = urllib.parse.quote(selector)
            url = url or "/"  # Use "/" for relative links to the root URL
        else:
            # Link to a different server.  Make it a gopher URL.
            url = entry.geturl(self.server.server_name, 70)

        description = entry.getname() or ""

        # text/gemini is expected to be UTF-8, so replace any stray bytes
        description_bytes = description.encode(errors="surrogateescape")
        description = description_bytes.decode(errors="backslashreplace")

        if entry.gettype() == "i":
            return f"{description}\n"
        elif entry.gettype() == "7":
            return f"=: {url} {description}\n"
        else:
            return f"=> {url} {description}\n"

    def renderdirstart(self, entry):
        return f"# Gopher: {entry.selector}\n\n"

    def renderdirend(self, entry):
        if self.config.has_option("protocols.gemini.SpartanProtocol", "footer"):
            text = self.config.get("protocols.gemini.SpartanProtocol", "footer")
            return f"\n{text}\n"
