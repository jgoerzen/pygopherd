import types

class FileNotFound:
    def __init__(self, arg):
        self.selector = arg
        self.comments = ''

        if type(arg) != types.StringType:
            self.selector = arg[0]
            self.comments = arg[1]
            
    def __str__(self):
        retval = "'%s' does not exist" % self.selector
        if self.comments:
            retval += " (%s)" % self.comments
        return retval
