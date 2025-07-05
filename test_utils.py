import pytest
from unittest.mock import patch, MagicMock
from utils import clean_body


class TestCleanBody:
    """Test the clean_body function for HTML cleaning and conversion."""
    
    def test_clean_body_basic_html(self):
        """Test basic HTML cleaning and conversion to markdown."""
        html = """
        <html>
            <body>
                <h1>Test Newsletter</h1>
                <p>This is a test paragraph.</p>
                <a href="https://example.com">Link text</a>
            </body>
        </html>
        """
        result = clean_body(html)
        
        # Check that markdown conversion happened
        assert "# Test Newsletter" in result
        assert "This is a test paragraph." in result
        assert "Link text" in result
        
    def test_clean_body_removes_style_tags(self):
        """Test that style tags are completely removed."""
        html = """
        <html>
            <head>
                <style>
                    body { color: red; }
                    .header { font-size: 20px; }
                </style>
            </head>
            <body>
                <h1>Header</h1>
                <p>Content</p>
            </body>
        </html>
        """
        result = clean_body(html)
        
        # Style content should be removed
        assert "color: red" not in result
        assert "font-size: 20px" not in result
        assert "body {" not in result
        assert ".header {" not in result
        
        # Content should remain
        assert "Header" in result
        assert "Content" in result
        
    def test_clean_body_removes_script_tags(self):
        """Test that script tags are completely removed."""
        html = """
        <html>
            <body>
                <h1>Newsletter</h1>
                <script>
                    console.log("tracking code");
                    analytics.track("page_view");
                </script>
                <p>Main content</p>
            </body>
        </html>
        """
        result = clean_body(html)
        
        # Script content should be removed
        assert "console.log" not in result
        assert "analytics.track" not in result
        assert "tracking code" not in result
        
        # Content should remain
        assert "Newsletter" in result
        assert "Main content" in result
        
    def test_clean_body_removes_meta_and_link_tags(self):
        """Test that meta and link tags are removed."""
        html = """
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="description" content="Newsletter description">
                <link rel="stylesheet" href="styles.css">
            </head>
            <body>
                <h1>Content</h1>
            </body>
        </html>
        """
        result = clean_body(html)
        
        # Meta and link tags should be removed
        assert "charset" not in result
        assert "description" not in result
        assert "stylesheet" not in result
        assert "styles.css" not in result
        
        # Content should remain
        assert "Content" in result
        
    def test_clean_body_removes_all_attributes(self):
        """Test that all HTML attributes are removed."""
        html = """
        <html>
            <body>
                <h1 class="header" id="main-title" style="color: blue;">Title</h1>
                <p class="content" data-tracking="123">Paragraph</p>
                <a href="https://example.com" target="_blank" rel="noopener">Link</a>
            </body>
        </html>
        """
        result = clean_body(html)
        
        # Attributes should be removed
        assert 'class="header"' not in result
        assert 'id="main-title"' not in result
        assert 'style="color: blue;"' not in result
        assert 'data-tracking="123"' not in result
        assert 'target="_blank"' not in result
        assert 'rel="noopener"' not in result
        
        # Content should remain
        assert "Title" in result
        assert "Paragraph" in result
        assert "Link" in result
        
    def test_clean_body_removes_css_rules(self):
        """Test that CSS rules are removed from the content."""
        html = """
        <html>
            <body>
                <div>
                    @media screen and (max-width: 600px) {
                        .mobile { display: block; }
                    }
                    .container { width: 100%; }
                    #header { background: blue; }
                    { orphaned rule }
                </div>
                <p>Main content</p>
            </body>
        </html>
        """
        result = clean_body(html)
        
        # CSS rules should be removed
        assert "@media screen" not in result
        assert ".mobile { display: block; }" not in result
        assert ".container { width: 100%; }" not in result
        assert "#header { background: blue; }" not in result
        assert "{ orphaned rule }" not in result
        
        # Content should remain
        assert "Main content" in result
        
    def test_clean_body_with_empty_html(self):
        """Test behavior with empty HTML."""
        html = ""
        result = clean_body(html)
        
        # Should return some form of processed content, not crash
        assert isinstance(result, str)
        
    def test_clean_body_with_none_input(self):
        """Test behavior with None input."""
        result = clean_body(None)
        
        # Should return error message due to exception
        assert result == "[ERROR: Could not clean/convert this email]"
        
    def test_clean_body_with_plain_text(self):
        """Test behavior with plain text (no HTML)."""
        text = "This is plain text with no HTML tags."
        result = clean_body(text)
        
        # Should still process and return the text
        assert "This is plain text with no HTML tags." in result
        
    def test_clean_body_with_malformed_html(self):
        """Test behavior with malformed HTML."""
        html = "<html><body><p>Unclosed paragraph<h1>Header</body>"
        result = clean_body(html)
        
        # Should still process successfully
        assert "Unclosed paragraph" in result
        assert "Header" in result
        
    @patch('utils.convert_to_markdown')
    def test_clean_body_markdown_conversion_error(self, mock_convert):
        """Test error handling when markdown conversion fails."""
        mock_convert.side_effect = Exception("Markdown conversion failed")
        
        html = "<html><body><p>Test content</p></body></html>"
        result = clean_body(html)
        
        # Should return error message
        assert result == "[ERROR: Could not clean/convert this email]"
        
    @patch('utils.BeautifulSoup')
    def test_clean_body_beautifulsoup_error(self, mock_soup):
        """Test error handling when BeautifulSoup fails."""
        mock_soup.side_effect = Exception("BeautifulSoup parsing failed")
        
        html = "<html><body><p>Test content</p></body></html>"
        result = clean_body(html)
        
        # Should return error message
        assert result == "[ERROR: Could not clean/convert this email]"
        
    def test_clean_body_preserves_structure(self):
        """Test that the basic structure is preserved in markdown."""
        html = """
        <html>
            <body>
                <h1>Main Title</h1>
                <h2>Section Title</h2>
                <p>First paragraph</p>
                <p>Second paragraph</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                </ul>
            </body>
        </html>
        """
        result = clean_body(html)
        
        # Check that structure is preserved
        assert "# Main Title" in result
        assert "## Section Title" in result
        assert "First paragraph" in result
        assert "Second paragraph" in result
        assert "Item 1" in result
        assert "Item 2" in result
        
    def test_clean_body_with_body_format_parameter(self):
        """Test that body_format parameter is handled (even if not used)."""
        html = "<html><body><p>Test content</p></body></html>"
        
        # Should not crash with body_format parameter
        result = clean_body(html, body_format="html")
        assert "Test content" in result
        
        result = clean_body(html, body_format="plain")
        assert "Test content" in result
        
    def test_clean_body_complex_newsletter_structure(self):
        """Test with a more complex newsletter-like structure."""
        html = """
        <html>
            <head>
                <style>
                    .header { background: #f0f0f0; }
                    .content { padding: 20px; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>AI Newsletter</h1>
                    <p>Weekly AI updates</p>
                </div>
                <div class="content">
                    <h2>This Week's Highlights</h2>
                    <p>OpenAI released new models...</p>
                    <a href="https://openai.com" target="_blank">Read more</a>
                </div>
                <script>
                    // Tracking code
                    analytics.track('newsletter_open');
                </script>
            </body>
        </html>
        """
        result = clean_body(html)
        
        # Content should be preserved
        assert "AI Newsletter" in result
        assert "Weekly AI updates" in result
        assert "This Week's Highlights" in result
        assert "OpenAI released new models" in result
        assert "Read more" in result
        
        # Unwanted elements should be removed
        assert "background: #f0f0f0" not in result
        assert "padding: 20px" not in result
        assert "analytics.track" not in result
        assert "newsletter_open" not in result
        assert 'class="header"' not in result
        assert 'target="_blank"' not in result