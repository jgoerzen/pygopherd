import SocketServer
import re, binascii
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
        self.iconmapping = eval(self.config.get("protocols.http.HTTPProtocol",
                                                "iconmapping"))

        # Slurp up remaining lines.
        while len(self.rfile.readline().strip()):
            pass
            
        self.selector = urllib.unquote(self.requestparts[1])

        icon = re.match('/PYGOPHERD-HTTPPROTO-ICONS/(.+)$', self.selector)
        if icon:
            iconname = icon.group(1)
            if icons.has_key(iconname):
                self.wfile.write("HTTP/1.0 200 OK\n")
                self.wfile.write("Content-Type: image/gif\n\n")
                self.wfile.write(binascii.unhexlify(icons[iconname]))
                return

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

        retstr += "<TR><TD>"
        retstr += self.getimgtag(entry)
        retstr += "</TD>\n<TD>&nbsp;"
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
        retstr += '</H1><TABLE WIDTH="100%" CELLSPACING="1" CELLPADDING="0">'
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

    def getimgtag(self, entry):
        if self.iconmapping.has_key(entry.gettype()):
            return '<IMG SRC="%s" WIDTH="20" HEIGHT="22" BORDER="0">' % \
                   ('/PYGOPHERD-HTTPPROTO-ICONS/' + \
                   self.iconmapping[entry.gettype()])
        else:
            return '&nbsp;'            

icons = {
'binary.gif':
'47494638396114001600c20000ffffffccffffcccccc99999933333300000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000001002c000000001400160000036948babcf1301040ab9d24be590a105d210013a9715e07a8a509a16beab5ae14df6a41e8fc76839d5168e8b3182983e4a0e0038a6e1525d396931d97be2ad482a55a55c6eec429f484a7b4e339eb215fd138ebda1b7fb3eb73983bafee8b094a8182493b114387885309003b',

'binhex.gif':
'47494638396114001600c20000ffffffccffff99999966666633333300000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000001002c000000001400160000036948babcf1301040ab9d24be59baefc0146adce78555068914985e2b609e0551df9b3c17ba995b408a602828e48a2681856894f44cc1628e07a42e9b985d14ab1b7c9440a9131c0c733b229bb5222ecdb6bfd6da3cd5d29d688a1aee2c97db044482834336113b884d09003b',

'folder.gif':
'47494638396114001600c20000ffffffffcc99ccffff99663333333300000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000002002c000000001400160000035428badcfe30ca4959b9f8ce12baef45c47d64a629c5407a6a8906432cc72b1c8ef51a13579e0f3c9c8f05ec0d4945e171673cb2824e2234da495261569856c5ddc27882d46c3c2680c3e6b47acd232c4cf08c3b01003b',

'image3.gif':
'47494638396114001600e30000ffffffff3333ccffff9999996600003333330099cc00993300336600000000000000000000000000000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000002002c0000000014001600000479b0c849a7b85814c0bbdf45766d5e49861959762a3a76442c132ae0aa44a0ef49d1ff2f4e6ea74b188f892020c70c3007d04152b3aa46a7adcaa42355160ee0f041d5a572bee23017cb1abbbf6476d52a0720ee78fc5a8930f8ff06087b66768080832a7d8a81818873744a8f8805519596503e19489b9c5311003b',

'sound1.gif':
'47494638396114001600c20000ffffffff3333ccffffcccccc99999966000033333300000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000002002c000000001400160000036b28badcfe3036c34290ea1c61558f07b171170985c0687e0d9a729e77693401dc5bd7154148fcb6db6b77e1b984c20d4fb03406913866717a842aa7d22af22acd120cdf6fd2d49cd10e034354871518de06b43a17334de42a36243e187d4a7b1a762c7b140b8418898a0b09003b',

'text.gif':
'47494638396114001600c20000ffffffccffff99999933333300000000000000000000000021fe4e546869732061727420697320696e20746865207075626c696320646f6d61696e2e204b6576696e204875676865732c206b6576696e68406569742e636f6d2c2053657074656d62657220313939350021f90401000001002c000000001400160000035838babcf1300c40ab9d23be693bcf11d75522b88dd7057144eb52c410cf270abb6e8db796e00b849aadf20b4a6ebb1705281c128daca412c03c3a7b50a4f4d9bc5645dae9f78aed6e975932baebfc0e7ef0b84f1691da8d09003b'}
