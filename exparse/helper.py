__author__ = 'Gary Wu'

import logging
mylogger = logging.getLogger(__name__)

from itertools import chain
from functools import partial

from lxml import etree
from lxml import html

def currency(elm):
    if elm is not None and elm.text:
        text = elm.text.strip()
        if text.startswith('$'):
            text = text[1:].strip()
            return int(float(text.replace(',', '')) * 100)
    return -1

def elm2dict(elm):
    return {
        'tag':elm.tag,
        'attrib':elm.attrib,
        'text':elm.text.strip() if elm.text else '',
        'tail':elm.tail.strip() if elm.tail else '',
        }

def dump_one(elm):
    data = elm2dict(elm)
    children = []
    for c in elm.getchildren():
        children.append(elm2dict(c))
    data['children'] = children
    return data

def dump(elm):
    all = []
    if isinstance(elm, list):
        for item in elm:
            all.append(dump_one(item))
        return all
    else:
        return dump_one(elm)

def dump_elm(elm, attr_types = ''):
    if isinstance(elm, html.HtmlElement):
        mylogger.debug('value: %s, type:%s' % (etree.tostring(elm, pretty_print = True), attr_types))
    elif hasattr(elm, 'text'):
        mylogger.debug('value: %s, type:%s' % (elm.text, attr_types))
    else:
        mylogger.debug('value: %s, type:%s' % (elm, attr_types))

def debug_lines(text, lines=10):
    if lines:
        mylogger.debug('\n\n' + '\n'.join(chain(text.splitlines()[:lines])) + '\n...\n')
    else:
        mylogger.debug('\n\n' + text)

def containing_class(class_name):
    return 'contains(concat(" ",normalize-space(@class), " "), " ' + class_name + ' ")'

def get_all_text(elm, sep = ' '):
    text = ''
    if elm.text:
        text = elm.text.strip()
    for c in elm.getchildren():
        text += get_all_text(c, sep)
    if elm.tail and elm.tail.strip():
        text += sep + elm.tail.strip() + sep
    return text

get_all_text_newline = partial(get_all_text, sep = '\n')
get_all_text_tab = partial(get_all_text, sep = '\t')

def stringify_children(elm):
    parts = ([elm.text.strip() if elm.text else ''] +
             list(
                 chain(*(
                     [c.text.strip() if c.text else '', stringify_children(c), c.tail.strip() if c.tail else '']
                     for c in elm.getchildren()
                    )
                 )
             ) + [elm.tail.strip() if elm.tail else '']
    )
    return ''.join(filter(None, parts))