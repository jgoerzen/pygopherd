from __future__ import annotations

import codecs
import configparser
import os.path
import re
import shelve
import stat
import time
import typing
import zipfile

from pygopherd.handlers.base import BaseHandler, VFS_Real


CacheData = typing.Mapping[str, typing.Any]


class VFSZip(VFS_Real):

    # See docstring in populate_cache() for details
    dircache: CacheData

    # Contains filenames that were not found in the zipfile, to prevent extra
    # lookups if the same invalid path is repeatedly requested.
    invalid_paths: typing.Set[str]

    # For efficient lookup of the inode for a file without needing to
    # recursively traverse the dircache for each path segment.
    #     entrycache[directory_name][filename] = inode for that file
    entrycache: typing.Dict[str, typing.Dict[str, str]]

    def __init__(
        self, config: configparser.ConfigParser, chain: VFS_Real, zipfilename: str
    ):
        super().__init__(config, chain)
        self.zipfilename = zipfilename
        self.zipfd = self.chain.open(self.zipfilename, mode="rb")
        self.zip = zipfile.ZipFile(self.zipfd)

        self.invalid_paths = set()
        self.entrycache = {}
        self.init_cache()

    def __del__(self):
        if hasattr(self, "zipfd"):
            self.zipfd.close()

    def get_cache_filename(self) -> str:
        (dir_, file) = os.path.split(self.zipfilename)
        return os.path.join(dir_, ".cache.pygopherd.zip3." + file)

    def save_cache(self) -> bool:
        cache_filename = self.get_cache_filename()
        cache_fspath = self.chain.getfspath(cache_filename)
        try:
            with shelve.open(cache_fspath, "n") as db:
                for (key, value) in self.dircache.items():
                    db[key] = value
        except OSError:
            return False
        else:
            return True

    def init_cache(self) -> None:
        cache_filename = self.get_cache_filename()
        zipfile_mtime = self.chain.stat(self.zipfilename)[stat.ST_MTIME]
        try:
            cache_mtime = self.chain.stat(cache_filename)[stat.ST_MTIME]
        except OSError:
            # Couldn't stat the cache, attempt to rebuild it
            self.populate_cache()
            self.save_cache()
            return

        if zipfile_mtime > cache_mtime:
            # The zipfile has been modified since the cache was generated,
            # rebuild the cache.
            self.populate_cache()
            self.save_cache()
            return

        cache_fspath = self.chain.getfspath(cache_filename)
        try:
            self.dircache = shelve.open(cache_fspath, "r")
        except Exception:
            self.populate_cache()
            self.save_cache()

    def _isentryincache(self, fspath: str) -> bool:
        try:
            self._getcacheentry(fspath)
            return True
        except KeyError:
            return False

    def _getcacheentry(self, fspath: str) -> typing.Union[dict, str]:
        return self.dircache[self._getcacheinode(fspath)]

    def _getcacheinode(self, fspath: str) -> str:
        inode = "0"
        if fspath == "":
            return inode

        (dir_, file) = os.path.split(fspath)
        if dir_ in self.entrycache:
            return self.entrycache[dir_][file]
        elif dir_ in self.invalid_paths:
            raise KeyError("Call for %s: directory %s non-existant" % (fspath, dir_))

        workingdir = ""

        for item in fspath.split("/"):
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
                self.invalid_paths.add(workingdir)
                raise KeyError("Call for %s: Couldn't find %s" % (fspath, item))
        return inode

    def populate_cache(self):
        """
        Build a dictionary that will be used to represent the zipfile structure.

        - Keys are inodes (string integers, like "0", "1", ...)
        - Values can be either strings or dicts
          - If the value is a string, it points to the filename in the zipfile.
          - If the value is a dict, it's a recursive cache for that directory.

        The "0" inode is always the root directory. To lookup a path, split it
        into segments and traverse the cache one segment at a time.

        E.g.

        /
        /hello.txt
        /some_directory/goodbye.txt

        {
            '0': {'hello.txt': '1', 'some_directory': '2'},
            '1': 'hello.txt',
            '2': {'goodbye.txt': '3'},
            '3': '/some_directory/goodbye.txt'
        }
        """
        symlinkinodes = []
        nextinode = 1
        self.dircache = {"0": {}}

        for info in self.zip.infolist():
            (dir_, filename) = os.path.split(info.filename)
            if dir_ == "/":
                dir_ = ""

            dirlevel = self.dircache["0"]
            for level in dir_.split("/"):
                if level == "":
                    continue
                if level not in dirlevel:
                    self.dircache[str(nextinode)] = {}
                    dirlevel[level] = str(nextinode)
                    nextinode += 1
                dirlevel = self.dircache[dirlevel[level]]

            if filename:
                if self._islinkinfo(info):
                    symlinkinodes.append(
                        {
                            "dirlevel": dirlevel,
                            "filename": filename,
                            "pathname": info.filename,
                            "dest": self._readlinkfspath(info.filename),
                        }
                    )
                else:
                    dirlevel[filename] = str(nextinode)
                    self.dircache[str(nextinode)] = info.filename  # used to be location
                    nextinode += 1

        lastsymlinklen = 0
        while len(symlinkinodes) and len(symlinkinodes) != lastsymlinklen:
            lastsymlinklen = len(symlinkinodes)
            newsymlinkinodes = []
            for item in symlinkinodes:
                if item["dest"][0] == "/":
                    dest = item["dest"][1:]
                else:
                    dest = os.path.join(os.path.dirname(item["pathname"]), item["dest"])
                    dest = os.path.normpath(dest)
                if self._isentryincache(dest):
                    item["dirlevel"][item["filename"]] = self._getcacheinode(dest)
                else:
                    newsymlinkinodes.append(item)
            symlinkinodes = newsymlinkinodes

    def _islinkinfo(self, info: zipfile.ZipInfo) -> bool:
        return stat.S_ISLNK(info.external_attr >> 16)

    def _readlinkfspath(self, fspath: str) -> str:
        return self.zip.read(fspath).decode(errors="surrogateescape")

    def _readlink(self, selector: str) -> str:
        return self._readlinkfspath(self._getfspathfinal(selector))

    def iswritable(self, selector: str) -> bool:
        return False

    def unlink(self, selector: str):
        raise NotImplementedError("VFSZip cannot unlink files.")

    def _getfspathfinal(self, selector: str) -> str:
        # Strip off the filename part.
        selector = selector[len(self.zipfilename) :]

        if selector.startswith("/"):
            selector = selector[1:]

        if selector.endswith("/"):
            selector = selector[:-1]

        return selector

    def getfspath(self, selector: str) -> str:
        return self._getfspathfinal(selector)

    def stat(self, selector: str):
        fspath = self.getfspath(selector)
        try:
            zi = self._getcacheentry(fspath)
        except KeyError:
            raise OSError(
                "Entry %s does not exist in %s" % (selector, self.zipfilename)
            )

        if type(zi) == dict:
            # It's a directory.
            return (
                16877,  # mode
                0,  # inode
                0,  # device
                3,  # links
                0,  # uid
                0,  # gid
                0,  # size
                0,  # access time
                0,  # modification time
                0,
            )  # change time

        zi = self.zip.getinfo(fspath)

        zt = zi.date_time
        modtime = time.mktime(zt + (0, 0, -1))
        return (
            33188,  # mode
            0,  # inode
            0,  # device
            1,  # links
            0,  # uid
            0,  # gid
            zi.file_size,  # size
            modtime,  # access time
            modtime,  # modification time
            modtime,
        )  # change time

    def isdir(self, selector: str) -> bool:
        fspath = self.getfspath(selector)
        try:
            item = self._getcacheentry(fspath)
        except KeyError:
            return False

        return type(item) == dict

    def isfile(self, selector: str) -> bool:
        fspath = self.getfspath(selector)
        try:
            item = self._getcacheentry(fspath)
        except KeyError:
            return False

        return type(item) != dict

    def exists(self, selector: str) -> bool:
        fspath = self.getfspath(selector)
        return self._isentryincache(fspath)

    def open(
        self, selector: str, mode: str = "rb", errors: typing.Optional[str] = None
    ) -> typing.IO:

        assert mode in ("r", "rb")

        fspath = self.getfspath(selector)
        try:
            item = self._getcacheentry(fspath)
        except KeyError:
            raise IOError("Request to open %s, which does not exist" % selector)

        if type(item) == dict:
            raise IOError(
                "Request to open %s, which is a directory (%s)" % (selector, str(item))
            )

        # zip.open() will only return the file object in bytes mode
        fp = self.zip.open(item)
        if mode == "r":
            # Attempted to read in "text mode", so decode the bytestream
            fp = codecs.getreader("utf-8")(fp)

        return fp

    def listdir(self, selector: str) -> typing.List[str]:
        fspath = self.getfspath(selector)
        try:
            retobj = self._getcacheentry(fspath)
        except KeyError:
            raise OSError(
                "listdir on %s (%s) failed: no such file or directory"
                % (selector, fspath)
            )

        if type(retobj) != dict:
            raise OSError(
                "listdir on %s failed: that is a file, not a directory.  Got %s"
                % (selector, str(retobj))
            )

        return list(retobj.keys())


class ZIPHandler(BaseHandler):

    handler: BaseHandler

    def canhandlerequest(self):
        """
        We can handle the request if it's a ZIP file, in our pattern, etc.
        """

        if not self.config.getboolean("handlers.ZIP.ZIPHandler", "enabled"):
            return False

        pattern = re.compile(self.config.get("handlers.ZIP.ZIPHandler", "pattern"))

        basename = self.selector
        appendage = None

        while True:

            if pattern.search(basename) and self.vfs.isfile(basename):
                # is_zipfile() accepts filenames as bytes, but the type stub is incorrect
                if zipfile.is_zipfile(self.vfs.getfspath(basename)):  # noqa
                    self.basename = basename
                    self.appendage = appendage
                    return True

            if (
                len(basename) == 0
                or basename == "/"
                or basename == "."
                or basename == "./"
            ):
                return False

            (head, tail) = os.path.split(basename)
            if appendage is not None:
                appendage = os.path.join(tail, appendage)
            else:
                appendage = tail

            basename = head

    def _makehandler(self):
        from pygopherd.handlers import HandlerMultiplexer

        if hasattr(self, "handler"):
            return
        vfs = VFSZip(self.config, self.vfs, self.basename)

        self.handler = HandlerMultiplexer.getHandler(
            self.getselector(), self.searchrequest, self.protocol, self.config, vfs=vfs
        )

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
