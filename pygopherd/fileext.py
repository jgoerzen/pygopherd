import functools
import mimetypes

typemap = {}


def extcmp(x, y):
    if x.count(".") > y.count("."):
        return 1
    if x.count(".") < y.count("."):
        return -1
    if len(x) > len(y):
        return 1
    if len(x) < len(y):
        return -1
    return (x > y) - (y < x)


extkey = functools.cmp_to_key(extcmp)


def extstrip(file, filetype):
    """Strips off the extension from file given type and returns the result.
    Returns file unmodified if no action is possible."""
    if not (filetype and filetype in typemap):
        return file
    for possible in typemap[filetype]:
        if file.endswith(possible):
            extindex = file.rfind(possible)
            return file[0:extindex]
    return file


def init():
    for fileext, filetype in list(mimetypes.types_map.items()):
        extlist = []
        if filetype in typemap:
            extlist = typemap[filetype]

        baselist = []
        # Add the basic extension.
        baselist.append(fileext)
        # Add it in all encoding flavors.
        baselist.extend([fileext + enc for enc in list(mimetypes.encodings_map.keys())])

        for shortsuff, longsuff in list(mimetypes.suffix_map.items()):
            if longsuff in baselist:
                baselist.append(shortsuff)

        extlist.extend(baselist)
        extlist.sort(key=extkey)
        extlist.reverse()
        typemap[filetype] = extlist
