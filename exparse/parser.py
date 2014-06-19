__author__ = 'Gary Wu'

import logging
mylogger = logging.getLogger(__name__)

import io
import inspect
from decimal import Decimal
from urlparse import urljoin
from itertools import chain

import dateutil.parser

from lxml import etree
from lxml import html as html_parser

from helper import debug_lines

class XMLSyntaxError(BaseException):
    def __init__(self, etree_error):
        self.etree_error = etree_error

_xslt='''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" indent="no"/>
    
    <xsl:template match="/|comment()|processing-instruction()">
        <xsl:copy>
          <xsl:apply-templates/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="*">
        <xsl:element name="{local-name()}">
          <xsl:apply-templates select="@*|node()"/>
        </xsl:element>
    </xsl:template>
    
    <xsl:template match="@*">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>
    </xsl:stylesheet>
    '''
    
def parse_no_namespace(xml): 
    xslt_doc = etree.parse(io.BytesIO(_xslt))  
    transform = etree.XSLT(xslt_doc)

    return transform(etree.fromstring(xml))

_get_text = lambda elm: (elm.text.strip() if elm.text else '') if hasattr(elm, 'text') else elm.strip()
        
_strip = lambda text: text.strip() if text else text

def or_(*args):
    return {'__or__':args}

def or_impl(root, converters=None, base_url = None, **args):
    values = []
    for item in args:
        value = parse_element(root, xpath = item, converters = converters, base_url = base_url)
        if value:
            return value

def _get_value(elm = None, text = None, attr_types = ['u'], converters = None, base_url = None):
    for attr_type in attr_types:
        mapping = {u'i':int,
                   u'f':float,
                   u'd':Decimal,
                   u's':str,
                   u'u':unicode,
                   u'int':int,
                   u'float':float,
                   u'datetime':dateutil.parser.parse,
                   u'decimal':Decimal,
                   u'string':str,
                   u'unicode':unicode}
        if converters and converters.get(attr_type):
            return converters.get(attr_type)(_get_text(elm) if elm is not None else text)
        elif attr_type in mapping:
            return mapping[attr_type](_get_text(elm) if elm is not None else text)
        elif attr_type == u'e':
            return elm
        elif attr_type == u't' and elm is not None and elm.tail:
            return elm.tail.strip()
        elif attr_type == u'url' and elm is not None:
            return urljoin(base_url, elm)
        elif attr_type == u'a' and elm is not None:
            parts = ([elm.text] + list(chain(*([_strip(c.text), _strip(c.tail)] for c in elm.getchildren()))) + [_strip(elm.tail)])
            # filter removes possible Nones in texts and tails
            return filter(None, parts)

def parse_dict(root, name, xpath, converters = None, base_url = None, array = False):
    value = None

    if len(xpath) > 1:
        return parse_element(root, xpath, converters = converters, base_url = base_url)
    else:
        xpath, obj = xpath.items()[0]
        if not isinstance(xpath, basestring):
            obj, xpath = xpath, obj
        try:
            elms = root.xpath(xpath)
        except etree.XPathEvalError:
            raise etree.XPathEvalError('Invalid expression: %s' % xpath)
        if not elms:
            mylogger.info('xpath: %s not found while looking for: %s' % (xpath, name))
        else:
            debug_lines(etree.tostring(root, pretty_print = True))
            value = []

            if callable(obj):
                spec = inspect.getargspec(obj)
                param = {}

                if 'converters' in spec.args:
                    param['converters'] = converters
                if 'base_url' in spec.args:
                    param['base_url'] = base_url

            for elm in elms:
                if callable(obj):
                    value.append(obj(elm, **param))
                else:
                    value.append(parse_element(elm, obj, converters = converters, base_url = base_url))

            if array == False and len(value) == 1:
                value = value[0]

        if value is not None:
            mylogger.info('xpath: %s not found while looking for: %s' % (xpath, name))

        return value if value is not None else ''

def parse_string(root, xpath, attr_type='u', converters = None, base_url = None, array = False):
    debug_lines(etree.tostring(root, pretty_print = True), 10)
    try:
        elms = root.xpath(xpath)
    except etree.XPathEvalError:
        raise etree.XPathEvalError('Invalid expression: %s' % xpath)
    if not elms:
        mylogger.debug('not found type:%s' % (attr_type))
    else:
        result = []
        for elm in elms:
            data = _get_value(elm,
                              attr_types = attr_type,
                              converters = converters,
                              base_url = base_url)
            mylogger.debug('Found value:%s' % (result))
            if not array:
                return data if data else ''
            else:
                result.append(data)
        return result

def parse_element(root, xpaths, converters=None, base_url = None):
    result = {}
    for key in xpaths:
        attr_types = []
        parts = key.split(':')
        if len(parts) > 1:
            name = parts[0]
            attr_types.extend(parts[1:])
        else:
            name = key
        if len(attr_types) == 1 and 'omit' in attr_types or 'o' in attr_types:
            attr_types.append('u')
        if len(attr_types) == 0:
            attr_types = ['u']

        xpath = xpaths[key]
        #mylogger.info('name: %s, xpaths: %s, xpath: %s' % (name, ('%s' % xpaths)[:50], ('%s' % xpath)[:50]))
        if isinstance(xpath, dict):
            data = parse_dict(root, name, xpath, converters, base_url)
        elif isinstance(xpath, list):
            assert len(xpath) == 1 and 'Only single item array is supported. Array means result is array not input'
            xpath = xpath[0]
            if isinstance(xpath, dict):
                data = parse_dict(root, name, xpath, converters, base_url, array = True)
            else:
                data = parse_string(root, xpath, attr_types, converters, base_url, array = True)
        else:
            data = parse_string(root, xpath, attr_types, converters, base_url)

        if 'omit' in attr_types or 'o' in attr_types:
            if len(xpaths) > 1:
                assert 0 and 'additional data omitted %s' % key
            return data
        else:
            result[name] = data if data else ''
            mylogger.info(('return name: %s, result: %s' % (name, ('%s' % result)[:100])))
    return result

def xml_to_tuple(xml, xpaths, converters = None, strip_namespace = True):
    if not xml:
        return 
    try:
        root = None
        if strip_namespace:
            root = parse_no_namespace(xml)
        else:
            root = etree.fromstring(xml)
        mylogger.debug(etree.tostring(root, pretty_print=True))
        return parse_element(root, xpaths, converters)
    except etree.XMLSyntaxError as e:
        raise(XMLSyntaxError(e))
    '''
    except:
        import sys
        info = sys.exc_info()
        mylogger.debug("Unexpected error: %s", info)
        raise
    '''

def parse(xpaths, html = None, xml = None, converters = None, base_url = None, strip_namespace = True):
    '''
    Parse either html or xml to a object defined by the xpaths. Resulting object could be a string, list, dict.
    :param xpaths: dict of xpaths. each data is extracted from html or xml based on each xpath.
    :param html: if present parse as html.
    :param xml: if present parse as xml
    :param converters: any data type converters used during parser
    :param base_url: base_url to convert relative url found to abusolute url
    :param strip_namespace: for xml strips namespace before parse
    :return: object that contains found data pointed to by xpaths
    '''
    if not html:
        return
    if xml:
        if strip_namespace:
            root = parse_no_namespace(xml)
        else:
            root = etree.fromstring(xml)
    else:
        root = html_parser.fromstring(html)
    #mylogger.debug(etree.tostring(root, pretty_print=True))
    return parse_element(root, xpaths, converters = converters, base_url = base_url)

