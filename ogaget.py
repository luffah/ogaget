#!/usr/bin/env python3
# encoding: utf-8
"""A tool to store credits related to a file found in OpenGameArt.org"""
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
from os.path import isfile, dirname, basename, splitext
from os import listdir
import tarfile
import argparse
import mimetypes
import lxml.html as mkxml
from lxml.html import HtmlElement as Element
from common.www import request_url, download
from common.credit_file import parse, write, _get_content

ALWAYS_GET = False

KEYS_HEADER = [
        'title', 'artist', 'date', 'license',
        'url', 'url artist', 'url file',
        'media ext', 'media file'
        ]
KEYS_FOOTER = [
        'comment'
        ]

KEYS_POSTPROC = {
    'url artist': lambda val: ['https://opengameart.org' + v for v in val]
}

FILES_XPATH =  './/span[@class="file"]/a/@href'
KEYS_XPATH = {
    'title': (
        './/div[contains(@class,"field-name-title")]'
        '/div[contains(@class,"field-items")]'
        '/div[contains(@class,"field-item")]'),
    'artist': (
        './/div[contains(@class,"field-name-author-submitter")]'
        '/div[contains(@class,"field-items")]'
        '/div[contains(@class,"field-item")]'
        '/span[@class="username"]'),
    'date': (
        './/div[contains(@class,"field-name-author-submitter")]'
        '/following-sibling::div[contains(@class,"field-name-post-date")]'
        '/div[contains(@class,"field-items")]'
        '/div[contains(@class,"field-item")]'),
    'license': (
        './/div[contains(@class,"field-name-field-art-licenses")]'
        '/div[contains(@class,"field-items")]'
        '/div[contains(@class,"field-item")]'),
    'url artist': (
        './/div[contains(@class,"field-name-author-submitter")]'
        '/div[contains(@class,"field-items")]'
        '/div[contains(@class,"field-item")]'
        '/span[@class="username"]/a/@href'),
}

def main(creditfile='', url='', html='', mediafile='', dl=False):
    """ Fetch missing datas / credit informations """
    file_to_dl = False
    download_requested = ALWAYS_GET or dl

    def _first(gen):
        if isinstance(gen, str):
            return gen
        if not gen:
            return None
        a_list = list(gen)
        return a_list[0] if a_list else None

    def choose(files):
        # TODO fzy like chooser
        if len(files) == 1:
            return files[0]
        else:
            print('\n'.join([
                "%d : %s" % (idx, n.replace('%20', ' '))
                for (idx, n) in enumerate(files)
            ]))
            idx = None
            while not isinstance(idx, int):
                try:
                    idx = int(input('i (0 =< i =< %s) ? ' % len(files)))
                except ValueError:
                    print('give number or hit Ctrl+c')
            return files[idx]

    def _update_refcredit():
        # refresh refcredit content, from url or html
        if html:
            html_content = '\n'.join(_get_content(html))
        elif url:
            refcredit['url'] = url
            response = request_url(url)
            if response:
                html_content = response.read()
            else:
                print('Failing to get info from url')
                return
        else:
            return

        def txtt(xpathresult):
            """ return a list of str from a xpath result """
            if xpathresult and isinstance(xpathresult[0], Element):
                return [e.text_content() for e in xpathresult]
            return xpathresult

        doc = mkxml.fromstring(html_content)
        if not refcredit.get('url file'):
            files = txtt(doc.xpath(FILES_XPATH))
            refcredit['url file'] = choose(files)
        for key in KEYS_XPATH:
            postproc = KEYS_POSTPROC.get(key, lambda a: a)
            refcredit[key] = postproc(txtt(doc.xpath(KEYS_XPATH[key])))

    name = (
        _first(splitext(basename(creditfile))) or
        _first(splitext(basename(mediafile)))  or
        _first(splitext(basename(html)))
    )
    # first get refcredit content
    creditfile = creditfile or (("%s.txt" % name) if name else '')
    (refcredit_orig, ordered_keys) = (
        parse(creditfile, return_ordered_keys=True)
        if creditfile else ({}, [])
    )
    refcredit = refcredit_orig.copy()
    url = url or _first(refcredit.get('url'))
    _update_refcredit()
    if isfile(mediafile) and not refcredit:
        print('Media file only (%s) is not enought to create a credit file' % mediafile)
        return
    file_to_dl = _first(refcredit.get('url file'))
    if not file_to_dl:
        print("Missing info 'url file' in %s" % creditfile)
        return

    # set dl file name according to its type
    dl_mimetype = mimetypes.guess_type(file_to_dl)[0]
    if dl_mimetype and (
            'audio' in dl_mimetype or
            'image' in dl_mimetype
            ):
        media_ext = (_first(refcredit.get('media ext')) or
                splitext(file_to_dl)[1])
        if not mediafile:
            mediafile = name + media_ext
        dl_file_name = mediafile
        print('media  : %s' % mediafile)
    else:
        dl_file_name = ('%s-%s' % (
            _first(refcredit['artist']), basename(file_to_dl))
            ).replace('%20',' ')
        print('archive: %s' % dl_file_name)

    if file_to_dl and download_requested and not isfile(dl_file_name):
        download(file_to_dl, dl_file_name)

    if not isfile(dl_file_name):
        print('No media or archive found : %s'
              % (dl_file_name))
        if download_requested:
            print('Download failed. Check url or internet connection.')
        else:
            print('Try -dl to download')
        return

    if dl_file_name == mediafile:
        pass
    elif tarfile.is_tarfile(dl_file_name):
        media_file_to_extract = _first(refcredit.get('media file', ''))
        tar = tarfile.open(dl_file_name)
        if not media_file_to_extract:
            media_exts = refcredit.get('media ext', [])
            media_file_to_extract = choose([
                tarinfo.name
                for tarinfo in tar.getmembers()
                if tarinfo.type == tarfile.REGTYPE and
                (not media_exts or splitext(tarinfo.name)[1] in media_exts)
            ])
        print('shall extract %s from %s' %
              (media_file_to_extract, dl_file_name))
        try:
            media_ext = splitext(media_file_to_extract)[1]
            if not mediafile:
                mediafile = name + media_ext
            print('> %s' % mediafile)
            tar._extract_member(tar.getmember(media_file_to_extract),
                                mediafile)
            refcredit['media file'] = media_file_to_extract
        except KeyError:
            print('No media found')
            exit()

    # something is wrong, explian what
    if not name:
        if url:
            print("It looks like there is no media related to this page.")
        return

    if refcredit_orig != refcredit:
        write(creditfile, refcredit, KEYS_HEADER + [
            k for k in ordered_keys if k not in (KEYS_HEADER + KEYS_FOOTER)
            ] + KEYS_FOOTER)

if __name__ == '__main__':
    args = argparse.Namespace(
            creditfile='', url='', html='', mediafile='', dl=False)
    def _use_argparse():
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('-c', action="store", dest="creditfile",
                default=args.creditfile,
                help="a file with 'key: comma-separated values'* as content")
        group = parser.add_mutually_exclusive_group()
        group.add_argument('-url', action="store", default=args.url,
                help="the url of page presenting the media")
        group.add_argument('-html', action="store", default=args.html,
                help="an alternative of the url (for testing)")
        parser.add_argument('-dl', action="store_true",
                help="download the media (choices are prompted if many are found)")
        parser.add_argument('-m', action="store", dest='mediafile',
                default=args.mediafile,
                help="the mediafile (used for naming credit file)")

        if not sys.argv[1:]:
            parser.print_help()
        return parser.parse_args()

    if not sys.argv[1:] or sys.argv[1].startswith('-'):
        args = _use_argparse()
    else:
        for i in sys.argv[1:]:
            if i == '-h':
                _use_argparse()
            if i in ['-dl']:
                args.dl = i
            elif not args.creditfile and isfile(i) and i.endswith('.txt'):
                args.creditfile = i
            elif not args.html and isfile(i) and i.endswith('.html'):
                args.html = i
            elif not args.url and '://' in i:
                args.url = i
            elif not args.mediafile:
                args.mediafile = i
    main(**vars(args))
