#!/usr/bin/env python3
# encoding: utf-8
#
# Copyright (C) 2019 luffah <contact@luffah.xyz>
# Author: luffah <contact@luffah.xyz>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from os.path import isfile, dirname, basename
from os import listdir
import lxml.html as mkxml
from lxml.html import HtmlElement as Element
from common.www import request_url, download
from common.credit_file import parse, write, _get_content

ALWAYS_GET = False

USAGE = (
    "A tool to store credits related to a file found in OpenGameArt.org\n"
    "Usage:\n"
    " {0} [<credit_file>|<url>|<html_file>]\n"
    "Parameters:\n"
    " <credit_file> : a file with key: comma-separated values as content\n"
    " <url> : the url of page presenting the media\n"
    " <html_file> : an alternative of the url (mainly for testing)"
    "Options:\n"
    " -dl : download the media (choices are prompted if many are found)\n"
). format(sys.argv[0])


KEYS_WANTED = ['title', 'artist', 'url artist', 'url file', 'url', 'date',
               'license']

KEYS_POSTPROC = {
    'url artist': lambda val: ['https://opengameart.org' + v for v in val]
}

KEYS_XPATH = {
    'artist': (
        './/div[contains(@class,"field-name-author-submitter")]'
        '/div[contains(@class,"field-items")]'
        '/div[contains(@class,"field-item")]'
        '/span[@class="username"]'),
    'url artist': (
        './/div[contains(@class,"field-name-author-submitter")]'
        '/div[contains(@class,"field-items")]'
        '/div[contains(@class,"field-item")]'
        '/span[@class="username"]/a/@href'),
    'date': (
        './/div[contains(@class,"field-name-author-submitter")]'
        '/following-sibling::div[contains(@class,"field-name-post-date")]'
        '/div[contains(@class,"field-items")]'
        '/div[contains(@class,"field-item")]'),
    'title': (
        './/div[contains(@class,"field-name-title")]'
        '/div[contains(@class,"field-items")]'
        '/div[contains(@class,"field-item")]'),
    'license': (
        './/div[contains(@class,"field-name-field-art-licenses")]'
        '/div[contains(@class,"field-items")]'
        '/div[contains(@class,"field-item")]'),
    'files': './/span[@class="file"]/a/@href'
}


def txtt(xpathresult):
    """ return a list of str from a xpath result """
    if xpathresult and isinstance(xpathresult[0], Element):
        return [e.text_content() for e in xpathresult]
    return xpathresult


def main(creditfile, mediafile, html, url, opts):
    refcredit = {}
    key_others = {}
    html_content = []
    name = False
    files = []
    file_to_dl = False
    dl = ALWAYS_GET or '-dl' in opts
    curdir = dirname(creditfile or mediafile or html or '') or '.'

    # first get refcredit content
    if creditfile:
        refcredit = parse(creditfile, with_order=False)
        name = '.'.join(basename(creditfile).split('.')[:-1])
        if not url and refcredit.get('url'):
            url = refcredit.get('url')[0]
        if refcredit.get('url file'):
            file_to_dl = refcredit.get('url file')[0]

    # refresh refcredit content, from url or html
    if html:
        html_content = '\n'.join(_get_content(html))
        if not name:
            name = '.'.join(basename(html).split('.')[:-1])
    elif url:
        key_others['url'] = url
        response = request_url(url)
        if response:
            html_content = response.read()

    if html_content:
        doc = mkxml.fromstring(html_content)

        files = txtt(doc.xpath(KEYS_XPATH['files']))

        for p in KEYS_WANTED:
            fu = KEYS_POSTPROC.get(p, lambda a: a)
            if p in KEYS_XPATH:
                refcredit[p] = fu(txtt(doc.xpath(KEYS_XPATH[p])))
            elif p in key_others:
                refcredit[p] = fu(key_others[p])

    # ensure mediafile (the media) is defined if it can be
    if mediafile:
        name = '.'.join(basename(mediafile).split('.')[:-1])
    elif name:
        related = [f for f in listdir(curdir)
                   if f != basename(html or '') and
                   f != basename(creditfile or '') and
                   '.'.join(f.split('.')[:-1]) == name]
        mediafile = related[0] if related else False

    # if mediafile not found,
    # ask user if needed which file to download / credit
    if files and not mediafile:
        if len(files) == 1:
            file_to_dl = files[0]
        else:
            idx = None
            print('\n'.join([
                "%d : %s" % (i, n.replace('%20', ' '))
                for (i, n) in enumerate(files)
            ]))
            while not isinstance(idx, int):
                try:
                    idx = int(input('i (0 =< i =< %s) ? ' % len(files)))
                except ValueError:
                    print('give number or hit Ctrl+c')
            file_to_dl = files[idx]

    if file_to_dl:
        if 'url file' in KEYS_WANTED:
            refcredit['url file'] = file_to_dl
        if not name:
            name = ".".join(
                basename(file_to_dl).replace('%20', '_').split('.')[:-1])
        if not mediafile:
            mediafile = "%s.%s" % (name, file_to_dl.split('.')[-1])

    # we can now try a download with known informations
    if dl:
        if isfile(mediafile):
            print("%s already exists" % (mediafile))
        elif file_to_dl:
            print("%s -> %s" % (file_to_dl, mediafile))
            download(file_to_dl, mediafile)
        else:
            print('No media found')

    # something is wrong, explian what
    if not name:
        if url:
            print("It looks like there is no media related to this page.")
        return

    # write to the corresponding creditfile
    write("%s.txt" % name, refcredit, KEYS_WANTED)

if __name__ == '__main__':
    opts = {}
    (creditfile, url, html, mediafile) = (False,) * 4
    for i in sys.argv[1:]:
        if i in ['-dl', '-h']:
            opts[i] = i
        elif not creditfile and isfile(i) and i.endswith('.txt'):
            creditfile = i
        elif not html and isfile(i) and i.endswith('.html'):
            html = i
        elif not url and '://' in i:
            url = i
        elif not mediafile:
            mediafile = i

    if '-h' in opts or len(sys.argv) < 2:
        print(USAGE)
        exit(1)

    main(creditfile, mediafile, html, url, opts)
