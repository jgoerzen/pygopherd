import SocketServer
import re
import os, stat, os.path, mimetypes, handlers, protocols, urllib, time
import protocols.base
import cgi

class GopherProtocol(protocols.base.BaseGopherProtocol):
    def canhandlerequest(self):
        self.requestparts = map(lambda arg: arg.strip(), self.request.split(" "))
        return len(self.requestparts == 3) and \
               (self.requestparts[0] == 'GET' or self.requestparts[0] == 'HEAD') and \
               self.requestparts[0:5] == 'HTTP/'

    def handle(self):
        self.canhandlerequest()         # To get self.requestparts

        # Slurp up remaining lines.
        while len(self.rfile.readline().strip()):
            pass
            
        self.selector = urllib.unquote(self.requestparts[1])

        # Use these in renderobjinfo -- it's used if we're displaying a dir.

        self.htmlstarted = 0
        self.htmlended = 1

        try:
            handler = self.gethandler()
            self.entry = handler.getentry()
            handler.prepare()
            self.wfile.write("HTTP/1.0 200 OK\n")
            if self.entry.getmtime() != None:
                gmtime = time.gmtime(self.entry.getmtime())
                mtime = time.strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime)
                self.wfile.write("Last-Modified: " + mtime + "\n")
            mimetype = self.getmimetype()
            if mimetype == None:
                mimetype = 'text/plain'
            if mimetype == 'application/gopher-menu':
                mimetype = 'text/html'
            self.wfile.write("Content-Type: " + mimetype + "\n\n")
            if self.requestparts[0] == 'GET':
                handler.write(self.wfile)
            if not self.htmlended:
                self.endhtml()
        except GopherExceptions.FileNotFound, e:
            self.filenotfound(str(e))
        except IOError, e:
            self.filenotfound(e[1])

    def renderobjinfo(self, entry):
        if not self.htmlstarted:
            self.starthtml()
            self.htmlstarted = 1
        retstr = '<TR><TD>'
        #url = 'http://
        #if entry.gettype != 'i':
        #    retstr += '<A HREF="%s">' % urllib.quote("http
    
    def starthtml(self):
        self.wfile.write('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">\n')
        self.wfile.write("""<HTML><HEAD><TITLE>Gopher""")
        if self.entry.getname():
            self.wfile.write(": " + cgi.escape(self.entry.getname()))
        self.wfile.write("""</TITLE></HEAD><BODY><H1>Gopher""")
        if self.entry.getname():
            self.wfile.write(": " + cgi.escape(self.entry.getname()))
        self.wfile.write('</H1><TABLE WIDTH="100%" CELLSPACING="0" CELLPADDING="0">')

    def endhtml(self):
        self.wfile.write('</TABLE></BODY></HTML>')
