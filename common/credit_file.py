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
INLINE_KEYS = [ 'license' ]

def _get_content(fname):
    ret = []
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


def parse(fpath, with_order=True, return_ordered_keys=False):
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
    tmpparsed = {}
    order = 0
    meta = False
    with_order = with_order or return_ordered_keys
    for line in _get_content(fpath):
        if line.startswith('#'):
            continue

        if key and not currval and line.startswith('   '):
            meta = True
            spl = line.split(':')
            tmpkey = spl[0].strip()
            tmpparsed[tmpkey] = (":".join(spl[1:])).strip()
            continue

        if meta:
            parsed[key] = (tmpparsed, order) if with_order else tmpparsed
            meta = False
            key = None
            tmpparsed = {}

        if line.startswith(' '):
            if key:
                currval += _to_list(line)
            continue

        if currval:
            parsed[key] = (currval, order) if with_order else currval
            (key, currval) = (None, [])

        if ':' in line:
            spl = line.split(':')
            key = spl[0].strip()
            order += 1
            if re.match("[^:]*:<.*", line):
                parsed[key] = (None, order) if with_order else None
                (key, currval) = (None, [])
            else:
                currval = _to_list(":".join(spl[1:]))
    if currval:
        parsed[key] = (currval, order) if with_order else currval
    if meta:
        parsed[key] = (tmpparsed, order) if with_order else tmpparsed

    if return_ordered_keys:
        return (
            {k: v[0] for k,v in parsed.items()},
            sorted(parsed.keys(), key=lambda k: parsed[k][1])
        )
    else:
        return parsed
