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

import re, zipfile, time, stat, unittest, os.path, struct
from StringIO import StringIO

UNX_IFMT = 0170000
UNX_IFLNK = 0120000

from pygopherd.handlers import base

class VFS_Zip(base.VFS_Real):
    def __init__(self, config, chain, zipfilename):
        self.config = config
        self.chain = chain
        self.zipfilename = zipfilename
        zipfd = self.chain.open(self.zipfilename)
        self.zip = zipfile.ZipFile(zipfd, 'r')
        self.members = self.zip.namelist()

    def _needschain(self, selector):
        return not selector.startswith(self.zipfilename)

    def _islinkattr(self, attr):
        str = struct.pack('l', attr)
        str2 = str[2:5] + str[0:2]
        result = int(struct.unpack('L', str2)[0])
        return (result & UNX_IFMT) == UNX_IFLNK

    def _islinkinfo(self, info):
        return self._islinkattr(info.external_attr)

    def _islinkname(self, selector):
        fspath = self._getfspathfinal(selector)
        if not len(fspath):
            return 0
        if not fspath in self.members:
            return 0
        info = self.zip.getinfo(fspath)
        return self._islinkinfo(info)

    def _readlink(self, selector):
        if not self._islinkname(selector):
            raise ValueError, "Readlink called on %s which is not a link"

        retval = self._open(self._getfspathfinal(selector)).read()
        return retval

    def iswritable(self, selector):
        if self._needschain(selector):
            return self.chain.iswritable(selector)

        return 0

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

        if selector.endswith('/subdir/2'):
            raise NotImplementedError, 'DEBUG'

        while (not self._needschain(selector)) and \
                  self._islinkname(selector):
            linkdest = self._readlink(selector)
            if linkdest.startswith('/'):
                selector = os.path.normpath(linkdest)
            else:
                selector = os.path.dirname(selector) + '/' + linkdest
                selector = os.path.normpath(selector)


        return self._getfspathfinal(selector)

    def stat(self, selector):
        if self._needschain(selector):
            return self.chain.stat(selector)

        fspath = self.getfspath(selector)
        isfile = 0
        try:
            zi = self.zip.getinfo(fspath)
            isfile = 1
        except:
            pass

        if not isfile:
            direxists = filter(lambda x: x.startswith(fspath), self.members)
            if not len(direxists):
                raise OSError, "Entry %s does not exist in %s" %\
                      (selector, self.zipfilename)

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

        return self.exists(selector) and stat.S_ISDIR(self.stat(selector)[0])

    def isfile(self, selector):
        if self._needschain(selector):
            return self.chain.isfile(selector)

        return self.exists(selector) and stat.S_ISREG(self.stat(selector)[0])

    def exists(self, selector):
        if self._needschain(selector):
            return self.chain.exists(selector)

        fspath = self.getfspath(selector)
        if fspath in self.members:
            return 1

        # Special case for directories -- may not appear in the file
        # themselves.

        direxists = filter(lambda x: x.startswith(fspath), self.members)
        return len(direxists)

    def _open(self, fspath):
        return StringIO(self.zip.read(fspath))

    def open(self, selector, *args, **kwargs):
        if self._needschain(selector):
            return apply(self.chain.open, (selector,) + args, kwargs)

        if not self.isfile(selector):
            raise IOError, "Request to open %s which is not a file" % selector

        return self._open(self.getfspath(selector))

    def listdir(self, selector):
        if self._needschain(selector):
            return self.chain.listdir(selector)

        fspath = self.getfspath(selector)
        if not len(fspath):
            candidates = self.members
        else:
            candidates = filter(lambda x: x.startswith(fspath + '/'), self.members)

        # OK, now chop off the fspath part.
        candidates = [x[len(fspath):] for x in candidates]

        retval = []
        for item in candidates:
            if item.startswith('/'):
                item = item[1:]
            slashindex = item.find('/')
            if slashindex != -1:
                item = item[:slashindex]
            if len(item) and not item in retval:
                retval.append(item)

        return retval

class TestVFS_Zip(unittest.TestCase):
    def setUp(s):
        from ConfigParser import ConfigParser
        s.config = ConfigParser()
        s.config.add_section('pygopherd')
        s.config.set("pygopherd", "root", os.path.abspath('testdata'))
        s.real = base.VFS_Real(s.config)
        s.z = VFS_Zip(s.config, s.real, '/testdata.zip')
        s.z2 = VFS_Zip(s.config, s.real, '/testdata2.zip')

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
