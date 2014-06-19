__author__ = 'Gary Wu'

from decimal import Decimal

import pytest

import exparse

@pytest.fixture
def html():
    return """
        <html>
            <tag1 class="plain" attr="abc" >
                tag1 text
                <tag2 attr="cbs" id="id2">
                    tag2 text
                    <br>
                    tag2 tail text
                </tag2>
                <tag3  class="good" >
                    this is tag3
                </tag3>
                <ul class="liststyle" >
                    <li>item 1</li>
                    <li>item 2</li>
                    <li>item 3</li>
                    <li>item 4</li>
                    <li>item 5</li>
                    <li>item 6</li>
                </ul>
            </tag1>
        </html>
        """

def test_id(html):
    path = {'data':'.//tag2[@id="id2"]'}

    result = exparse.parse(path, html)
    assert result == {'data': u'tag2 text'}

def test_tag(html):
    path = {'data':'.//tag2'}

    result = exparse.parse(path, html)
    assert result == {'data': u'tag2 text'}

def test_class(html):
    path = {'data':'.//tag1[@class="plain"]'}

    result = exparse.parse(path, html)
    assert result == {'data': 'tag1 text'}

def test_array(html):
    path = {'data':['.//ul[@class="liststyle"]/li']}

    result = exparse.parse(path, html)
    assert result == {'data': ['item 1', 'item 2', 'item 3', 'item 4', 'item 5', 'item 6']}

def test_simple_html():
    html = '''
        <html>
            <div id = "top">
                top
                <a href='abc1'>abc1</a>
                <a href='abc2'>abc2</a>
                <a href='abc3'>abc3</a>
                <a href='abc4'>abc4</a>
                <a href='abc5'>abc5</a>
                <a href='abc6'>abc6</a>
                <a href='abc7'>abc7</a>
                <a href='abc8'>abc8</a>
                <div class = "top_group">
                    <img src="img_1">img_1</img>
                    <h1>Title Title</h1>
                    <p>message message</p>
                </div>
            </div>
            <div id = "middle">
                middle
            </div>
            <div id = "bottom">
                bottom
            </div>
            <a href='another_link' id="another_link"></a>
            <p>text_value</p>
        </html>
    '''

    top_group_xpath = {'img':{'.//img':exparse.img}, 'title':'.//h1', 'message':'.//p'}

    html_xpath = {'top':'.//div[@id="top"]',
                  'middle':'.//div[@id="middle"]',
                  'top_group':{'.//div[@class="top_group"]': top_group_xpath},
                  'next':{'link':'.//a[@id="another_link"]/@href', 'text':'.//p'},
                  #'next_link':{'link':'.//a[@id="another_link"]/@href'},
                  'links':[{'.//div[@id="top"]/a':exparse.a}]}
    '''
    'name':'.//path',
    'name':abc,
    'name':{'.//path':abc}
    'name':{'name_1':'.//path', 'name_2':'.//path'}
    'name':['.//path'],
    'name':[{'.//path':abc}]
    '''
    data = exparse.parse(html_xpath, html)
    assert data['top_group'] == {'message': u'message message', 'img': {'src': u'img_1', 'alt':'', 'title':''}, 'title': u'Title Title'}
    assert data['next'] == {'link':'another_link', 'text':'message message'}

def test_simple_xml():
    xml='''
        <tag1>
            value1
            <tag2>
                value2
                <tag3>
                    value3
                </tag3>
            </tag2>
        </tag1>
      '''

    xml_xpath = {'tag1':'/tag1',
                 'tag2':'.//tag2',
                 'tag3':'.//tag3',
                 }

    items = exparse.parse(xml_xpath, xml)
    #assert items['tag1'] == 'value1'
    assert items['tag2'] == 'value2'
    assert items['tag3'] == 'value3'

def test_type_decorator():
    html ='''
        <tag1>
            value1
            <tag2>
                4.11
                <tag3>
                   3.44
                </tag3>
            </tag2>
        </tag1>
      '''

    path = {'tag1':'/tag1',
                 'tag2:d':'.//tag2',
                 'tag3:f':'.//tag3',
                 }

    items = exparse.parse(path, html)
    #assert items['tag1'] == 'value1'
    assert items['tag2'] == Decimal('4.11')
    assert items['tag3'] == 3.44
    assert isinstance(items['tag2'], Decimal)
    assert isinstance(items['tag3'], float)

def test_custom_function():
    html ='''
        <tag1>
            value1
            <tag2>
                4.11
                <tag3>
                   $3.44
                </tag3>
            </tag2>
        </tag1>
      '''

    path = {'tag1':'/tag1',
             'tag2':{'.//tag2':lambda x: int(Decimal(x.text.strip()) * 100)},
             'tag3':{'.//tag3':lambda x: Decimal(x.text.strip()[1:])},
             }

    items =  exparse.parse(path, html)
    #assert items['tag1'] == 'value1'
    assert items['tag2'] == 411
    assert items['tag3'] == Decimal('3.44')
    assert isinstance(items['tag3'], Decimal)

def test_custom_function_with_type_decorator():
    html ='''
        <tag1>
            value1
            <tag2>
                4.11
                <tag3>
                   $3.14
                </tag3>
            </tag2>
        </tag1>
      '''

    path = {'tag1':'/tag1',
                 'tag2:d':{'.//tag2':lambda x: int(Decimal(x.text.strip()) * 100)},
                 'tag3:i':{'.//tag3':lambda x: Decimal(x.text.strip()[1:])},
                 }

    items = exparse.parse(path, html)
    #assert items['tag1'] == 'value1'
    assert items['tag2'] == 411
    assert items['tag3'] == Decimal('3.14')

@pytest.mark.bad
def test_omit_single():
    html='''
        <tag1>
            value1
            <tag2>
                <tag3>4.10</tag3>
           </tag2>
            <tag2>
                <tag3>4.11</tag3>
            </tag2>
        </tag1>
      '''

    tag3_path = { 'tag3:d':{'.//tag3':lambda x: int(Decimal(x.text.strip()) * 100)}}
    path = {'tag2:o':[{'.//tag2':tag3_path}]}

    items = exparse.parse(path, html)
    assert items[0]['tag3'] == Decimal('410')
    assert items[1]['tag3'] == Decimal('411')

def test_contain_class():
    html = '''
            <html>
            <body>
                <div>
                    <ul class="unstyled shelfItems shelfActive list">
                        <li>abc</li>
                        <li>cbs</li>
                    </ul>
                </div>
            </body>
            </html>
        '''
    product_grid_xpath = {'data:o':['//ul[' + exparse.containing_class('shelfItems') + ']/li']}
    #xpath = {'li:o':['//ul[' + containing_class('shelfItems') + ']/li']}
    li = exparse.parse(product_grid_xpath, html)
    assert li == ['abc', 'cbs']
