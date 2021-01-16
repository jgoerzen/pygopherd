from __future__ import annotations

import configparser
import typing

from pygopherd import GopherExceptions

# Running eval() when loading the configuration requires all of the handlers to
# be in the module namespace
from pygopherd.handlers import *  # noqa
from pygopherd.handlers.base import BaseHandler, VFS_Real

if typing.TYPE_CHECKING:
    from pygopherd.protocols.base import BaseGopherProtocol


handlers = None
rootpath = None


def init_default_handlers(config: configparser.ConfigParser) -> None:
    global handlers, rootpath
    if not handlers:
        handlers = eval(config.get("handlers.HandlerMultiplexer", "handlers"))
        rootpath = config.get("pygopherd", "root")


def getHandler(
    selector: str,
    searchrequest: str,
    protocol: BaseGopherProtocol,
    config: configparser.ConfigParser,
    handlerlist: typing.Optional[typing.List[BaseHandler]] = None,
    vfs: typing.Optional[VFS_Real] = None,
):
    """Called without handlerlist specified, uses the default as listed
    in config."""
    global handlers, rootpath
    init_default_handlers(config)

    typing.cast(handlers, typing.List[BaseHandler])
    typing.cast(rootpath, str)

    if vfs is None:
        vfs = VFS_Real(config)

    if handlerlist is None:
        handlerlist = handlers

    # SECURITY: assert that our absolute path is within the absolute
    # path of the site root.

    # if not os.path.abspath(rootpath + '/' + selector). \
    #   startswith(os.path.abspath(rootpath)):
    #    raise GopherExceptions.FileNotFound, \
    #          [selector, "Requested document is outside the server root",
    #           protocol]

    statresult = None
    try:
        statresult = vfs.stat(selector)
    except OSError:
        pass
    for handler in handlerlist:
        htry = handler(selector, searchrequest, protocol, config, statresult, vfs)
        if htry.isrequestforme():
            return htry.gethandler()

    raise GopherExceptions.FileNotFound(selector, "no handler found", protocol)
