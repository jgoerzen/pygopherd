import handlers, handlers.file, handlers.dir

def getHandler(selector, protocol, config):
    h = [handlers.file.FileHandler, handlers.dir.DirHandler]

    for handler in h:
        htry = handler(selector, protocol, config)
        if htry.canhandlerequest():
            return htry
