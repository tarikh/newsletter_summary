import pytest
import json
import os
import tempfile
import datetime
from unittest.mock import patch, mock_open, MagicMock
from report import generate_report


class TestGenerateReport:
    """Test the main report generation function."""
    
    def test_generate_report_basic(self):
        """Test basic report generation functionality."""
        newsletters = [
            {
                'subject': 'AI Weekly Update',
                'sender': 'AI Newsletter <ai@newsletter.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<html><body><h1>AI News</h1><p>Content here</p></body></html>'
            }
        ]
        
        topics = ['AI Breakthrough', 'ChatGPT Update']
        llm_analysis = "### 1. AI Breakthrough\n- **What's New:** Revolutionary AI model"
        days = 7
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    report, filename_date_range = generate_report(
                        newsletters, topics, llm_analysis, days
                    )
        
        # Check basic structure
        assert "# AI NEWSLETTER SUMMARY" in report
        assert "## TOP AI DEVELOPMENTS THIS WEEK" in report
        assert "### 1. AI Breakthrough" in report
        assert "## NEWSLETTER SOURCES" in report
        assert "## METHODOLOGY" in report
        
        # Check filename format
        assert "20240102_1030" in filename_date_range
        assert "from_20240101" in filename_date_range
    
    def test_generate_report_with_model_info(self):
        """Test report generation with model information."""
        newsletters = [
            {
                'subject': 'Test Newsletter',
                'sender': 'Test <test@example.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>Test content</p>'
            }
        ]
        
        model_info = {
            "model": "claude-3-5-sonnet",
            "timestamp": "2024-01-01T12:00:00"
        }
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            mock_datetime.fromisoformat.return_value = datetime.datetime(2024, 1, 1, 12, 0, 0)
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    report, _ = generate_report(
                        newsletters, [], "Test analysis", 7, model_info
                    )
        
        # Check model info is included
        assert "## Generated with claude-3-5-sonnet" in report
        assert "Analysis performed using claude-3-5-sonnet on 2024-01-01 12:00:00" in report
    
    def test_generate_report_breaking_news_section(self):
        """Test breaking news section generation."""
        now = datetime.datetime(2024, 1, 2, 12, 0, 0)
        recent_date = now - datetime.timedelta(hours=12)  # Within 24 hours
        
        newsletters = [
            {
                'subject': 'Breaking: OpenAI Announces New Model',
                'sender': 'AI News <news@ai.com>',
                'date': recent_date.strftime('%a, %d %b %Y %H:%M:%S +0000'),
                'body': '<p>Breaking news content</p>'
            },
            {
                'subject': 'Regular Newsletter Update',
                'sender': 'Weekly AI <weekly@ai.com>',
                'date': recent_date.strftime('%a, %d %b %Y %H:%M:%S +0000'),
                'body': '<p>Regular content</p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.strftime = datetime.datetime.strftime
            mock_datetime.timedelta = datetime.timedelta
            
            with patch('report.parsedate_to_datetime') as mock_parse:
                mock_parse.return_value = recent_date
                
                with patch('builtins.open', mock_open(read_data='{}')):
                    with patch('os.path.exists', return_value=False):
                        report, _ = generate_report(
                            newsletters, [], "Test analysis", 7
                        )
        
        # Check breaking news section
        assert "## JUST IN: LATEST DEVELOPMENTS" in report
        assert "🔥 **OpenAI Announces New Model**" in report
        assert "Regular Newsletter Update" in report
    
    def test_generate_report_newsletter_sources(self):
        """Test newsletter sources section generation."""
        newsletters = [
            {
                'subject': 'Newsletter 1',
                'sender': 'The Neuron <newsletter@theneurondaily.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>Content with <a href="https://www.theneurondaily.com">website</a></p>'
            },
            {
                'subject': 'Newsletter 2',
                'sender': 'The Neuron <newsletter@theneurondaily.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>More content</p>'
            },
            {
                'subject': 'Newsletter 3',
                'sender': 'TLDR AI <ai@tldr.tech>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>TLDR content</p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    report, _ = generate_report(
                        newsletters, [], "Test analysis", 7
                    )
        
        # Check sources section
        assert "## NEWSLETTER SOURCES" in report
        assert "3 newsletters across 2 sources" in report
        assert "[The Neuron](https://www.theneurondaily.com) - 2 issues" in report
        assert "[TLDR AI](https://www.tldrnewsletter.com) - 1 issues" in report
    
    def test_generate_report_date_parsing_error(self):
        """Test handling of date parsing errors."""
        newsletters = [
            {
                'subject': 'Test Newsletter',
                'sender': 'Test <test@example.com>',
                'date': 'Invalid date format',
                'body': '<p>Test content</p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            mock_datetime.timedelta = datetime.timedelta
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    with patch('builtins.print') as mock_print:
                        report, _ = generate_report(
                            newsletters, [], "Test analysis", 7
                        )
        
        # Check that warning was printed
        mock_print.assert_called_once()
        assert "Warning: Could not parse date" in mock_print.call_args[0][0]
        
        # Check that report still generated with fallback date
        assert "# AI NEWSLETTER SUMMARY" in report
    
    def test_generate_report_website_cache_loading(self):
        """Test loading and updating website cache."""
        newsletters = [
            {
                'subject': 'Test Newsletter',
                'sender': 'Test Newsletter <test@example.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>Test content</p>'
            }
        ]
        
        existing_cache = {
            'test newsletter': {
                'url': 'https://cached.example.com',
                'verified': True
            }
        }
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            
            with patch('builtins.open', mock_open(read_data=json.dumps(existing_cache))) as mock_file:
                with patch('os.path.exists', return_value=True):
                    with patch('json.load', return_value=existing_cache):
                        report, _ = generate_report(
                            newsletters, [], "Test analysis", 7
                        )
        
        # Check that cached URL was used
        assert "[Test Newsletter](https://cached.example.com) - 1 issues" in report
    
    def test_generate_report_domain_from_email(self):
        """Test website detection from email domain."""
        newsletters = [
            {
                'subject': 'Test Newsletter',
                'sender': 'Example Newsletter <newsletter@example.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>Test content</p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    report, _ = generate_report(
                        newsletters, [], "Test analysis", 7
                    )
        
        # Check that domain-based URL was used
        assert "[Example Newsletter](https://example.com) - 1 issues" in report
    
    def test_generate_report_plausible_homepage_from_body(self):
        """Test website detection from newsletter body."""
        newsletters = [
            {
                'subject': 'Test Newsletter',
                'sender': 'Unknown Newsletter <unknown@random.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>Visit our website at <a href="https://website.com/">https://website.com/</a></p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    report, _ = generate_report(
                        newsletters, [], "Test analysis", 7
                    )
        
        # Check that URL from body was used
        assert "[Unknown Newsletter](https://website.com/) - 1 issues" in report
    
    def test_generate_report_filters_tracking_urls(self):
        """Test that tracking URLs are filtered out."""
        newsletters = [
            {
                'subject': 'Test Newsletter',
                'sender': 'Test <test@example.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>Visit <a href="https://track.example.com/click">tracking link</a> or <a href="https://example.com/">main site</a></p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    report, _ = generate_report(
                        newsletters, [], "Test analysis", 7
                    )
        
        # Check that tracking URL was filtered out and main site was used
        assert "track.example.com" not in report
        assert "[Test](https://example.com/) - 1 issues" in report
    
    def test_generate_report_curated_websites(self):
        """Test that curated websites override other detection methods."""
        newsletters = [
            {
                'subject': 'Test Newsletter',
                'sender': 'The Neuron <different@domain.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>Content with <a href="https://wrong.com">wrong link</a></p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    report, _ = generate_report(
                        newsletters, [], "Test analysis", 7
                    )
        
        # Check that curated website was used instead of domain or body URL
        assert "[The Neuron](https://www.theneurondaily.com) - 1 issues" in report
        assert "wrong.com" not in report
        assert "different.com" not in report
    
    def test_generate_report_no_website_found(self):
        """Test behavior when no website can be determined."""
        newsletters = [
            {
                'subject': 'Test Newsletter',
                'sender': 'Unknown <unknown@unknown.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>No useful links here</p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    report, _ = generate_report(
                        newsletters, [], "Test analysis", 7
                    )
        
        # Check that newsletter is listed without a link
        assert "- Unknown - 1 issues" in report
    
    def test_generate_report_cache_update(self):
        """Test that website cache is updated after report generation."""
        newsletters = [
            {
                'subject': 'Test Newsletter',
                'sender': 'Test <test@test.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>Content</p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            
            with patch('builtins.open', mock_open(read_data='{}')) as mock_file:
                with patch('os.path.exists', return_value=True):
                    with patch('json.load', return_value={}):
                        with patch('json.dump') as mock_dump:
                            report, _ = generate_report(
                                newsletters, [], "Test analysis", 7
                            )
        
        # Check that cache was updated
        mock_dump.assert_called_once()
        updated_cache = mock_dump.call_args[0][0]
        assert 'test' in updated_cache
        assert updated_cache['test']['url'] == 'https://test.com'
        assert not updated_cache['test']['verified']  # Should be False for domain-based detection
    
    def test_generate_report_subject_cleaning(self):
        """Test cleaning of newsletter subjects for breaking news."""
        now = datetime.datetime(2024, 1, 2, 12, 0, 0)
        recent_date = now - datetime.timedelta(hours=12)
        
        newsletters = [
            {
                'subject': '[AI Weekly] Breaking: New AI Model Released',
                'sender': 'AI News <news@ai.com>',
                'date': recent_date.strftime('%a, %d %b %Y %H:%M:%S +0000'),
                'body': '<p>Breaking news content</p>'
            },
            {
                'subject': 'Newsletter Name: Important Update',
                'sender': 'Weekly AI <weekly@ai.com>',
                'date': recent_date.strftime('%a, %d %b %Y %H:%M:%S +0000'),
                'body': '<p>Regular content</p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.strftime = datetime.datetime.strftime
            mock_datetime.timedelta = datetime.timedelta
            
            with patch('report.parsedate_to_datetime') as mock_parse:
                mock_parse.return_value = recent_date
                
                with patch('builtins.open', mock_open(read_data='{}')):
                    with patch('os.path.exists', return_value=False):
                        report, _ = generate_report(
                            newsletters, [], "Test analysis", 7
                        )
        
        # Check that subjects were cleaned
        assert "🔥 **New AI Model Released**" in report
        assert "Important Update" in report
        assert "[AI Weekly]" not in report
        assert "Newsletter Name:" not in report
    
    def test_generate_report_multiple_same_sender(self):
        """Test handling of multiple newsletters from same sender."""
        newsletters = [
            {
                'subject': 'Newsletter 1',
                'sender': 'Same Sender <same@example.com>',
                'date': 'Mon, 01 Jan 2024 12:00:00 +0000',
                'body': '<p>Content 1</p>'
            },
            {
                'subject': 'Newsletter 2',
                'sender': 'Same Sender <same@example.com>',
                'date': 'Tue, 02 Jan 2024 12:00:00 +0000',
                'body': '<p>Content 2</p>'
            },
            {
                'subject': 'Newsletter 3',
                'sender': 'Same Sender <same@example.com>',
                'date': 'Wed, 03 Jan 2024 12:00:00 +0000',
                'body': '<p>Content 3</p>'
            }
        ]
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 4, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    report, _ = generate_report(
                        newsletters, [], "Test analysis", 7
                    )
        
        # Check that count is correct
        assert "3 newsletters across 1 sources" in report
        assert "Same Sender](https://example.com) - 3 issues" in report
    
    def test_generate_report_empty_newsletters(self):
        """Test handling of empty newsletter list."""
        newsletters = []
        
        with patch('report.datetime.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 2, 10, 30, 0)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.datetime.strftime
            mock_datetime.timedelta = datetime.timedelta
            
            with patch('builtins.open', mock_open(read_data='{}')):
                with patch('os.path.exists', return_value=False):
                    report, _ = generate_report(
                        newsletters, [], "Test analysis", 7
                    )
        
        # Check that report handles empty newsletters gracefully
        assert "# AI NEWSLETTER SUMMARY" in report
        assert "0 newsletters across 0 sources" in report