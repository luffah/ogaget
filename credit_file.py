# -*- coding: utf-8 -*-
# Copyright (C) 2019 luffah <contact@luffah.xyz>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""
    define (parse and write) the format of a credit file
    ```
    # HEY I'M A CREDIT FILE (this line is ignored)

    a key: a value

    an other key: value1; value2; value3

    # values can be written on multiple lines
    # beginning with a space
    alterate key:
     value1; value2
     value3
    ```
"""
import re
import os
from os.path import isfile
INLINE_KEYS = ['license']


def _get_content(fname):
    ret = []
    if isfile(fname):
        with open(fname, "r") as buf:
            ret = buf.readlines()
    return ret


def _write(fname, lines):
    with open(fname, "w") as buf:
        buf.writelines(lines)


def write(fname, infos, order):
    """
    Write lines from a dictionnary 'infos' in the file 'fname'.
    Datas are ordered according to 'order'.
    """
    ret = []
    for k in order:
        if k in infos:
            if isinstance(infos[k], str):
                ret.append("%s: %s\n" % (k, infos[k]))
            elif len(infos[k]) == 1:
                ret.append("%s: %s\n" % (
                    k, infos[k][0]))
            elif k in INLINE_KEYS:
                ret.append("%s: %s\n" % (
                    k, ','.join(infos[k])))
            else:
                ret.append("%s:\n %s\n" % (
                    k, '\n '.join(infos[k])))
    print("> %s" % fname)
    _write(fname, ret)


def parse(fpath, with_order=False, return_ordered_keys=False):
    """
    Parse a credit file.
    return a dictionnary ({key:[list(values), order of appearance]}
    if with_order is True
    else a dictionnary key:values
    """
    def _to_list(line):
        return [  # remove empty strings in values separated by ;
            s.strip()
            for s in line.strip().split(';')
            if s.strip()
        ]

    (key, currval) = (None, [])
    parsed = {}
    curparsed = parsed  # just a pointer
    curindent = 0
    parent_keys = []
    tabwitdth = 4
    order = 0
    with_order = with_order or return_ordered_keys
    order_maxdepth = 1
    ordering = False

    def _consume():
        nonlocal key
        nonlocal currval
        curparsed[key] = (currval, order) if ordering else currval
        (key, currval) = (None, [])

    def _add_subset():
        nonlocal curindent
        nonlocal curparsed
        if key not in curparsed:
            curparsed[key] = ({}, order) if ordering else {}
        curparsed = curparsed[key][0] if ordering else curparsed[key]
        curindent += 1
        parent_keys.append(key)

    def _leave_subset(indent):
        nonlocal curindent
        nonlocal curparsed
        while indent < curindent:
            parent_keys.pop()
            curindent -= 1
        curparsed = parsed
        for k in parent_keys:
            curparsed = curparsed[k]
            if ordering:
                curparsed = curparsed[0]

    for line in _get_content(fpath):
        if line.startswith('#'):  # drop comments
            continue

        spaces = (len(line) - len(line.lstrip()))
        indent_rest = spaces % 4
        indent = int(spaces / tabwitdth)

        ordering = with_order and len(parent_keys) < order_maxdepth

        if indent_rest:
            if key:  # multiline string props
                currval += _to_list(line)
            continue

        if currval:
            _consume()

        if indent < curindent:
            _leave_subset(indent)

        if key and indent == curindent + 1:
            _add_subset()

        if ':' in line:  # define key
            spl = line.split(':')
            key = spl[0].strip()
            order += 1
            if re.match("[^:]*:<.*", line):
                (key, currval) = (None, [])
            else:
                currval = _to_list(":".join(spl[1:]))
    if currval:
        _consume()

    if os.environ.get('DEBUG', False):
        from pprint import pprint
        print('------------')
        pprint(parsed)
        print('------------')
    if return_ordered_keys:
        return (
            {k: v[0] for k, v in parsed.items()},
            sorted(parsed.keys(), key=lambda k: parsed[k][1])
        )
    else:
        return parsed
