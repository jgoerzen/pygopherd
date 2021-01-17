import re
import stat
import subprocess
import typing

from pygopherd import gopherentry
from pygopherd.handlers.base import BaseHandler


class CompressedGopherEntry(gopherentry.GopherEntry):
    """
    Using an abstract class because we attach extra variables to the gopher entry.
    """

    realencoding: str


class FileHandler(BaseHandler):
    def canhandlerequest(self):
        """We can handle the request if it's for a file."""
        return self.statresult and stat.S_ISREG(self.statresult[stat.ST_MODE])

    def getentry(self):
        if not self.entry:
            self.entry = gopherentry.GopherEntry(self.selector, self.config)
            self.entry.populatefromfs(self.getselector(), self.statresult, vfs=self.vfs)
        return self.entry

    def write(self, wfile):
        self.vfs.copyto(self.getselector(), wfile)


class CompressedFileHandler(FileHandler):
    decompressors: typing.Dict[str, str]
    decompresspatt: str
    entry: typing.Optional[CompressedGopherEntry]

    def canhandlerequest(self):
        self.initdecompressors()

        # It's OK to call just canhandlerequest() since we're not
        # overriding the security or isrequestforme functions.

        return (
            super().canhandlerequest()
            and self.getentry().realencoding
            and self.getentry().realencoding in self.decompressors
            and re.search(self.decompresspatt, self.selector)
        )

    def getentry(self) -> CompressedGopherEntry:
        if not self.entry:
            self.entry = typing.cast(CompressedGopherEntry, super().getentry())

            self.entry.realencoding = None
            if (
                self.entry.getencoding()
                and self.entry.getencoding() in self.decompressors
                and self.entry.getencodedmimetype()
            ):
                # When the client gets it, there will not be
                # encoding.  Therefore, we remove the encoding and switch
                # to the real MIME type.
                self.entry.mimetype = self.entry.getencodedmimetype()
                self.entry.encodedmimetype = None
                self.entry.realencoding = self.entry.encoding
                self.entry.encoding = None
                self.entry.type = self.entry.guesstype()
        return self.entry

    def initdecompressors(self) -> None:
        if not hasattr(self, "decompressors"):
            self.decompressors = eval(
                self.config.get("handlers.file.CompressedFileHandler", "decompressors")
            )
            self.decompresspatt = self.config.get(
                "handlers.file.CompressedFileHandler", "decompresspatt"
            )

    def write(self, wfile):
        decompprog = self.decompressors[self.getentry().realencoding]
        with self.vfs.open(self.getselector(), "rb") as fp:
            subprocess.run([decompprog], stdin=fp, stdout=wfile)
