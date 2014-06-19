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

def get_all_text(elm, sep = ' '):
    text = ''
    if elm.text:
        text = elm.text.strip()
    for c in elm.getchildren():
        text += get_all_text(c, sep)
    if elm.tail:
        text += sep + elm.tail.strip() + sep
    return text

img = {'src':'.//@src', 'alt':'.//@alt', 'title':'.//@title'}
a = {'href':'.//@href', 'target':'.//@target', 'text':'text()'}
ul = {'data:o':[{'.//li':lambda x: get_all_text(x).strip()}]}

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
        value = path_to_tuple(root, xpath = item, converters = converters, base_url = base_url)
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

def path_to_tuple(root, xpaths, converters=None, base_url = None):
    result = {}

    for name in xpaths:
        xpath = xpaths[name]
        mylogger.info('name: %s, xpaths: %s, xpath: %s' % (name, ('%s' % xpaths)[:50], ('%s' % xpath)[:50]))

        attr_types = ['u']
        parts = name.split(u':')
        if len(parts) > 1:
            name = parts[0]
            attr_types = parts[1:]

        if isinstance(xpath, dict):
            if len(xpath) == 1:
                xpath, obj = xpath.items()[0]
                if not isinstance(xpath, basestring):
                    obj, xpath = xpath, obj
                try:
                    elm = root.xpath(xpath)
                except etree.XPathEvalError:
                    raise etree.XPathEvalError('Invalid expression: %s' % xpath)
                if not elm:
                    mylogger.info('xpath: %s not found while looking for: %s' % (xpath, name))
                else:
                    debug_lines(etree.tostring(root, pretty_print = True))
                    value = None

                    if callable(obj):
                        if isinstance(elm, list) and len(elm) == 1:
                            elm = elm[0]
                        if elm is not None:
                            spec = inspect.getargspec(obj)
                            param = {}

                            if 'converters' in spec.args:
                                param['converters'] = converters
                            if 'base_url' in spec.args:
                                param['base_url'] = base_url

                            value = obj(elm, **param)

                            '''
                            if attr_types:
                                value = _get_value(text = value,
                                        attr_types = attr_types,
                                        converters = converters)
                            '''
                    else:
                        mylogger.debug(elm)
                        value = path_to_tuple(elm[0], obj, converters = converters, base_url = base_url)
                        
                    if value is not None:
                        if 'omit' in attr_types or 'o' in attr_types:
                            if isinstance(value, dict):
                                result.update(value)
                            else:
                                raise ValueError
                        else:
                            result[name] = value
                    else:
                        mylogger.info('xpath: %s not found while looking for: %s' % (xpath, name))
            else:
                value = path_to_tuple(root, xpath, converters = converters, base_url = base_url)
                if value:
                    result[name] = value
                else:
                    raise ValueError
                        
        elif isinstance(xpath, list):
            xpath = xpath[0]
            if isinstance(xpath, dict):
                value = []
                xpath, obj = xpath.items()[0]
                debug_lines(etree.tostring(root, pretty_print = True))
                debug_lines(xpath)
                try:
                    elements = root.xpath(xpath)
                except etree.XPathEvalError:
                    raise etree.XPathEvalError('Invalid expression: %s' % xpath)
                for elm in elements:
                    mylogger.debug(elm)

                    if callable(obj):
                        if elm is not None:
                            spec = inspect.getargspec(obj)
                            param = {}

                            if 'converters' in spec.args:
                                param['converters'] = converters
                            if 'base_url' in spec.args:
                                param['base_url'] = base_url

                            data = obj(elm, **param)
                    else:
                        data = path_to_tuple(elm, obj, converters = converters, base_url = base_url)

                    if data:
                        value.append(data)
                    else:
                        mylogger.debug('xpath: %s not found', elm)
                if value:
                    if 'merge' in attr_types or 'm' in attr_types:
                        data = {}
                        for item in value:
                            data.update(item)

                        if 'omit' in attr_types or 'o' in attr_types:
                            result.update({k:v for k, v in data.iteritems()})
                        else:
                            result[name] = data
                    else:
                        result[name] = value
                    mylogger.debug('%s = %s' % (xpath, value))
                else:
                    mylogger.debug('xpath: %s not found', xpath)
            else:
                mylogger.debug('xpath: %s', xpath)
                mylogger.debug(etree.tostring(root, pretty_print = True))
                try:
                    elms = root.xpath(xpath)
                except etree.XPathEvalError:
                    raise etree.XPathEvalError('Invalid expression: %s' % xpath)
                if elms:
                    result[name] = [elm.text for elm in elms]
                    mylogger.debug(('%s = %s' % (xpath, result[name]))[:100])
                else:
                    mylogger.debug('xpath: %s not found', xpath)
        else:
            debug_lines(etree.tostring(root, pretty_print = True), 10)
            try:
                elm = root.xpath(xpath)
            except etree.XPathEvalError:
                raise etree.XPathEvalError('Invalid expression: %s' % xpath)
            if elm:
                result[name] = _get_value(elm = elm[0], 
                        attr_types = attr_types,
                        converters = converters,
                        base_url = base_url)
                mylogger.debug('Found name:%s, value:%s' % (name, result[name]))
            else:
                mylogger.debug('not found name:%s, type:%s' % (name, attr_types))

    if result:
        if 'omit' in attr_types or 'o' in attr_types:
            if len(result.keys()) == 1:
                result = result[name]
        '''
            else:
                if isinstance(result[name], list):
                    for item in result[name]:
                        result.update(item)
                else:
                    result.update(result[name])
                del result[name]
        '''
        mylogger.info(('return name: %s, result: %s' % (name, ('%s' % result)[:100])))
        return result
    else:
        mylogger.info('%s(%s) has no result' % (name, xpath))
                
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
        return path_to_tuple(root, xpaths, converters)
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
    return path_to_tuple(root, xpaths, converters = converters, base_url = base_url)

