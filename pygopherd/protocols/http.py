import SocketServer
import re
import os, stat, os.path, mimetypes, handlers, protocols, urllib, time
import protocols.base
import cgi, GopherExceptions

class HTTPProtocol(protocols.base.BaseGopherProtocol):
    def canhandlerequest(self):
        self.requestparts = map(lambda arg: arg.strip(), self.request.split(" "))
        return len(self.requestparts) == 3 and \
               (self.requestparts[0] == 'GET' or self.requestparts[0] == 'HEAD') and \
               self.requestparts[2][0:5] == 'HTTP/'

    def handle(self):
        self.canhandlerequest()         # To get self.requestparts

        # Slurp up remaining lines.
        while len(self.rfile.readline().strip()):
            pass
            
        self.selector = urllib.unquote(self.requestparts[1])

        try:
            handler = self.gethandler()
            self.entry = handler.getentry()
            handler.prepare()
            self.wfile.write("HTTP/1.0 200 OK\n")
            if self.entry.getmtime() != None:
                gmtime = time.gmtime(self.entry.getmtime())
                mtime = time.strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime)
                self.wfile.write("Last-Modified: " + mtime + "\n")
            mimetype = self.entry.getmimetype()
            if mimetype == None:
                mimetype = 'text/plain'
            if mimetype == 'application/gopher-menu':
                mimetype = 'text/html'
            self.wfile.write("Content-Type: " + mimetype + "\n\n")
            if self.requestparts[0] == 'GET':
                handler.write(self.wfile)
        except GopherExceptions.FileNotFound, e:
            self.filenotfound(str(e))
        except IOError, e:
            self.filenotfound(e[1])

    def renderobjinfo(self, entry):
        retstr = '<TR><TD>'
        url = None
        # Decision time....
        if (not entry.gethost()) and (not entry.getport()):
            # It's a link to our own server.  Make it as such.  (relative)
            url = entry.getselector()
        else:
            # Link to a different server.  Make it a gopher URL.
            url = 'gopher://%s:%d/%s%s' % \
                  (entry.gethost(self.server.server_name),
                   entry.getport(70),
                   entry.gettype('0'),
                   entry.getselector())
        if re.match('(/|)URL:', entry.getselector()):
            # It's a plain URL.  Make it that.
            url = re.match('(/|)URL:(.+)$', entry.getselector()).group(1)

        # OK.  Render.

        retstr += "<TR><TD>&nbsp;"
        if entry.gettype() != 'i':
            retstr += '<A HREF="%s">' % urllib.quote(url)
        retstr += "<TT>"
        if entry.getname() != None:
            retstr += cgi.escape(entry.getname())
        else:
            retstr += cgi.escape(entry.getselector())
        retstr += "</TT>"
        if entry.gettype() != 'i':
            retstr += '</A>'
        retstr += '</TD><TD><FONT SIZE="-2">'
        if entry.getmimetype():
            subtype = re.search('/.+$', entry.getmimetype())
            if subtype:
                retstr += cgi.escape(subtype.group()[1:])
        retstr += '</FONT></TD></TR>\n'
        return retstr
    
    def renderdirstart(self, entry):
        retstr ='<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">'
        retstr += "\n<HTML><HEAD><TITLE>Gopher"
        if self.entry.getname():
            retstr += ": " + cgi.escape(self.entry.getname())
        retstr += "</TITLE></HEAD><BODY><H1>Gopher"
        if self.entry.getname():
            retstr += ": " + cgi.escape(self.entry.getname())
        retstr += '</H1><TABLE WIDTH="100%" CELLSPACING="0" CELLPADDING="0">'
        return retstr

    def renderdirend(self, entry):
        return '</TABLE></BODY></HTML>'

    def filenotfound(self, msg):
        self.wfile.write("HTTP/1.0 404 Not Found\n")
        self.wfile.write("Content-Type: text/html\n\n")
        self.wfile.write('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">')
        self.wfile.write("""\n<HTML><HEAD><TITLE>Selector Not Found</TITLE>
        <H1>Selector Not Found</H1>
        <TT>""")
        self.wfile.write(cgi.escape(msg))
        self.wfile.write("</TT><HR>Pygopherd</BODY></HTML>\n")
