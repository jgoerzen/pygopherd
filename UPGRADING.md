# Upgrading to PyGopherd v3.0

Notes for updating an existing PyGopherd server deployment to run on python 3.

## Server Version

Install PyGopherd v3.0+ from [michael-lazar/pygopherd](https://github.com/michael-lazar/pygopherd)
or another dependable source.

## Cached Files

PyGopherd will create cache files that start with ``.cache.pygopherd.*`` in
your gopher root directory. These files are used to index directories and zip
files for faster loading. Before launching the new server, clear out any
existing PyGopherd cache files from your system.

```
find /var/gopher -type f -name '.cache.pygopherd.*' -delete
```

## /etc/pygopherd/pygopherd.conf

Because the PyGopherd config file format uses evaluated python code, you will
need to make sure your config file is python 3 compatible.
There is one known spot where the default config file needed to be updated.

```
encoding = mimetypes.encodings_map.items() + \
         {'.bz2' : 'bzip2',
           '.tal': 'tal.TALFileHandler'
          }.items()
```

must be changed to

```
encoding = list(mimetypes.encodings_map.items()) + \
          list({'.bz2' : 'bzip2',
           '.tal': 'tal.TALFileHandler'
          }.items())
```



## PYG files

PyGopherd supports ``*.pyg`` files which use a special file handler to execute
python code directly. If you have written any custom PYG files for your server,
you will need to make sure that they are compatible with python 3.

The internal API has not changed, but some methods now expect bytes instead of
strings. An example PYG file is shown [here](testdata/testfile.pyg).

#### Before

```
def write(self, wfile):
    wfile.write(self.definition)
```

#### After

```
def write(self, wfile):
    wfile.write(self.definition.encode())
```

## Other Handlers

Some handler classes required major refactoring to support python 3. Notably
the ``mbox`` and ``ZIP`` handlers were significantly changed. Effort was made
to preserve the old behavior as closely as possible.

If you're using any of these handlers on your server, test them out and report
back with any issues!
