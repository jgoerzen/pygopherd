import re
import typing
import urllib.error
import urllib.parse
import urllib.request

from pygopherd import GopherExceptions
from pygopherd.protocols.base import BaseGopherProtocol


class GeminiProtocol(BaseGopherProtocol):
    secure = True

    query_prefix = "/GEMINI-QUERY"

    def __init__(self, *args: typing.Any, **kwargs: typing.Any):
        super().__init__(*args, **kwargs)

    def canhandlerequest(self):
        # Even though gemini can accept proxy URLs with different hostnames
        # and ports, we're pretending that every request starting with
        # gemini:// is meant for this server.
        return self.check_tls() and self.request.startswith("gemini://")

    def handle(self):
        # Be overly permissive here and ignore most request validation like
        # checking for a strict <CR><LF> or denying requests over 1024 bytes.
        url_parts = urllib.parse.urlparse(self.request.strip())

        selector = url_parts.path
        searchrequest = url_parts.query

        if selector.startswith(self.query_prefix):
            self.handle_input(selector, searchrequest)
            return

        self.selector = urllib.parse.unquote(selector, errors="surrogateescape")
        self.searchrequest = urllib.parse.unquote(
            searchrequest, errors="surrogateescape"
        )

        try:
            handler = self.gethandler()
            self.log(handler)
            self.entry = handler.getentry()
            handler.prepare()
        except GopherExceptions.FileNotFound as e:
            self.write_status(51, str(e))
            return
        except IOError as e:
            GopherExceptions.log(e, self, None)
            self.write_status(51, e[1])
            return

        if handler.isdir():
            self.write_status(20, "text/gemini")
            self.writedir(self.entry, handler.getdirlist())
        else:
            mimetype = self.adjust_mimetype(self.entry.getmimetype())
            self.write_status(20, mimetype)
            self.handler.write(self.wfile)

    def handle_input(self, selector: str, searchrequest: str) -> None:
        """
        Gemini is reversed from gopher in that it can't specify a
        search link inside a directory listing. So instead, we add
        a special prefix to search URLs in order to tell the server
        to prompt for input. After input has been submitted, we
        redirect back to the original selector.

        The selector and searchrequest arguments should already be
        URL-quoted.
        """
        if not searchrequest:
            self.write_status(10, "Enter input")
        else:
            selector = selector[len(self.query_prefix) :]
            self.write_status(30, f"{selector}?{searchrequest}")

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
            if entry.gettype() == "7":
                url = self.query_prefix + url
        else:
            # Link to a different server.  Make it a gopher URL.
            url = entry.geturl(self.server.server_name, 70)

        description = entry.getname() or ""

        # text/gemini is expected to be UTF-8, so replace any stray bytes
        description_bytes = description.encode(errors="surrogateescape")
        description = description_bytes.decode(errors="backslashreplace")

        if entry.gettype() == "i":
            return f"{description}\n"
        else:
            return f"=> {url} {description}\n"

    def renderdirstart(self, entry):
        return f"# Gopher: {entry.selector}\n\n"

    def renderdirend(self, entry):
        if self.config.has_option("protocols.gemini.GeminiProtocol", "footer"):
            text = self.config.get("protocols.gemini.GeminiProtocol", "footer")
            return f"\n{text}\n"
