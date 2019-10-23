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

import re, time, stat, unittest, os.path, struct, types, shelve, marshal
from io import StringIO
from pygopherd import zipfile

class MarshalingShelf(shelve.Shelf):
    def __getitem__(self, key):
        return marshal.loads(self.dict[key])

    def __setitem__(self, key, value):
        self.dict[key] = marshal.dumps(value)

class DbfilenameShelf(MarshalingShelf):
    def __init__(self, filename, flag='c'):
        import dbm
        MarshalingShelf.__init__(self, dbm.open(filename, flag))

def shelveopen(filename, flag='c'):
    return DbfilenameShelf(filename, flag)

UNX_IFMT = 0o170000
UNX_IFLNK = 0o120000

from pygopherd.handlers import base

class VFS_Zip(base.VFS_Real):
    def __init__(self, config, chain, zipfilename):
        self.config = config
        self.chain = chain
        self.zipfilename = zipfilename
        self.entrycache = {}
        self.badcache = {}
        self._initzip()

    def _getcachefilename(self):
        (dir, file) = os.path.split(self.zipfilename)
        return os.path.join(dir, '.cache.pygopherd.zip.' + file)

    def _initcache(self):
        """Returns 1 if a cache was found existing; 0 if not."""
        filename = self._getcachefilename()
        if isinstance(self.chain, base.VFS_Real) and \
               self.chain.iswritable(filename):
            fspath = self.chain.getfspath(filename)
            zipfilemtime = self.chain.stat(self.zipfilename)[stat.ST_MTIME]
            try:
                cachemtime = self.chain.stat(filename)[stat.ST_MTIME]
            except OSError:
                self._createcache(fspath)
                return 0

            if zipfilemtime > cachemtime:
                self._createcache(fspath)
                return 0
            
            try:
                self.dircache = shelveopen(fspath, 'r')
            except:
                self._createcache(fspath)
                return 0

            return 1

    def _createcache(self, fspath):
        self.dircache = {}
        try:
            self.dbdircache = shelveopen(fspath, 'n')
        except e:
            GopherExceptions.log(e, handler = self)
            return 0

    def _savecache(self):
        if not hasattr(self, 'dbdircache'):
            # createcache was somehow unsuccessful
            return
        for (key, value) in self.dircache.items():
            self.dbdircache[key] = value

    def _initzip(self):
        zipfd = self.chain.open(self.zipfilename)
        self.zip = zipfile.ZipReader(zipfd)
        if not self._initcache():
            # For reloading an existing one.  Must be called before _cachedir.
            self._cachedir()
            self._savecache()
            self.dbdircache.close()       # Flush it out

    def _isentryincache(self, fspath):
        try:
            self._getcacheentry(fspath)
            return 1
        except KeyError:
            return 0

    def _getcacheentry(self, fspath):
        return self.dircache[self._getcacheinode(fspath)]

    def _getcacheinode(self, fspath):
        inode = '0'
        if fspath == '':
            return inode

        (dir, file) = os.path.split(fspath)
        if dir in self.entrycache:
            return self.entrycache[dir][file]
        elif dir in self.badcache:
            raise KeyError("Call for %s: directory %s non-existant" % (fspath, dir))

        workingdir = ''
        
        for item in fspath.split('/'):
            # right now, directory holds the directory from the *last* iteration.
            directory = self.dircache[inode]
            if type(directory) != dict:
                raise KeyError("Call for %s: couldn't find %s" % (fspath, item))
            self.entrycache[workingdir] = directory
            
            workingdir = os.path.join(workingdir, item)
            try:
                # Now, inode holds the inode number.
                inode = directory[item]
            except KeyError:
                self.badcache[workingdir] = 1
                raise KeyError("Call for %s: Couldn't find %s" % (fspath, item))
        return inode
        
    def _cachedir(self):
        symlinkinodes = []
        nextinode = 1
        self.zip.GetContents()
        self.dircache = {'0': {}}

        for (file, location) in self.zip.locationmap.items():
            info = self.zip.getinfo(file)
            (dir, filename) = os.path.split(file)
            if dir == '/':
                dir == ''

            dirlevel = self.dircache['0']
            for level in dir.split('/'):
                if level == '':
                    continue
                if level not in dirlevel:
                    self.dircache[str(nextinode)] = {}
                    dirlevel[level] = str(nextinode)
                    nextinode += 1
                dirlevel = self.dircache[dirlevel[level]]

            if len(filename):
                if self._islinkinfo(info):
                    symlinkinodes.append({'dirlevel': dirlevel,
                                          'filename': filename,
                                          'pathname': file,
                                          'dest': self._readlinkfspath(file)})
                else:
                    dirlevel[filename] = str(nextinode)
                    self.dircache[str(nextinode)] = location
                    nextinode += 1

        lastsymlinklen = 0
        while len(symlinkinodes) and len(symlinkinodes) != lastsymlinklen:
            lastsymlinklen = len(symlinkinodes)
            newsymlinkinodes = []
            for item in symlinkinodes:
                if item['dest'][0] == '/':
                    dest = item['dest'][1:]
                else:
                    dest = os.path.join(os.path.dirname(item['pathname']),
                                        item['dest'])
                    dest = os.path.normpath(dest)
                if self._isentryincache(dest):
                    item['dirlevel'][item['filename']] = \
                        self._getcacheinode(dest)
                else:
                    newsymlinkinodes.append(item)
            symlinkinodes = newsymlinkinodes
                                                         
    def _islinkattr(self, attr):
        str = struct.pack('L', attr)
        str2 = str[2:5] + str[0:2]
        result = struct.unpack('L', str2)[0]
        return (result & UNX_IFMT) == UNX_IFLNK

    def _islinkinfo(self, info):
        if type(info) == dict:
            return 0
        return self._islinkattr(info.external_attr)

    def _readlinkfspath(self, fspath):
        # Since only called from the cache thing, this isn't needed.
        #if not self._islinkfspath(fspath):
        #    raise ValueError, "Readlinkfspath called on %s which is not a link" % fspath

        return self.zip.read(fspath)

    def _readlink(self, selector):
        return self._readlinkfspath(self, self._getfspathfinal(selector))

    def iswritable(self, selector):
        return 0

    def unlink(self, selector):
        raise NotImplementedError("VFS_ZIP cannot unlink files.")

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
        # We can skip the initial part -- it just contains the start of
        # the path.

        return self._getfspathfinal(selector)

    def stat(self, selector):
        fspath = self.getfspath(selector)
        try:
            zi = self._getcacheentry(fspath)
        except KeyError:
            raise OSError("Entry %s does not exist in %s" %\
                  (selector, self.zipfilename))
        
        if type(zi) == dict:
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

        zi = self.zip.getinfofrompos(zi)

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
        fspath = self.getfspath(selector)
        try:
            item = self._getcacheentry(fspath)
        except KeyError:
            return 0

        return type(item) == dict

    def isfile(self, selector):
        fspath = self.getfspath(selector)
        try:
            item = self._getcacheentry(fspath)
        except KeyError:
            return 0

        return type(item) != dict

    def exists(self, selector):
        fspath = self.getfspath(selector)
        return self._isentryincache(fspath)

    def _open(self, fspath):
        return self.zip.open_pos(self._getcacheentry(fspath))

    def open(self, selector, *args, **kwargs):
        fspath = self.getfspath(selector)
        try:
            item = self._getcacheentry(fspath)
        except KeyError:
            raise IOError("Request to open %s, which does not exist" % selector)
        if type(item) == dict:
            raise IOError("Request to open %s, which is a directory (%s)" % (selector, str(item)))

        return self.zip.open_pos(item)

    def listdir(self, selector):
        fspath = self.getfspath(selector)
        try:
            retobj = self._getcacheentry(fspath)
        except KeyError:
            raise OSError("listdir on %s (%s) failed: no such file or directory" % (selector, fspath))

        if type(retobj) != dict:
            raise OSError("listdir on %s failed: that is a file, not a directory.  Got %s" % (selector, str(retobj)))

        return list(retobj.keys())


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
        from configparser import ConfigParser
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
        s.assertEqual(m1, m2)
        s.assertEqual(m1, ['.abstract', 'README', 'pygopherd',
                            'testarchive.tar', 'testarchive.tar.gz',
                            'testarchive.tgz', 'testfile.txt',
                            'testfile.txt.gz', 'testfile.txt.gz.abstract'])

        m1 = s.z.listdir('/testdata.zip/pygopherd')
        m2 = s.z2.listdir('/testdata2.zip/pygopherd')

        m1.sort()
        m2.sort()

        s.assertEqual(m1, m2 + ['ziponly'])
        s.assertEqual(m1, ['pipetest.sh', 'pipetestdata', 'ziponly'])

    def test_needschain(s):
        return
        assert s.z._needschain('/testfile.txt')
        assert s.z._needschain('/foo/testdata.zip')
        assert not s.z._needschain('/testdata.zip')
        assert not s.z._needschain('/testdata.zip/foo')
        assert not s.z._needschain('/testdata.zip/foo/bar')

    def test_iswritable(s):
        assert not s.z.iswritable('/testdata.zip')
        assert not s.z.iswritable('/testdata.zip/README')
        assert not s.z.iswritable('/testdata.zip/pygopherd')
        #assert s.z.iswritable('/README')
        #assert s.z.iswritable('/.foo')

    def test_getfspath(s):
        s.assertEqual(s.z.getfspath('/testdata.zip/foo'), 'foo')
        s.assertEqual(s.z.getfspath('/testdata.zip'), '')
        s.assertEqual(s.z.getfspath('/testdata.zip/foo/bar'), 'foo/bar')

    def test_stat(s):
        s.assertRaises(OSError, s.z.stat, '/testdata.zip/nonexistant')
        #s.assertRaises(OSError, s.z.stat, '/nonexistant')
        #assert stat.S_ISREG(s.z.stat('/testfile.txt')[0])
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
        #assert not s.z2.exists('/testdata.zip/pygopherd')

    def test_symlinkexists(s):
        assert s.zs.exists('/symlinktest.zip/real.txt')
        assert s.zs.exists('/symlinktest.zip/linked.txt')
        assert s.zs.exists('/symlinktest.zip/subdir/linktosubdir2')

    def test_symlinkgetfspath(s):
        s.assertEqual(s.zs.getfspath('/symlinktest.zip'), '')
        s.assertEqual(s.zs.getfspath('/symlinktest.zip/real.txt'), 'real.txt')
        s.assertEqual(s.zs.getfspath('/symlinktest.zip/subdir'), 'subdir')
        s.assertEqual(s.zs.getfspath('/symlinktest.zip/subdir2/real2.txt'),
                                      'subdir2/real2.txt')


    def test_symlink_listdir(s):
        m1 = s.zs.listdir('/symlinktest.zip')
        m1.sort()

        s.assertEqual(m1, ['linked.txt', 'linktosubdir', 'real.txt',
                            'subdir', 'subdir2'])

        tm2 = ['linked2.txt', 'linkedabs.txt', 'linkedrel.txt', 'linktoself',
               'linktosubdir2']
        m2 = s.zs.listdir('/symlinktest.zip/subdir')
        m2.sort()
        s.assertEqual(m2, tm2)

        m2 = s.zs.listdir('/symlinktest.zip/linktosubdir')
        m2.sort()
        s.assertEqual(m2, tm2)

        s.assertRaises(OSError, s.zs.listdir, '/symlinktest.zip/nonexistant')
        s.assertRaises(OSError, s.zs.listdir, '/symlinktest.zip/real.txt')
        s.assertRaises(OSError, s.zs.listdir, '/symlinktest.zip/linktosubdir/linkedrel.txt')

        m2 = s.zs.listdir('/symlinktest.zip/linktosubdir/linktoself/linktoself')
        
        m2.sort()
        s.assertEqual(m2, tm2)

        m3 = s.zs.listdir('/symlinktest.zip/linktosubdir/linktoself/linktosubdir2')
        s.assertEqual(m3, ['real2.txt'])
        
    def test_symlink_open(s):
        realtxt = "Test.\n"
        real2txt = "asdf\n"

        # Establish basis for tests is correct.
        
        s.assertEqual(s.zs.open('/symlinktest.zip/real.txt').read(),
                       realtxt)
        s.assertEqual(s.zs.open('/symlinktest.zip/subdir2/real2.txt').read(),
                       real2txt)

        # Now, run the tests.
        s.assertEqual(s.zs.open('/symlinktest.zip/subdir/linked2.txt').read(),
                       real2txt)
        s.assertEqual(s.zs.open('/symlinktest.zip/linktosubdir/linked2.txt').read(),
                       real2txt)
        s.assertEqual(s.zs.open('/symlinktest.zip/linktosubdir/linkedabs.txt').read(),
                       realtxt)
        s.assertEqual(s.zs.open('/symlinktest.zip/linktosubdir/linktoself/linktoself/linktoself/linkedrel.txt').read(),
                       realtxt)
        s.assertEqual(s.zs.open('/symlinktest.zip/subdir/linktosubdir2/real2.txt').read(),
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

        s.assertEqual(s.z.open('/testdata.zip/testfile.txt').read(),
                       'Test\n')
        shouldbe = "Word1\nWord2\nWord3\n"
        s.assertEqual(s.z.open('/testdata.zip/pygopherd/pipetestdata').read(),
                       shouldbe)
        s.assertEqual(s.z2.open('/testdata2.zip/pygopherd/pipetestdata').read(),
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
