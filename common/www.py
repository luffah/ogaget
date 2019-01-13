"""
    Implements functions to fetch files from web.
"""
from shutil import move
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


def download(url, fname):
    """ Download distant file (from url) to fname. (with a progress bar) """
    response = request_url(url)
    if not response:
        return
    block_sz = 8192
    bar_size = 40
    file_size = int(response.info().get("Content-Length"))
    fname_tmp = fname + '.part'
    with open(fname_tmp, 'wb') as fbuf:
        file_size_dl = 0
        buf = True
        while buf:
            buf = response.read(block_sz)
            file_size_dl += len(buf)
            fbuf.write(buf)
            status = "|%s| %10dk / %dk " % (
                ('-' * bar_size).replace(
                    '-', '#',
                    int(file_size_dl * bar_size / file_size)
                ), file_size_dl/1024, file_size/1024)
            status = status + chr(8)*(len(status)+1)
            print(status, end="\r")
    move(fname_tmp, fname)
    print(" " * 80, end="\r")
