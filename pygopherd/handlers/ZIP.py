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

import re, zipfile, time, stat, unittest, os.path, struct, types, copy
import cPickle, fcntl
from StringIO import StringIO

UNX_IFMT = 0170000
UNX_IFLNK = 0120000

from pygopherd.handlers import base

def GetPicklableZipFile(zipfile, chain, zipfilename, dircache):
    pzf = copy.copy(zipfile)
    pzf.fp = None
    return (pzf, chain, zipfilename, dircache)

def UnpickleZipFileObject(pickleobj):
    """Warning: if read-write ZIPs are ever implemented along with
    nested zips, this or the above may break.

    Returns a new (ZipFile, dircache) object."""

    (zipfile, chain, zipfilename, dircache) = pickleobj
    zipfile.fp = chain.open(zipfilename)
    return (zipfile, dircache)

class VFS_Zip(base.VFS_Real):
    def __init__(self, config, chain, zipfilename):
        self.config = config
        self.chain = chain
        self.zipfilename = zipfilename
        self._initzip()

    def _getcachefilename(self):
        (dir, file) = os.path.split(self.zipfilename)
        return os.path.join(dir, '.cache.pygopherd.zip.' + file)

    def _loadcache(self):
        filename = self._getcachefilename()
        if self.chain.iswritable(filename):
            zipfilemtime = self.chain.stat(self.zipfilename)[stat.ST_MTIME]
            try:
                cachemtime = self.chain.stat(filename)[stat.ST_MTIME]
            except OSError:
                return 0

            if zipfilemtime > cachemtime:
                return 0
            
            try:
                fd = self.chain.open(filename)
            except OSError:
                return 0

            fcntl.flock(fd, fcntl.LOCK_SH)
            (self.zip, self.dircache) = \
                           UnpickleZipFileObject(cPickle.load(fd))
            fcntl.flock(fd, fcntl.LOCK_UN)
            return 1

    def _savecache(self):
        filename = self._getcachefilename()
        if not self.chain.iswritable(filename):
            return

        try:
            fd = self.chain.open(filename, 'wb')
        except OSError:
            return

        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            cPickle.dump(GetPicklableZipFile(self.zip, self.chain,
                                             self.zipfilename, self.dircache),
                         fd, 1)
        except:
            self.chain.unlink(filename)
            fd.close()
            raise

        fd.close()

    def _initzip(self):
        if self._loadcache():
            self.memberinfo = self.zip.NameToInfo
        else:
            # For reading from a new Zip file.
            zipfd = self.chain.open(self.zipfilename)
            self.zip = zipfile.ZipFile(zipfd, 'r')
            self.dircache = None
            # For reloading an existing one.  Must be called before _cachedir.
            self.memberinfo = self.zip.NameToInfo
            self._cachedir()
            self._savecache()

    def _isentryincache(self, fspath):
        try:
            self._getcacheentry(fspath)
            return 1
        except KeyError:
            return 0

    def _getcacheentry(self, fspath):
        cur = self.dircache
        if fspath == '':
            return cur
        for item in fspath.split('/'):
            if type(cur) != types.DictType:
                raise KeyError, "Call for %s: couldn't find %s" % (fspath, item)
            try:
                cur = cur[item]
            except KeyError:
                raise KeyError, "Call for %s: Couldn't find %s" % (fspath, item)
        return cur

    def _cachedir(self):
        if self.dircache != None:
            return

        self.dircache = {}

        for (file, info) in self.memberinfo.iteritems():
            (dir, filename) = os.path.split(file)
            if dir == '/':
                dir == ''

            dirlevel = self.dircache
            for level in dir.split('/'):
                if level == '':
                    continue
                if not dirlevel.has_key(level):
                    dirlevel[level] = {}
                dirlevel = dirlevel[level]

            if len(filename):
                dirlevel[filename] = info

    def _needschain(self, selector):
        return not selector.startswith(self.zipfilename)

    def _islinkattr(self, attr):
        str = struct.pack('l', attr)
        str2 = str[2:5] + str[0:2]
        result = int(struct.unpack('L', str2)[0])
        return (result & UNX_IFMT) == UNX_IFLNK

    def _islinkinfo(self, info):
        if type(info) == types.DictType:
            return 0
        return self._islinkattr(info.external_attr)

    def _islinkfspath(self, fspath):
        if not len(fspath):
            return 0

        try:
            info = self._getcacheentry(fspath)
        except KeyError:
            return 0
        
        return self._islinkinfo(info)

    def _islinkname(self, selector):
        return self._islinkfspath(self._getfspathfinal(selector))

    def _readlinkfspath(self, fspath):
        if not self._islinkfspath(fspath):
            raise ValueError, "Readlinkfspath called on %s which is not a link"

        return self._open(fspath).read()

    def _readlink(self, selector):
        return self._readlinkfspath(self, self._getfspathfinal(selector))

    def iswritable(self, selector):
        if self._needschain(selector):
            return self.chain.iswritable(selector)

        return 0

    def unlink(self, selector):
        raise NotImplementedError, "VFS_ZIP cannot unlink files."

    def _getfspathfinal(self, selector):
        # Strip off the filename part.
        selector = selector[len(self.zipfilename):]

        if selector.startswith('/'):
            selector = selector[1:]

        if selector.endswith('/'):
            selector = selector[:-1]

        return selector
    
    def _transformlink(self, fspath):
        while self._islinkfspath(fspath):
            linkdest = self._readlinkfspath(fspath)
            if linkdest.startswith('/'):
                fspath = os.path.normpath(linkdest)[1:]
            else:
                fspath = os.path.join(os.path.dirname(fspath), linkdest)
                fspath = os.path.normpath(fspath)

        return fspath
        

    def getfspath(self, selector):
        print ' ******** getfspath ********'
        if self._needschain(selector):
            return self.chain.getfspath(selector)

        # We can skip the initial part -- it just contains the start of
        # the path.

        selector = self._getfspathfinal(selector)
        print "selector =", selector
        if not len(selector):
            return selector

        # Build from the bottom up.
        newselector = ''
        components = selector.split('/')

        print "components =", components
        for item in components:
            print "item =", item
            newselector = os.path.join(newselector, item)
            newselector = self._transformlink(newselector)
            print "newselector =", newselector

        return os.path.normpath(newselector)

    def stat(self, selector):
        if self._needschain(selector):
            return self.chain.stat(selector)

        fspath = self.getfspath(selector)
        try:
            zi = self._getcacheentry(fspath)
        except KeyError:
            raise OSError, "Entry %s does not exist in %s" %\
                  (selector, self.zipfilename)
        
        if type(zi) == types.DictType:
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
            

    def isdir(self, selector):
        if self._needschain(selector):
            return self.chain.isdir(selector)

        fspath = self.getfspath(selector)
        try:
            item = self._getcacheentry(fspath)
        except KeyError:
            return 0

        return type(item) == types.DictType

    def isfile(self, selector):
        if self._needschain(selector):
            return self.chain.isfile(selector)

        fspath = self.getfspath(selector)
        try:
            item = self._getcacheentry(fspath)
        except KeyError:
            return 0

        return type(item) != types.DictType

    def exists(self, selector):
        if self._needschain(selector):
            return self.chain.exists(selector)

        fspath = self.getfspath(selector)
        return self._isentryincache(fspath)

    def _open(self, fspath):
        return StringIO(self.zip.read(fspath))

    def open(self, selector, *args, **kwargs):
        if self._needschain(selector):
            return apply(self.chain.open, (selector,) + args, kwargs)

        fspath = self.getfspath(selector)
        try:
            item = self._getcacheentry(fspath)
        except KeyError:
            raise IOError, "Request to open %s, which does not exist" % selector
        if type(item) == types.DictType:
            raise IOError, "Request to open %s, which is a directory" % selector

        return self._open(fspath)

    def listdir(self, selector):
        if self._needschain(selector):
            return self.chain.listdir(selector)

        fspath = self.getfspath(selector)
        try:
            retobj = self._getcacheentry(fspath)
        except KeyError:
            raise OSError, "listdir on %s (%s) failed: no such file or directory" % (selector, fspath)

        if type(retobj) != types.DictType:
            raise OSError, "listdir on %s failed: that is a file, not a directory" % selector

        return retobj.keys()


class TestVFS_Zip_huge(unittest.TestCase):
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

    def testlistdir3(self):
        from pygopherd.protocols.rfc1436 import GopherProtocol
        self.proto = GopherProtocol("/foo.zip/lib/dpkg/info\n",
                                    self.server,
                                    self.handler, self.rfile, self.wfile,
                                    self.config)
        self.proto.handle()
        
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
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/linked.txt'),
                                      'real.txt')
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/linktosubdir'),
                                      'subdir')
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/subdir/linked2.txt'),
                                      'subdir2/real2.txt')
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/linktosubdir/linked2.txt'),
                                      'subdir2/real2.txt')
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/linktosubdir/linkedabs.txt'),
                                      'real.txt')
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/linktosubdir/linktoself'),
                                      'subdir')
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/subdir/linktosubdir2'),
                                      'subdir2')
        s.assertEquals(s.zs.getfspath('/symlinktest.zip/linktosubdir/linkedrel.txt'),
                                      'real.txt')

    def test_islinkname(s):
        assert not s.zs._islinkname('/symlinktest.zip/real.txt')
        assert not s.zs._islinkname('/symlinktest.zip/nonexistant')
        assert s.zs._islinkname('/symlinktest.zip/linktosubdir')
        assert s.zs._islinkname('/symlinktest.zip/subdir/linkedrel.txt')

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
        s.assertEquals(s.zs.open('/symlinktest.zip/linktosubdir/linked2.txt').read(),
                       real2txt)
        s.assertEquals(s.zs.open('/symlinktest.zip/linktosubdir/linktoself/linktoself/linktoself/linkedrel.txt').read(),
                       realtxt)
        s.assertEquals(s.zs.open('/symlinktest.zip/subdir/linktosubdir2/real2.txt').read(),
                       real2txt)

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
