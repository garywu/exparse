__author__ = 'Work'

from helper import get_all_text, get_all_text_newline, get_all_text_tab
from parser import parse, parse_element, parse_string

img = {'src':'.//@src', 'alt':'.//@alt', 'title':'.//@title'}
a = {'href':'.//@href', 'target':'.//@target', 'text':'text()'}
ul = {'data:o':[{'.//li':lambda x: get_all_text(x).strip()}]}

input = {
    'data:o':{'.':lambda x: x}
}
form = {
    'data:o':[{'.//input':input}]
}

tr_xpath = {
    'td:o':[{'.//td':lambda x: x}]
}

table_xpath = {
    'tr:o':[{'.//tr':lambda x: x}]
}

tables_xpath = {
    'table:o':[{'.//table':lambda x: x}]
}

class Td(object):
    def __init__(self, element, value_xpath):
        self.attrib = element.attrib
        self.text = element.text
        self.id = element.attrib.get('id')
        self.tail = element.tail
        self.all_text = get_all_text_newline(element)
        if value_xpath:
            self.value = parse_string(element, value_xpath)

class Tr(object):
    def __init__(self, element, columns):
        self.attrib = element.attrib
        self.text = element.text
        self.tail = element.tail
        self.all_text = get_all_text_tab(element)
        self.id = element.attrib.get('id')
        self.td = columns

    @classmethod
    def from_element(cls, elm, value_xpath = None):
        elms = parse_element(elm, tr_xpath)
        tds = []
        for td in elms:
            tds.append(Td(td, value_xpath))
        return cls(elm, tds)

class Table(object):
    def __init__(self, element, rows):

        self.attrib = element.attrib
        self.text = element.text
        self.tail = element.tail
        self.id = element.attrib.get('id')
        self.tr = rows

    @classmethod
    def from_element(cls, elm, value_xpath = None):
        elms = parse_element(elm, table_xpath)
        trs = []
        for tr in elms:
            trs.append(Tr.from_element(tr, value_xpath))
        return cls(elm, trs)

    @staticmethod
    def parse(html, value_xpath = None):
        tables = []
        elms = parse(tables_xpath, html)
        for elm in elms:
            tables.append(Table.from_element(elm, value_xpath))

        return tables