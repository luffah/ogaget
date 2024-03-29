#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 luffah <contact@luffah.xyz>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""A tool to store credits related to a file found in OpenGameArt.org"""
import sys
import signal
from os.path import isfile, basename, splitext, isdir
from os import listdir, chdir
import argparse
import mimetypes
import lxml.html as mkxml
from lxml.html import HtmlElement as Element
from .selector import choose, first, get_fname
from .unarchiver import Unarchiver
from .www import request_url, download
from .credit_file import parse, write, _get_content

ALWAYS_GET = False

KEYS_HEADER = [
    'title', 'collection', 'sub collection', 'artist', 'date', 'license',
    'url', 'url artist', 'url file',
    'media ext', 'media file'
]
KEYS_FOOTER = [
    'comment'
]

KEYS_POSTPROC = {
    'url artist': lambda val: ['https://opengameart.org' + v for v in val]
}

FILES_XPATH = './/span[@class="file"]/a/@href'
KEYS_XPATH = {
    'title~': (
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


def main(creditfile='', url='', html='', mediafile='',
         directory='', dl=False, renew=False):
    """
    main . what else ?
    mmm. pylint dislike the fact of using command args as function argument

    Function : Fetch missing datas / credit informations
    """
    if directory:
        chdir(directory)
        for fname in listdir('.'):
            if isfile(fname) and fname.endswith('.txt'):
                main(creditfile=fname, dl=dl)
            elif isdir(fname):
                main(directory=fname, dl=dl)
        chdir('..')
        return
    print('*' * 34)

    file_to_dl = False
    download_requested = ALWAYS_GET or dl

    def _get_title(fname):
        return splitext(get_fname(first(fname)).replace('_', ' '))[0]

    def _update_title_for_collection(files, ctx):
        titles = set(splitext(f)[0] for f in files)
        if len(titles) > 1:
            if ctx == 'url':
                refcredit['collection~'] = refcredit['title~']
                refcredit['title~'] = _get_title(refcredit['url file'])
            elif ctx == 'archive':
                if 'collection~' in refcredit:
                    refcredit['sub collection'] = _get_title(
                        refcredit['url file'])
                else:
                    refcredit['collection~'] = refcredit['title~']

                refcredit['title~'] = _get_title(refcredit['media file'])

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
        files = txtt(doc.xpath(FILES_XPATH))
        if not refcredit.get('url file') or renew:
            refcredit['url file'] = choose(files, "'url file' for '%s'" % name,
                                           defaultinput=name)
        for key in KEYS_XPATH:
            postproc = KEYS_POSTPROC.get(key, lambda a: a)
            refcredit[key] = postproc(txtt(doc.xpath(KEYS_XPATH[key])))
        _update_title_for_collection(files, 'url')

    name = (
        first(splitext(basename(creditfile))) or
        first(splitext(basename(mediafile))) or
        first(splitext(basename(html)))
    )

    def keyboard_interrupt_handler(sig, frame):
        if sig or frame:
            pass
        print("ogaget has been interrupted while %s for '%s'" % (step, name))
        sys.exit(0)

    signal.signal(signal.SIGINT, keyboard_interrupt_handler)
    step = 'parsing datas'

    # first get refcredit content
    creditfile = creditfile or (("%s.txt" % name) if name else '')

    (refcredit_orig, ordered_keys) = (
        parse(creditfile, return_ordered_keys=True)
        if creditfile else ({}, [])
    )
    refcredit = refcredit_orig.copy()
    url = url or first(refcredit.get('url'))
    step = 'fetching datas from url'
    _update_refcredit()
    if isfile(mediafile) and not refcredit:
        print('Media file only (%s) is not enought to create a credit file' % mediafile)
        return
    file_to_dl = first(refcredit.get('url file'))
    if not file_to_dl:
        print("Missing info 'url file' in %s" % creditfile)
        return

    step = 'guessing mimetypes'
    # set dl file name according to its type
    dl_mimetype = mimetypes.guess_type(file_to_dl)[0]
    if dl_mimetype and (
            'audio' in dl_mimetype or
            'image' in dl_mimetype
    ):
        media_ext = (first(refcredit.get('media ext')) or
                     splitext(file_to_dl)[1])
        if not mediafile:
            mediafile = name + media_ext
        dl_file_name = mediafile
        print('media  : %s' % mediafile)
        step = 'downloading media file'
    else:
        dl_file_name = (
            '%s-%s' % (
                first(refcredit['artist']), basename(file_to_dl))
        ).replace('%20', ' ')
        print('archive: %s' % dl_file_name)
        step = 'downloading archive file'

    if file_to_dl and download_requested and (
            renew or not isfile(dl_file_name)):
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
    else:
        step = 'extracting file'
        media_file_to_extract = first(refcredit.get('media file', ''))
        media_exts = refcredit.get('media ext', [])

        def get_media_file_name():
            print('shall extract %s from %s' %
                  (media_file_to_extract, dl_file_name))
            media_ext = splitext(media_file_to_extract)[1]
            tgt = mediafile or (name + media_ext)
            print('> %s' % tgt)
            return tgt

        def test_extension(name):
            return not media_exts or splitext(name)[1] in media_exts

        try:
            unarchiver = Unarchiver(dl_file_name)
            files = unarchiver.getfiles(test_extension)
            if not media_file_to_extract or renew:
                media_file_to_extract = choose(files, "'media file' for '%s'" % name,
                                               defaultinput=name)
            unarchiver.extract_file_as(
                media_file_to_extract, get_media_file_name())
            refcredit['media file'] = media_file_to_extract
            _update_title_for_collection(files, 'archive')
        except KeyError:
            print('No media found')
            sys.exit(1)

    # something is wrong, explian what
    if not name:
        if url:
            print("It looks like there is no media related to this page.")
        return

    refcreditup = {}
    for k in refcredit.keys():
        if k.endswith('~'):
            refcreditup[k[:-1]] = refcredit[k]
    refcredit.update(refcreditup)

    step = 'writing changes'
    if refcredit_orig != refcredit:
        write(creditfile, refcredit, KEYS_HEADER + [
            k for k in ordered_keys if k not in (KEYS_HEADER + KEYS_FOOTER)
        ] + KEYS_FOOTER)


def parse_args():
    """
    parse arguments and options / define usage
    """
    if sys.argv[1:2] == ['keys']:
        print("\n".join(KEYS_HEADER + KEYS_FOOTER))
        sys.exit(0)

    if sys.argv[1:] and not sys.argv[1].startswith('-'):
        arg = sys.argv[1]
        sys.argv.insert(1, (
            arg.endswith('.txt') and '-c' or
            arg.endswith('.html') and '-html' or
            '://' in arg and sys.argv.insert(1, '-url') or
            isdir(arg) and '--recursive' or
            isfile(arg) and '-m' or
            '-h'))

    parser = argparse.ArgumentParser(prog='ogaget', description=__doc__)
    parser.add_argument('-c', action="store", dest="creditfile", default='',
                        help="a file with 'key: comma-separated values'* as content")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-url', action="store", default='',
                       help="the url of page presenting the media")
    group.add_argument('-html', action="store", default='',
                       help="an alternative of the url (for testing)")
    parser.add_argument('-dl', action="store_true",
                        help="download the media (choices are prompted if many are found)")
    parser.add_argument('-renew', action="store_true",
                        help="force a choice prompt (avoid stored infos)")
    parser.add_argument('--recursive', action="store", dest="directory",
                        help="act recursively")
    parser.add_argument('-m', action="store", dest='mediafile', default='',
                        help="the mediafile (used for naming credit file)")

    args = parser.parse_args()
    if not sys.argv[1:] or (args.directory and not isdir(args.directory)):
        parser.print_help()

    main(**vars(args))


if __name__ == '__main__':
    parse_args()
