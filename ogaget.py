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
        for key in KEYS_WANTED:
            postproc = KEYS_POSTPROC.get(key, lambda a: a)
            if key in KEYS_XPATH:
                refcredit[key] = postproc(txtt(doc.xpath(KEYS_XPATH[key])))
        if not refcredit.get('url file'):
            files = txtt(doc.xpath(KEYS_XPATH['files']))
            if len(files) == 1:
                refcredit['url file'] = files[0]
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
                        exit()
                refcredit['url file'] = files[idx]

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
    media_file_to_extract = _first(refcredit.get('media file', ''))
    file_to_dl = _first(refcredit.get('url file'))
    if not file_to_dl:
        print("Missing info 'url file' in %s" % creditfile)
        return
    media_ext = (_first(refcredit.get('media ext')) or
                 splitext(media_file_to_extract or file_to_dl)[1])
    # ensure mediafile (the media) is defined if it can be
    if not mediafile:
        mediafile = name + media_ext
    dl_mimetype = mimetypes.guess_type(file_to_dl)[0]
    if dl_mimetype and (
            'audio' in dl_mimetype or
            'image' in dl_mimetype
            ):
        dl_file_name = mediafile
        print('media  : %s' % mediafile)
    else:
        dl_file_name = ('%s-%s' % (
            _first(refcredit['artist']), basename(file_to_dl))
            ).replace('%20',' ')
        # FIXME : if mediafile not found,
        # shall ask user if needed which file to download / credit
        print('archive: %s' % dl_file_name)
        print('media  ? %s' % mediafile)

    if isfile(mediafile):
        print("%s already exists" % (mediafile))
    # we can now try a download with known informations
    else:
        if file_to_dl and download_requested and not isfile(dl_file_name):
            # print(file_to_dl)
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
            if not media_file_to_extract:
                # FIXME : a choice list
                print("'media file' key shall be defined to extract the file")
                return
            print('shall extract %s from %s' %
                  (media_file_to_extract, dl_file_name))
            tar = tarfile.open(dl_file_name)
            try:
                tar._extract_member(tar.getmember(media_file_to_extract),
                                    mediafile)
            except KeyError:
                print('No media found')
                exit()

    # something is wrong, explian what
    if not name:
        if url:
            print("It looks like there is no media related to this page.")
        return

    # write to the corresponding creditfile (and try not to change order)
    if refcredit_orig != refcredit:
        write(creditfile, refcredit, ordered_keys + [
            k for k in KEYS_WANTED if k not in ordered_keys
        ])

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
