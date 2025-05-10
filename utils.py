import re
from bs4 import BeautifulSoup
from html_to_markdown import convert_to_markdown

def clean_body(html, body_format=None):
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(['style', 'script', 'meta', 'link']):
            tag.decompose()
        for tag in soup.find_all(True):
            tag.attrs = {}
        cleaned_html = str(soup)
        cleaned_html = re.sub(r'(?s)@media[^{]+{[^}]+}', '', cleaned_html)
        cleaned_html = re.sub(r'(?s)\.[\w\-]+[^{]*{[^}]+}', '', cleaned_html)
        cleaned_html = re.sub(r'(?s){[^}]+}', '', cleaned_html)
        markdown = convert_to_markdown(cleaned_html, heading_style="atx")
        return markdown
    except Exception as e:
        return "[ERROR: Could not clean/convert this email]" 