# pygopherd -- Gopher-based protocol server in Python
# module: ZIP transparent handling
# Copyright (C) 2003 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import re, time, stat, unittest, os.path, struct, types, copy
from StringIO import StringIO
from pygopherd import zipfile

UNX_IFMT = 0170000L
UNX_IFLNK = 0120000L

from pygopherd.handlers import base

class VFS_Zip(base.VFS_Real):
    def __init__(self, config, chain, zipfilename):
        self.config = config
        self.chain = chain
        self.zipfilename = zipfilename

        zipfd = self.chain.open(self.zipfilename)
        self.zip = zipfile.ZipReader(zipfd)

    def _needschain(self, selector):
        return not selector.startswith(self.zipfilename)

    # Functions to determine if this is a link.

    def _islinkattr(self, attr):
        str = struct.pack('L', attr)
        str2 = str[2:5] + str[0:2]
        result = struct.unpack('L', str2)[0]
        return (result & UNX_IFMT) == UNX_IFLNK

    def _islinkinfo(self, info):
        if type(info) == types.DictType:
            return 0
        return self._islinkattr(info.external_attr)

    # Functions to read a link.

    def _readlinkfspath(self, fspath):
        """It better be a link before you try this!"""
        return self._open(fspath).read()

    def _readlink(self, selector):
        return self._readlinkfspath(self, self._getfspathfinal(selector))

    # Resolve a link into its final form.

    def _resolvelink(self, fspath):
        zi = None
        newpath = ''
        for component in fspath.split('/'):
            newpath = os.path.join(newpath, component)
            while 1:
                try:
                    zi = self.zip.getinfo(newpath)
                except KeyError:
                    break
                if not self._islinkinfo(zi):
                    break

                newlink = self._readlinkfspath(newpath)
                if newlink[0] == '/':
                    newpath = os.path.normpath(newlink[1:])
                else:
                    newpath = os.path.normpath(os.path.join(os.path.dirname(newpath), newlink))
        return newpath

    def _getinfofspath(self, fspath):
        """This function takes a pre-resolved link!"""
        return self.zip.getinfo(fspath)

    def _getinfo(self, selector):
        return self._getinfofspath(self._getfspathresolved(selector))

    def iswritable(self, selector):
        if self._needschain(selector):
            return self.chain.iswritable(selector)

        return 0

    def unlink(self, selector):
        raise NotImplementedError, "VFS_ZIP cannot unlink files."

    def _getfspathresolved(self, selector):
        return self._resolvelink(self._getfspathfinal(selector))

    def _getfspathfinal(self, selector):
        # Strip off the filename part.
        selector = selector[len(self.zipfilename):]

        if selector.startswith('/'):
            selector = selector[1:]

        if selector.endswith('/'):
            selector = selector[:-1]

        return selector
    
    def getfspath(self, selector):
        if self._needschain(selector):
            return self.chain.getfspath(selector)

        # We can skip the initial part -- it just contains the start of
        # the path.

        return self._getfspathfinal(selector)

    def stat(self, selector):
        if self._needschain(selector):
            return self.chain.stat(selector)

        fspath = self._getfspathresolved(selector)

        try:
            zi = self._getinfofspath(fspath)
            zt = zi.date_time
            modtime = time.mktime(zt + (0, 0, -1))
            return (33188,                  # mode
                    0,                      # inode
                    0,                      # device
                    1,                      # links
                    0,                      # uid
                    0,                      # gid
                    zi.file_size,           # size
                    modtime,                # access time
                    modtime,                # modification time
                    modtime)                # change time
        except KeyError:
            pass
        
        if not self._isdir_fspath(fspath):
            raise OSError, "Entry %s does not exist in %s" %\
                  (selector, self.zipfilename)
            
        # It's a directory.
        return (16877,              # mode
                0,                  # inode
                0,                  # device
                3,                  # links
                0,                  # uid
                0,                  # gid
                0,                  # size
                0,                  # access time
                0,                  # modification time
                0)                  # change time


    def _isdir_fspath(self, fspath):
        return self.zip.directorymap.has_key(fspath)

    def isdir(self, selector):
        if self._needschain(selector):
            return self.chain.isdir(selector)

        return self._isdir_fspath(self._getfspathresolved(selector))

    def _isfile_fspath(self, fspath):
        return self.zip.locationmap.has_key(fspath)
    
    def isfile(self, selector):
        if self._needschain(selector):
            return self.chain.isfile(selector)

        return self._isfile_fspath(self._getfspathresolved(selector))

    def _exists_fspath(self, fspath):
        return self._isfile_fspath(fspath) or self._isdir_fspath(fspath)

    def exists(self, selector):
        if self._needschain(selector):
            return self.chain.exists(selector)

        return self._exists_fspath(self._getfspathresolved(selector))

    def _open(self, fspath):
        return self.zip.open(fspath)

    def open(self, selector, *args, **kwargs):
        if self._needschain(selector):
            return apply(self.chain.open, (selector,) + args, kwargs)

        fspath = self._getfspathresolved(selector)
        if not self._isfile_fspath(fspath):
            raise IOError, "Request to open non-existant file"
        return self._open(fspath)

    def listdir(self, selector):
        if self._needschain(selector):
            return self.chain.listdir(selector)

        fspath = self._getfspathresolved(selector)
        if not self._isdir_fspath(fspath):
            raise OSError, "Request to list non-existant directory"

        retval = []
        for item in self.zip.locationmap.iterkeys():
            (d, f) = os.path.split(item)
            if d == fspath and f != '':
                retval.append(f)
        return retval
        
#class TestVFS_Zip_huge(unittest.TestCase):
class DISABLED_TestVFS_Zip_huge:
    def setUp(self):
        from pygopherd import testutil
        from pygopherd.protocols.rfc1436 import GopherProtocol
        self.config = testutil.getconfig()
        self.rfile = StringIO("/testfile.txt\n")
        self.wfile = StringIO()
        self.logfile = testutil.getstringlogger()
        self.handler = testutil.gettestinghandler(self.rfile, self.wfile,
                                                  self.config)
        self.server = self.handler.server
        self.proto = GopherProtocol("/testfile.txt\n", self.server,
                                    self.handler, self.rfile, self.wfile,
                                    self.config)
        self.config.set("handlers.ZIP.ZIPHandler", "enabled", 'true')
        from pygopherd.handlers import HandlerMultiplexer
        HandlerMultiplexer.handlers = None
        handlerlist = self.config.get("handlers.HandlerMultiplexer", "handlers")
        handlerlist = handlerlist.strip()
        handlerlist = handlerlist[0] + 'ZIP.ZIPHandler, ' + handlerlist[1:]
        self.config.set("handlers.HandlerMultiplexer", "handlers", handlerlist)


    def testlistdir1(self):
        from pygopherd.protocols.rfc1436 import GopherProtocol
        self.proto = GopherProtocol("/foo.zip\n",
                                    self.server,
                                    self.handler, self.rfile, self.wfile,
                                    self.config)
        self.proto.handle()

    def testlistdir2(self):
        from pygopherd.protocols.rfc1436 import GopherProtocol
        self.proto = GopherProtocol("/foo.zip/lib\n",
                                    self.server,
                                    self.handler, self.rfile, self.wfile,
                                    self.config)
        self.proto.handle()

#    def testlistdir3(self):
#        from pygopherd.protocols.rfc1436 import GopherProtocol
#        self.proto = GopherProtocol("/foo.zip/lib/dpkg/info\n",
#                                    self.server,
#                                    self.handler, self.rfile, self.wfile,
#                                    self.config)
#        self.proto.handle()
        
    def testopen1(self):
        from pygopherd.protocols.rfc1436 import GopherProtocol
        self.proto = GopherProtocol("/foo.zip/lib/dpkg/info/dpkg.list\n",
                                    self.server,
                                    self.handler, self.rfile, self.wfile,
                                    self.config)
        self.proto.handle()

    def testopen2(self):
        from pygopherd.protocols.rfc1436 import GopherProtocol
        self.proto = GopherProtocol("/foo.zip/games/bsdgames/snake.log\n",
                                    self.server,
                                    self.handler, self.rfile, self.wfile,
                                    self.config)
        self.proto.handle()

    def testopen3(self):
        from pygopherd.protocols.rfc1436 import GopherProtocol
        self.proto = GopherProtocol("/foo.zip/www/apache2-default/manual/platforms/index.html\n",
                                    self.server,
                                    self.handler, self.rfile, self.wfile,
                                    self.config)
        self.proto.handle()

class TestVFS_Zip(unittest.TestCase):
    def setUp(s):
        from ConfigParser import ConfigParser
        s.config = ConfigParser()
        s.config.add_section('pygopherd')
        s.config.set("pygopherd", "root", os.path.abspath('testdata'))
        s.real = base.VFS_Real(s.config)
        s.z = VFS_Zip(s.config, s.real, '/testdata.zip')
        s.z2 = VFS_Zip(s.config, s.real, '/testdata2.zip')
        s.zs = VFS_Zip(s.config, s.real, '/symlinktest.zip')

    def test_listdir(s):
        m1 = s.z.listdir('/testdata.zip')
        m2 = s.z2.listdir('/testdata2.zip')

        m1.sort()
        m2.sort()

        assert 'pygopherd' in m1
        s.assertEquals(m1, m2)
        s.assertEquals(m1, ['.abstract', 'README', 'pygopherd',
                            'testarchive.tar', 'testarchive.tar.gz',
                            'testarchive.tgz', 'testfile.txt',
                            'testfile.txt.gz', 'testfile.txt.gz.abstract'])

        m1 = s.z.listdir('/testdata.zip/pygopherd')
        m2 = s.z2.listdir('/testdata2.zip/pygopherd')

        m1.sort()
        m2.sort()

        s.assertEquals(m1, m2 + ['ziponly'])
        s.assertEquals(m1, ['pipetest.sh', 'pipetestdata', 'ziponly'])

    def test_needschain(s):
        assert s.z._needschain('/testfile.txt')
        assert s.z._needschain('/foo/testdata.zip')
        assert not s.z._needschain('/testdata.zip')
        assert not s.z._needschain('/testdata.zip/foo')
        assert not s.z._needschain('/testdata.zip/foo/bar')

    def test_iswritable(s):
        assert not s.z.iswritable('/testdata.zip')
        assert not s.z.iswritable('/testdata.zip/README')
        assert not s.z.iswritable('/testdata.zip/pygopherd')
        assert s.z.iswritable('/README')
        assert s.z.iswritable('/.foo')

    def test_getfspath(s):
        s.assertEquals(s.z.getfspath('/testdata.zip/foo'), 'foo')
        s.assertEquals(s.z.getfspath('/testdata.zip'), '')
        s.assertEquals(s.z.getfspath('/testdata.zip/foo/bar'), 'foo/bar')

    def test_stat(s):
        s.assertRaises(OSError, s.z.stat, '/testdata.zip/nonexistant')
        s.assertRaises(OSError, s.z.stat, '/nonexistant')
        assert stat.S_ISREG(s.z.stat('/testfile.txt')[0])
        assert stat.S_ISDIR(s.z.stat('/testdata.zip')[0])
        assert stat.S_ISREG(s.z.stat('/testdata.zip/README')[0])
        assert stat.S_ISDIR(s.z.stat('/testdata.zip/pygopherd')[0])
        assert stat.S_ISDIR(s.z2.stat('/testdata2.zip/pygopherd')[0])
        assert stat.S_ISREG(s.z.stat('/testdata.zip/pygopherd/pipetest.sh')[0])
        assert stat.S_ISREG(s.z2.stat('/testdata2.zip/pygopherd/pipetest.sh')[0])

    def test_isdir(s):
        assert not s.z.isdir('/testdata.zip/README')
        assert not s.z2.isdir('/testdata.zip/README')
        assert s.z.isdir('/pygopherd')
        assert s.z.isdir('/testdata.zip/pygopherd')
        assert s.z2.isdir('/testdata2.zip/pygopherd')
        assert s.z.isdir('/testdata.zip')

    def test_isfile(s):
        assert s.z.isfile('/testdata.zip/README')
        assert not s.z.isfile('/testdata.zip')
        assert not s.z.isfile('/testdata.zip/pygopherd')
        assert not s.z2.isfile('/testdata2.zip/pygopherd')
        assert s.z.isfile('/testdata.zip/.abstract')

    def test_exists(s):
        assert s.z.exists('/README')
        assert not s.z.exists('/READMEnonexistant')
        assert s.z.exists('/testdata.zip')
        assert s.z.exists('/testdata.zip/README')
        assert s.z.exists('/testdata.zip/pygopherd')
        assert s.z2.exists('/testdata2.zip/pygopherd')
        assert not s.z2.exists('/testdata.zip/pygopherd')

    def test_symlinkexists(s):
        assert s.zs.exists('/symlinktest.zip/real.txt')
        assert s.zs.exists('/symlinktest.zip/linked.txt')
        assert s.zs.exists('/symlinktest.zip/subdir/linktosubdir2')

    def test_symlinkgetfspath(s):
        s.assertEquals(s.zs.getfspath('/symlinktest.zip'), '')
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/real.txt'), 'real.txt')
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/subdir'), 'subdir')
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/subdir2/real2.txt'),
                                      'subdir2/real2.txt')

    def test_resolvelink(s):
        a = s.assertEquals
        f = s.zs._resolvelink
        a(f(''), '')
        a(f('real.txt'), 'real.txt')
        a(f('linktosubdir'), 'subdir')
        a(f('subdir'), 'subdir')
        a(f('subdir2'), 'subdir2')

        for d in ['subdir', 'linktosubdir', 'subdir/linktoself',
                  'linktosubdir/linktoself', 'subdir/linktoself/linktoself',
                  'linktosubdir/linktoself/linktoself']:
            a(f(d + '/linked2.txt'), 'subdir2/real2.txt')
            a(f(d + '/linkedabs.txt'), 'real.txt')
            a(f(d + '/linkedrel.txt'), 'real.txt')
            a(f(d + '/linktoself'), 'subdir')
            a(f(d + '/linktosubdir2'), 'subdir2')
            a(f(d + '/linktosubdir2/real2.txt'), 'subdir2/real2.txt')
            a(f(d + '/linktosubdir2/foo.txt'), 'subdir2/foo.txt')


#    def test_islinkname(s):
#        assert not s.zs._islinkname('/symlinktest.zip/real.txt')
#        assert not s.zs._islinkname('/symlinktest.zip/nonexistant')

    def test_symlink_listdir(s):
        m1 = s.zs.listdir('/symlinktest.zip')
        m1.sort()

        s.assertEquals(m1, ['linked.txt', 'linktosubdir', 'real.txt',
                            'subdir', 'subdir2'])

        tm2 = ['linked2.txt', 'linkedabs.txt', 'linkedrel.txt', 'linktoself',
               'linktosubdir2']
        m2 = s.zs.listdir('/symlinktest.zip/subdir')
        m2.sort()
        s.assertEquals(m2, tm2)

        m2 = s.zs.listdir('/symlinktest.zip/linktosubdir')
        m2.sort()
        s.assertEquals(m2, tm2)

        s.assertRaises(OSError, s.zs.listdir, '/symlinktest.zip/nonexistant')
        s.assertRaises(OSError, s.zs.listdir, '/symlinktest.zip/real.txt')
        s.assertRaises(OSError, s.zs.listdir, '/symlinktest.zip/linktosubdir/linkedrel.txt')

        m2 = s.zs.listdir('/symlinktest.zip/linktosubdir/linktoself/linktoself')
        
        m2.sort()
        s.assertEquals(m2, tm2)

        m3 = s.zs.listdir('/symlinktest.zip/linktosubdir/linktoself/linktosubdir2')
        s.assertEquals(m3, ['real2.txt'])

        s.assertEquals(s.zs.listdir('/symlinktest.zip/linktosubdir'),
                       s.zs.listdir('/symlinktest.zip/subdir'))

        s.assertEquals(s.zs.listdir('/symlinktest.zip/linktosubdir/linktoself'),
                       s.zs.listdir('/symlinktest.zip/subdir'))

        s.assertEquals(s.zs.listdir('/symlinktest.zip/subdir/linktosubdir2'),
                       s.zs.listdir('/symlinktest.zip/subdir2'))
        
        
    def test_symlink_open(s):
        realtxt = "Test.\n"
        real2txt = "asdf\n"

        # Establish basis for tests is correct.
        
        s.assertEquals(s.zs.open('/symlinktest.zip/real.txt').read(),
                       realtxt)
        s.assertEquals(s.zs.open('/symlinktest.zip/subdir2/real2.txt').read(),
                       real2txt)

        # Now, run the tests.
        s.assertEquals(s.zs.open('/symlinktest.zip/subdir/linked2.txt').read(),
                       real2txt)
        s.assertEquals(s.zs.open('/symlinktest.zip/linked.txt').read(),
                       realtxt)
        s.assertEquals(s.zs.open('/symlinktest.zip/linktosubdir/linked2.txt').read(),
                       real2txt)
        s.assertEquals(s.zs.open('/symlinktest.zip/linktosubdir/linkedabs.txt').read(),
                       realtxt)
        s.assertEquals(s.zs.open('/symlinktest.zip/linktosubdir/linktoself/linktoself/linktoself/linkedrel.txt').read(),
                       realtxt)
        s.assertEquals(s.zs.open('/symlinktest.zip/subdir/linktosubdir2/real2.txt').read(),
                       real2txt)

        s.assertEquals(s.zs.open('/symlinktest.zip/linktosubdir/linkedrel.txt').read(),
                       realtxt)

        s.assertRaises(IOError, s.zs.open, '/symlinktest.zip')
        s.assertRaises(IOError, s.zs.open, '/symlinktest.zip/subdir')
        s.assertRaises(IOError, s.zs.open, '/symlinktest.zip/linktosubdir')
        s.assertRaises(IOError, s.zs.open, '/symlinktest.zip/subdir/linktoself')
        s.assertRaises(IOError, s.zs.open, '/symlinktest.zip/linktosubdir/linktoself/linktosubdir2')

    def test_symlink_isdir(s):
        assert s.zs.isdir('/symlinktest.zip/subdir')
        assert s.zs.isdir('/symlinktest.zip/linktosubdir')
        assert not s.zs.isdir('/symlinktest.zip/linked.txt')
        assert not s.zs.isdir('/symlinktest.zip/real.txt')

        assert s.zs.isdir('/symlinktest.zip/subdir/linktoself')
        assert s.zs.isdir('/symlinktest.zip/subdir/linktosubdir2')
        assert s.zs.isdir('/symlinktest.zip/linktosubdir/linktoself/linktosubdir2')
        assert not s.zs.isdir('/symlinktest.zip/nonexistant')
        assert not s.zs.isdir('/symlinktest.zip/subdir/linkedrel.txt')
        assert s.zs.isdir('/symlinktest.zip')

    def test_symlink_isfile(s):
        assert s.zs.isfile('/symlinktest.zip/real.txt')
        assert not s.zs.isfile('/symlinktest.zip')
        assert not s.zs.isfile('/symlinktest.zip/subdir')
        assert not s.zs.isfile('/symlinktest.zip/linktosubdir')
        assert s.zs.isfile('/symlinktest.zip/linktosubdir/linkedrel.txt')
        assert s.zs.isfile('/symlinktest.zip/linktosubdir/linked2.txt')
        assert s.zs.isfile('/symlinktest.zip/subdir/linktoself/linktosubdir2/real2.txt')
        assert not s.zs.isfile('/symlinktest.zip/subdir/linktoself/linktosubdir2/real.txt')
        
    def test_open(s):
        s.assertRaises(IOError, s.z.open, '/testdata.zip/pygopherd')
        s.assertRaises(IOError, s.z2.open, '/testdata2.zip/pygopherd')
        s.assertRaises(IOError, s.z2.open, '/testdata.zip/pygopherd')

        assert s.z.open("/testdata.zip/.abstract")

        s.assertEquals(s.z.open('/testdata.zip/testfile.txt').read(),
                       'Test\n')
        shouldbe = "Word1\nWord2\nWord3\n"
        s.assertEquals(s.z.open('/testdata.zip/pygopherd/pipetestdata').read(),
                       shouldbe)
        s.assertEquals(s.z2.open('/testdata2.zip/pygopherd/pipetestdata').read(),
                       shouldbe)
        
        
        
class ZIPHandler(base.BaseHandler):
    def canhandlerequest(self):
        """We can handle the request if it's a ZIP file, in our pattern, etc.
        """

        if not self.config.getboolean("handlers.ZIP.ZIPHandler",
                                      "enabled"):
            return 0


        pattern = re.compile(self.config.get("handlers.ZIP.ZIPHandler",
                                             "pattern"))

        basename = self.selector
        appendage = None

        while 1:
            if pattern.search(basename) and \
               self.vfs.isfile(basename) and \
               zipfile.is_zipfile(self.vfs.getfspath(basename)):
                self.basename = basename
                self.appendage = appendage
                return 1

            if len(basename) == 0 or basename == '/' or basename == '.' or \
               basename == './':
                return 0

            (head, tail) = os.path.split(basename)
            if appendage != None:
                appendage = os.path.join(tail, appendage)
            else:
                appendage = tail

            basename = head

    def _makehandler(self):
        if hasattr(self, 'handler'):
            return
        vfs = VFS_Zip(self.config, self.vfs, self.basename)
        from pygopherd.handlers import HandlerMultiplexer
        self.handler = HandlerMultiplexer.getHandler(self.getselector(),
                                                     self.searchrequest,
                                                     self.protocol,
                                                     self.config,
                                                     vfs = vfs)
        

    def prepare(self):
        self._makehandler()
        self.handler.prepare()

    def isdir(self):
        return self.handler.isdir()

    def getdirlist(self):
        return self.handler.getdirlist()

    def write(self, wfile):
        self.handler.write(wfile)
               
    def getentry(self):
        self._makehandler()
        return self.handler.getentry()
