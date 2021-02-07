import os
import stat
import subprocess

from pygopherd import gopherentry
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.virtual import Virtual


class ExecHandler(Virtual):
    def canhandlerequest(self):
        # We ONLY handle requests from the real filesystem.
        return (
            isinstance(self.vfs, VFS_Real)
            and self.statresult
            and stat.S_ISREG(self.statresult[stat.ST_MODE])
            and (stat.S_IMODE(self.statresult[stat.ST_MODE]) & stat.S_IXOTH)
        )

    def getentry(self):
        entry = gopherentry.GopherEntry(self.getselector(), self.config)
        entry.settype("0")
        entry.setname(os.path.basename(self.getselector()))
        entry.setmimetype("text/plain")
        entry.setgopherpsupport(0)
        return entry

    def write(self, wfile):
        newenv = os.environ.copy()
        newenv["SERVER_NAME"] = self.protocol.server.server_name
        newenv["SERVER_PORT"] = str(self.protocol.server.server_port)
        newenv["REMOTE_ADDR"] = self.protocol.requesthandler.client_address[0]
        newenv["REMOTE_PORT"] = str(self.protocol.requesthandler.client_address[1])
        newenv["REMOTE_HOST"] = newenv["REMOTE_ADDR"]
        newenv["SELECTOR"] = self.selector
        newenv["REQUEST"] = self.getselector()
        if self.searchrequest:
            newenv["SEARCHREQUEST"] = self.searchrequest
        wfile.flush()

        args = [self.getfspath()]
        if self.selectorargs:
            args.extend(self.selectorargs.split(" "))

        if not self.protocol.check_tls():
            subprocess.run(args, env=newenv, stdout=wfile)
        else:
            # We can't pass the file handler because it's wrapped in a TLS context.
            # So grab the output from the CGI script and send it directly.
            resp = subprocess.run(args, env=newenv, capture_output=True)
            wfile.write(resp.stdout)
