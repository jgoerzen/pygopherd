from handlers import file, dir, url

def getHandler(selector, protocol, config):
    h = eval(config.get("handlers.HandlerMultiplexer", "handlers"))

    for handler in h:
        htry = handler(selector, protocol, config)
        if htry.canhandlerequest():
            return htry
