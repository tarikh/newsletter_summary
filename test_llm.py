import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from llm import (
    analyze_newsletters_unified, 
    analyze_with_openrouter,
    log_cost_data,
    analyze_with_fallback,
    check_openrouter_status,
    analyze_with_llm_direct
)


class TestAnalyzeNewslettersUnified:
    """Test the main newsletter analysis function."""
    
    def test_analyze_newsletters_unified_basic(self):
        """Test basic newsletter analysis with mocked responses."""
        newsletters = [
            {
                'subject': 'AI Weekly Update',
                'sender': 'ai@newsletter.com',
                'date': '2024-01-01',
                'body': '<html><body><h1>AI News</h1><p>ChatGPT update released</p></body></html>',
                'body_format': 'html'
            }
        ]
        
        expected_response = """### 1. ChatGPT Major Update
- **What's New:** OpenAI releases new version with improved capabilities
- **Why It Matters:** Better AI assistance for everyday tasks
- **Practical Impact:** Users can now get more accurate help with work and personal tasks
- **Source:** AI Weekly Update"""
        
        with patch('llm.analyze_with_openrouter') as mock_openrouter:
            mock_openrouter.return_value = expected_response
            
            result, topics = analyze_newsletters_unified(newsletters)
            
            assert result == expected_response
            assert 'ChatGPT Major Update' in topics
            mock_openrouter.assert_called_once()
    
    def test_analyze_newsletters_unified_custom_topics(self):
        """Test with custom number of topics."""
        newsletters = [
            {
                'subject': 'Test Newsletter',
                'sender': 'test@example.com',
                'date': '2024-01-01',
                'body': '<p>Test content</p>',
                'body_format': 'html'
            }
        ]
        
        with patch('llm.analyze_with_openrouter') as mock_openrouter:
            mock_openrouter.return_value = "### 1. Test Topic\n- **What's New:** Test"
            
            analyze_newsletters_unified(newsletters, num_topics=5)
            
            # Check that the prompt includes the custom number of topics
            call_args = mock_openrouter.call_args[0][0]
            assert "5 most significant" in call_args
    
    def test_analyze_newsletters_unified_content_truncation(self):
        """Test that long content is truncated to manage token usage."""
        long_content = "A" * 5000  # Content longer than 3000 chars
        newsletters = [
            {
                'subject': 'Long Newsletter',
                'sender': 'long@example.com',
                'date': '2024-01-01',
                'body': f'<p>{long_content}</p>',
                'body_format': 'html'
            }
        ]
        
        with patch('llm.analyze_with_openrouter') as mock_openrouter:
            mock_openrouter.return_value = "### 1. Test Topic"
            
            analyze_newsletters_unified(newsletters)
            
            # Check that content was truncated
            call_args = mock_openrouter.call_args[0][0]
            assert "..." in call_args
    
    def test_analyze_newsletters_unified_multiple_newsletters(self):
        """Test processing multiple newsletters."""
        newsletters = [
            {
                'subject': 'Newsletter 1',
                'sender': 'sender1@example.com',
                'date': '2024-01-01',
                'body': '<p>Content 1</p>',
                'body_format': 'html'
            },
            {
                'subject': 'Newsletter 2',
                'sender': 'sender2@example.com',
                'date': '2024-01-02',
                'body': '<p>Content 2</p>',
                'body_format': 'html'
            }
        ]
        
        with patch('llm.analyze_with_openrouter') as mock_openrouter:
            mock_openrouter.return_value = "### 1. Combined Topic"
            
            analyze_newsletters_unified(newsletters)
            
            # Check that both newsletters are included in the prompt
            call_args = mock_openrouter.call_args[0][0]
            assert "NEWSLETTER #1" in call_args
            assert "NEWSLETTER #2" in call_args
            assert "Newsletter 1" in call_args
            assert "Newsletter 2" in call_args
    
    @patch.dict(os.environ, {"USE_OPENROUTER": "false"})
    def test_analyze_newsletters_unified_direct_openai(self):
        """Test direct OpenAI API call when OpenRouter is disabled."""
        newsletters = [
            {
                'subject': 'Test',
                'sender': 'test@example.com',
                'date': '2024-01-01',
                'body': '<p>Test content</p>'
            }
        ]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "### 1. Test Topic"
        
        with patch('llm.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            result, topics = analyze_newsletters_unified(newsletters, provider='openai')
            
            assert result == "### 1. Test Topic"
            mock_client.chat.completions.create.assert_called_once()
    
    @patch.dict(os.environ, {"USE_OPENROUTER": "false"})
    def test_analyze_newsletters_unified_direct_claude(self):
        """Test direct Claude API call when OpenRouter is disabled."""
        newsletters = [
            {
                'subject': 'Test',
                'sender': 'test@example.com',
                'date': '2024-01-01',
                'body': '<p>Test content</p>'
            }
        ]
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "### 1. Test Topic"
        
        with patch('llm.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            result, topics = analyze_newsletters_unified(newsletters, provider='claude')
            
            assert result == "### 1. Test Topic"
            mock_client.messages.create.assert_called_once()


class TestAnalyzeWithOpenrouter:
    """Test the OpenRouter integration function."""
    
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    def test_analyze_with_openrouter_success(self):
        """Test successful OpenRouter API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test response'}}],
            'usage': {'total_tokens': 100, 'prompt_tokens': 50, 'completion_tokens': 50}
        }
        
        with patch('llm.requests.post') as mock_post:
            mock_post.return_value = mock_response
            with patch('llm.log_cost_data') as mock_log:
                result = analyze_with_openrouter("Test prompt", "openai")
                
                assert result == "Test response"
                mock_post.assert_called_once()
                mock_log.assert_called_once()
    
    def test_analyze_with_openrouter_missing_key(self):
        """Test error when OpenRouter API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY environment variable is required"):
                analyze_with_openrouter("Test prompt", "openai")
    
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    def test_analyze_with_openrouter_custom_model(self):
        """Test using custom OpenRouter model."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test response'}}],
            'usage': {'total_tokens': 100}
        }
        
        with patch('llm.requests.post') as mock_post:
            mock_post.return_value = mock_response
            with patch('llm.log_cost_data'):
                analyze_with_openrouter("Test prompt", "openai", "custom/model")
                
                # Check that custom model was used
                call_data = json.loads(mock_post.call_args[1]['data'])
                assert call_data['model'] == "custom/model"
    
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    def test_analyze_with_openrouter_api_error(self):
        """Test handling of API errors."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        
        with patch('llm.requests.post') as mock_post:
            mock_post.return_value = mock_response
            
            with pytest.raises(Exception, match="Error from OpenRouter API"):
                analyze_with_openrouter("Test prompt", "openai")
    
    def test_analyze_with_openrouter_unknown_provider(self):
        """Test error with unknown provider."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"}):
            with pytest.raises(ValueError, match="Unknown model provider"):
                analyze_with_openrouter("Test prompt", "unknown_provider")


class TestLogCostData:
    """Test the cost logging functionality."""
    
    def test_log_cost_data_new_file(self):
        """Test logging to a new file."""
        cost_data = {
            "timestamp": "2024-01-01T00:00:00",
            "model": "test-model",
            "total_tokens": 100,
            "cost": 0.001
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_file_path = tmp_file.name
        
        try:
            # Remove the file so we test new file creation
            os.unlink(tmp_file_path)
            
            with patch.dict(os.environ, {"OPENROUTER_COST_LOG": tmp_file_path}):
                log_cost_data(cost_data)
                
                # Check that file was created and contains the data
                with open(tmp_file_path, 'r') as f:
                    logged_data = json.load(f)
                
                assert len(logged_data) == 1
                assert logged_data[0] == cost_data
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    def test_log_cost_data_append_to_existing(self):
        """Test appending to existing cost log file."""
        existing_data = [{"timestamp": "2024-01-01T00:00:00", "cost": 0.001}]
        new_data = {"timestamp": "2024-01-02T00:00:00", "cost": 0.002}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            json.dump(existing_data, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            with patch.dict(os.environ, {"OPENROUTER_COST_LOG": tmp_file_path}):
                log_cost_data(new_data)
                
                # Check that data was appended
                with open(tmp_file_path, 'r') as f:
                    logged_data = json.load(f)
                
                assert len(logged_data) == 2
                assert logged_data[0] == existing_data[0]
                assert logged_data[1] == new_data
        finally:
            os.unlink(tmp_file_path)
    
    def test_log_cost_data_corrupted_file(self):
        """Test handling of corrupted JSON file."""
        cost_data = {"timestamp": "2024-01-01T00:00:00", "cost": 0.001}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_file.write("invalid json content")
            tmp_file_path = tmp_file.name
        
        try:
            with patch.dict(os.environ, {"OPENROUTER_COST_LOG": tmp_file_path}):
                log_cost_data(cost_data)
                
                # Check that file was overwritten with new data
                with open(tmp_file_path, 'r') as f:
                    logged_data = json.load(f)
                
                assert len(logged_data) == 1
                assert logged_data[0] == cost_data
        finally:
            os.unlink(tmp_file_path)


class TestAnalyzeWithFallback:
    """Test the fallback mechanism."""
    
    def test_analyze_with_fallback_success(self):
        """Test successful OpenRouter call without fallback."""
        with patch('llm.analyze_with_openrouter') as mock_openrouter:
            mock_openrouter.return_value = "Success response"
            
            result = analyze_with_fallback("Test prompt")
            
            assert result == "Success response"
            mock_openrouter.assert_called_once()
    
    def test_analyze_with_fallback_to_direct_api(self):
        """Test fallback to direct API when OpenRouter fails."""
        with patch('llm.analyze_with_openrouter') as mock_openrouter:
            mock_openrouter.side_effect = Exception("OpenRouter error")
            
            with patch('llm.analyze_with_llm_direct') as mock_direct:
                mock_direct.return_value = "Fallback response"
                
                result = analyze_with_fallback("Test prompt")
                
                assert result == "Fallback response"
                mock_openrouter.assert_called_once()
                mock_direct.assert_called_once()


class TestCheckOpenrouterStatus:
    """Test the OpenRouter status checking function."""
    
    def test_check_openrouter_status_missing_key(self):
        """Test status check when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            success, message = check_openrouter_status()
            
            assert not success
            assert "OPENROUTER_API_KEY environment variable not set" in message
    
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    def test_check_openrouter_status_success(self):
        """Test successful status check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rate_limit": "1000",
            "rate_limit_remaining": "999"
        }
        
        with patch('llm.requests.get') as mock_get:
            mock_get.return_value = mock_response
            
            success, message = check_openrouter_status()
            
            assert success
            assert "OpenRouter configured correctly" in message
            assert "1000" in message
            assert "999" in message
    
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    def test_check_openrouter_status_api_error(self):
        """Test status check with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch('llm.requests.get') as mock_get:
            mock_get.return_value = mock_response
            
            success, message = check_openrouter_status()
            
            assert not success
            assert "OpenRouter API error" in message
            assert "Unauthorized" in message
    
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    def test_check_openrouter_status_exception(self):
        """Test status check with network exception."""
        with patch('llm.requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            success, message = check_openrouter_status()
            
            assert not success
            assert "Error checking OpenRouter status" in message
            assert "Network error" in message


class TestAnalyzeWithLlmDirect:
    """Test the direct LLM API function."""
    
    def test_analyze_with_llm_direct_openai(self):
        """Test direct OpenAI API call."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "OpenAI response"
        
        with patch('llm.openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            result = analyze_with_llm_direct("Test prompt", provider='openai')
            
            assert result == "OpenAI response"
            mock_client.chat.completions.create.assert_called_once()
    
    def test_analyze_with_llm_direct_claude(self):
        """Test direct Claude API call."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Claude response"
        
        with patch('llm.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            result = analyze_with_llm_direct("Test prompt", provider='claude')
            
            assert result == "Claude response"
            mock_client.messages.create.assert_called_once()
    
    def test_analyze_with_llm_direct_default_provider(self):
        """Test that Claude is used as default provider."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Default response"
        
        with patch('llm.anthropic.Anthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client
            
            result = analyze_with_llm_direct("Test prompt")
            
            assert result == "Default response"
            mock_client.messages.create.assert_called_once()


class TestTopicExtraction:
    """Test topic extraction from analysis results."""
    
    def test_topic_extraction_from_analysis(self):
        """Test extracting topic titles from analysis text."""
        analysis_text = """
        ### 1. ChatGPT Gets Major Update
        - **What's New:** OpenAI releases new version
        
        ### 2. Google Announces Bard AI
        - **What's New:** Google's AI assistant launches
        
        ### 3. Meta's AI Research Breakthrough
        - **What's New:** New language model architecture
        """
        
        newsletters = [
            {
                'subject': 'Test',
                'sender': 'test@example.com',
                'date': '2024-01-01',
                'body': '<p>Test content</p>'
            }
        ]
        
        with patch('llm.analyze_with_openrouter') as mock_openrouter:
            mock_openrouter.return_value = analysis_text
            
            result, topics = analyze_newsletters_unified(newsletters)
            
            assert len(topics) == 3
            assert "ChatGPT Gets Major Update" in topics
            assert "Google Announces Bard AI" in topics
            assert "Meta's AI Research Breakthrough" in topics