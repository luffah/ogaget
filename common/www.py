"""
Implements functions to fetch files from web
"""
import  sys
from shutil import move, get_terminal_size
import urllib.request as urllib
from urllib.error import URLError


def request_url(url):
    """ Return HTTP response for url. """
    ret = None
    try:
        req = urllib.Request(
            url, headers={'User-Agent': "Magic Browser"})
        ret = urllib.urlopen(req)
    except URLError as err:
        print(err.reason)
    return ret

def _filesize(num):
    for unit in ['', 'k', 'M', 'G']:
        if abs(num) < 1024.0:
            return "%3.1f%s" % (num, unit)
        num /= 1024.0
    return "Too big"

class ProgBar():
    def __init__(self, size):
        self.max = size
        self.size = _filesize(size)
        self.txtinfo = "{1:<8} / {2:<8} {0}"
        self.barsize = (get_terminal_size((80, 20)).columns - 
                len(self.txtinfo.format('-',0,0)))

    def up(self, size):
        status = self.txtinfo.format(
                ('░' * self.barsize).replace(
                    '░', '█', int(size * self.barsize / self.max)
                    ), _filesize(size), self.size)
        sys.stdout.write(status)
        sys.stdout.flush()
        sys.stdout.write("\r")

def download(url, fname):
    """ Download distant file (from url) to fname. (with a progress bar) """
    response = request_url(url)
    if not response:
        return
    block_sz = 8192
    file_size = int(response.info().get("Content-Length"))
    fname_tmp = fname + '.part'
    progress = ProgBar(file_size)

    with open(fname_tmp, 'wb') as fbuf:
        file_size_dl = 0
        buf = True
        while buf:
            buf = response.read(block_sz)
            file_size_dl += len(buf)
            fbuf.write(buf)
            progress.up(file_size_dl)
    move(fname_tmp, fname)
    print(" " * 80)
