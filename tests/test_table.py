from __future__ import print_function
__author__ = 'Work'

import exparse

def test_table():
    with open('fixtures/orderlist.html', 'rb') as f:
        html = f.read().decode('utf-8')

    tables = exparse.Table.parse(html, value_xpath = './/span')
    assert len(tables) == 2