#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 luffah <contact@luffah.xyz>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import tarfile
import zipfile
import shutil


class Unarchiver(object):

    def __init__(self, fname):
        self.type = (
            tarfile.is_tarfile(fname) and 'tar' or
            zipfile.is_zipfile(fname) and 'zip' or
            ''
            )

        if not self.type:
            print('archive format is not supported')
            raise KeyError

        self.fname = fname
        self.archive = None
        self.open()

    def open(self):
        if self.type == 'tar':
            self.archive = tarfile.open(self.fname)
        elif self.type == 'zip':
            self.archive = zipfile.ZipFile(self.fname)

    def extract_file_as(self, name, target):
        ar = self.archive
        if self.type == 'tar':
            ar._extract_member(ar.getmember(name), target)
        elif self.type == 'zip':
            with ar.open(ar.getinfo(name)) as src, \
                    open(target, "wb") as tgt:
                        shutil.copyfileobj(src, tgt)

    def getfiles(self, test=lambda a:True):
        files = []
        if self.type == 'tar':
            files = [info.name for info in self.archive.getmembers()
                     if info.type == tarfile.REGTYPE
                     and test(info.name)]
        elif self.type == 'zip':
            files = [info.filename for info in self.archive.filelist
                     if info.filename[-1] != '/'
                     and test(info.filename)]

        return files
