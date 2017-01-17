from bs4 import BeautifulSoup
import re
def cut_html(html, count):
    text = re.findall("<.*?>.*?</.*?>", html)



html_doc = """
<p class="title"><b>The Dormouse's story</b></p>
<p class="story">Once upon a time there were three little sisters; and their names were
<a href="http://example.com/elsie" class="sister" id="link1">Elsie</a>,
<a href="http://example.com/lacie" class="sister" id="link2">Lacie</a> and
<a href="http://example.com/tillie" class="sister" id="link3">Tillie</a>;
and they lived at the bottom of a well.</p>

<p class="story">...</p>
"""
if __name__ == '__main__':
    cut_html(html_doc, -1)