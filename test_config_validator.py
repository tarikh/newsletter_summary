import pytest
import json
import os
import tempfile
from unittest.mock import patch, mock_open
from config_validator import (
    validate_url,
    validate_newsletter_websites_json,
    validate_environment_variables,
    validate_credentials_files,
    validate_all_configuration,
    print_validation_report,
    ConfigValidationError
)


class TestValidateUrl:
    """Test URL validation function."""
    
    def test_validate_url_valid_http(self):
        """Test validation of valid HTTP URLs."""
        assert validate_url("http://example.com") == True
        assert validate_url("http://www.example.com") == True
        assert validate_url("http://subdomain.example.com/path") == True
    
    def test_validate_url_valid_https(self):
        """Test validation of valid HTTPS URLs."""
        assert validate_url("https://example.com") == True
        assert validate_url("https://www.example.com") == True
        assert validate_url("https://subdomain.example.com/path/to/page") == True
    
    def test_validate_url_invalid_schemes(self):
        """Test validation rejects invalid schemes."""
        assert validate_url("ftp://example.com") == False
        assert validate_url("mailto:test@example.com") == False
        assert validate_url("javascript:alert('xss')") == False
    
    def test_validate_url_malformed(self):
        """Test validation of malformed URLs."""
        assert validate_url("not-a-url") == False
        assert validate_url("http://") == False
        assert validate_url("://example.com") == False
        assert validate_url("") == False
        assert validate_url("example.com") == False  # Missing scheme
    
    def test_validate_url_none_and_exceptions(self):
        """Test URL validation with None and exception cases."""
        assert validate_url(None) == False
        assert validate_url(123) == False  # Non-string input


class TestValidateNewsletterWebsitesJson:
    """Test newsletter websites JSON validation."""
    
    def test_validate_newsletter_websites_valid_file(self):
        """Test validation of valid newsletter websites file."""
        valid_data = {
            "newsletter1": {
                "url": "https://example1.com",
                "verified": True
            },
            "newsletter2": {
                "url": "https://example2.com",
                "verified": False
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(valid_data, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            is_valid, errors = validate_newsletter_websites_json(tmp_file_path)
            assert is_valid == True
            assert errors == []
        finally:
            os.unlink(tmp_file_path)
    
    def test_validate_newsletter_websites_missing_file(self):
        """Test validation when file doesn't exist."""
        is_valid, errors = validate_newsletter_websites_json('nonexistent.json')
        assert is_valid == False
        assert len(errors) == 1
        assert "not found" in errors[0]
    
    def test_validate_newsletter_websites_invalid_json(self):
        """Test validation of invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            tmp_file.write("invalid json content")
            tmp_file_path = tmp_file.name
        
        try:
            is_valid, errors = validate_newsletter_websites_json(tmp_file_path)
            assert is_valid == False
            assert len(errors) == 1
            assert "Invalid JSON" in errors[0]
        finally:
            os.unlink(tmp_file_path)
    
    def test_validate_newsletter_websites_not_dict(self):
        """Test validation when root is not a dictionary."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(["not", "a", "dict"], tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            is_valid, errors = validate_newsletter_websites_json(tmp_file_path)
            assert is_valid == False
            assert "Root element must be a dictionary" in errors[0]
        finally:
            os.unlink(tmp_file_path)
    
    def test_validate_newsletter_websites_missing_fields(self):
        """Test validation when required fields are missing."""
        invalid_data = {
            "newsletter1": {
                "url": "https://example.com"
                # Missing 'verified' field
            },
            "newsletter2": {
                "verified": True
                # Missing 'url' field
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(invalid_data, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            is_valid, errors = validate_newsletter_websites_json(tmp_file_path)
            assert is_valid == False
            assert len(errors) == 2
            assert any("Missing 'verified'" in error for error in errors)
            assert any("Missing 'url'" in error for error in errors)
        finally:
            os.unlink(tmp_file_path)
    
    def test_validate_newsletter_websites_invalid_url(self):
        """Test validation with invalid URLs."""
        invalid_data = {
            "newsletter1": {
                "url": "not-a-valid-url",
                "verified": True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(invalid_data, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            is_valid, errors = validate_newsletter_websites_json(tmp_file_path)
            assert is_valid == False
            assert "Invalid URL" in errors[0]
        finally:
            os.unlink(tmp_file_path)
    
    def test_validate_newsletter_websites_tracking_urls(self):
        """Test detection of tracking URLs."""
        tracking_data = {
            "newsletter1": {
                "url": "https://track.example.com/click?utm_source=newsletter",
                "verified": True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(tracking_data, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            is_valid, errors = validate_newsletter_websites_json(tmp_file_path)
            assert is_valid == False
            assert "tracking/temporary URL" in errors[0]
        finally:
            os.unlink(tmp_file_path)
    
    def test_validate_newsletter_websites_duplicate_urls(self):
        """Test detection of duplicate URLs."""
        duplicate_data = {
            "newsletter1": {
                "url": "https://example.com",
                "verified": True
            },
            "newsletter2": {
                "url": "https://example.com",
                "verified": True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(duplicate_data, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            is_valid, errors = validate_newsletter_websites_json(tmp_file_path)
            assert is_valid == False
            assert "Duplicate URL" in errors[0]
        finally:
            os.unlink(tmp_file_path)
    
    def test_validate_newsletter_websites_generic_domains(self):
        """Test detection of overly generic domains."""
        generic_data = {
            "newsletter1": {
                "url": "https://substack.com",
                "verified": True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(generic_data, tmp_file)
            tmp_file_path = tmp_file.name
        
        try:
            is_valid, errors = validate_newsletter_websites_json(tmp_file_path)
            assert is_valid == False
            assert "too generic" in errors[0]
        finally:
            os.unlink(tmp_file_path)


class TestValidateEnvironmentVariables:
    """Test environment variables validation."""
    
    @patch.dict(os.environ, {"USE_OPENROUTER": "true", "OPENROUTER_API_KEY": "test_key"})
    def test_validate_environment_openrouter_enabled_valid(self):
        """Test validation with OpenRouter enabled and valid key."""
        is_valid, errors = validate_environment_variables()
        assert is_valid == True
        assert errors == []
    
    @patch.dict(os.environ, {"USE_OPENROUTER": "true"}, clear=True)
    def test_validate_environment_openrouter_enabled_missing_key(self):
        """Test validation with OpenRouter enabled but missing key."""
        is_valid, errors = validate_environment_variables()
        assert is_valid == False
        assert "OPENROUTER_API_KEY environment variable is required" in errors[0]
    
    @patch.dict(os.environ, {"USE_OPENROUTER": "true", "OPENROUTER_API_KEY": "   "})
    def test_validate_environment_openrouter_enabled_empty_key(self):
        """Test validation with OpenRouter enabled but empty key."""
        is_valid, errors = validate_environment_variables()
        assert is_valid == False
        assert "OPENROUTER_API_KEY cannot be empty" in errors[0]
    
    @patch.dict(os.environ, {"USE_OPENROUTER": "false", "ANTHROPIC_API_KEY": "test_key"})
    def test_validate_environment_openrouter_disabled_valid(self):
        """Test validation with OpenRouter disabled and valid direct API key."""
        is_valid, errors = validate_environment_variables()
        assert is_valid == True
        assert errors == []
    
    @patch.dict(os.environ, {"USE_OPENROUTER": "false"}, clear=True)
    def test_validate_environment_openrouter_disabled_no_keys(self):
        """Test validation with OpenRouter disabled but no direct API keys."""
        is_valid, errors = validate_environment_variables()
        assert is_valid == False
        assert "Either ANTHROPIC_API_KEY or OPENAI_API_KEY is required" in errors[0]
    
    @patch.dict(os.environ, {"USE_OPENROUTER": "false", "ANTHROPIC_API_KEY": "   "})
    def test_validate_environment_openrouter_disabled_empty_key(self):
        """Test validation with empty direct API key."""
        is_valid, errors = validate_environment_variables()
        assert is_valid == False
        assert "ANTHROPIC_API_KEY cannot be empty" in errors[0]
    
    @patch.dict(os.environ, {"OPENROUTER_COST_LOG": "/nonexistent/path/log.json"})
    def test_validate_environment_invalid_cost_log_path(self):
        """Test validation with invalid cost log directory."""
        is_valid, errors = validate_environment_variables()
        assert is_valid == False
        assert "Directory for OPENROUTER_COST_LOG does not exist" in errors[0]
    
    @patch.dict(os.environ, {"NEWSLETTER_SUMMARY_OUTPUT_DIR": "/nonexistent/path"})
    def test_validate_environment_invalid_output_dir(self):
        """Test validation with invalid output directory."""
        is_valid, errors = validate_environment_variables()
        assert is_valid == False
        assert "NEWSLETTER_SUMMARY_OUTPUT_DIR does not exist" in errors[0]


class TestValidateCredentialsFiles:
    """Test credentials files validation."""
    
    def test_validate_credentials_files_missing_credentials(self):
        """Test validation when credentials.json is missing."""
        with patch('os.path.exists', return_value=False):
            is_valid, errors = validate_credentials_files()
            assert is_valid == False
            assert "credentials.json' not found" in errors[0]
    
    def test_validate_credentials_files_valid_credentials(self):
        """Test validation with valid credentials.json."""
        valid_creds = {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(valid_creds))):
                is_valid, errors = validate_credentials_files()
                assert is_valid == True
                assert errors == []
    
    def test_validate_credentials_files_invalid_json(self):
        """Test validation with invalid JSON in credentials.json."""
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='invalid json')):
                is_valid, errors = validate_credentials_files()
                assert is_valid == False
                assert "Invalid JSON in credentials.json" in errors[0]
    
    def test_validate_credentials_files_missing_fields(self):
        """Test validation with missing required fields."""
        invalid_creds = {
            "installed": {
                "client_id": "test_client_id"
                # Missing other required fields
            }
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(invalid_creds))):
                is_valid, errors = validate_credentials_files()
                assert is_valid == False
                assert len(errors) >= 3  # Missing client_secret, auth_uri, token_uri
    
    def test_validate_credentials_files_valid_token(self):
        """Test validation with valid token.json."""
        valid_creds = {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        valid_token = {
            "token": "test_token",
            "refresh_token": "test_refresh"
        }
        
        def mock_exists(path):
            return True
        
        def mock_open_func(path, *args, **kwargs):
            if 'credentials.json' in path:
                return mock_open(read_data=json.dumps(valid_creds))()
            elif 'token.json' in path:
                return mock_open(read_data=json.dumps(valid_token))()
        
        with patch('os.path.exists', side_effect=mock_exists):
            with patch('builtins.open', side_effect=mock_open_func):
                is_valid, errors = validate_credentials_files()
                assert is_valid == True
                assert errors == []
    
    def test_validate_credentials_files_invalid_token(self):
        """Test validation with invalid token.json."""
        valid_creds = {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        
        def mock_exists(path):
            return True
        
        def mock_open_func(path, *args, **kwargs):
            if 'credentials.json' in path:
                return mock_open(read_data=json.dumps(valid_creds))()
            elif 'token.json' in path:
                return mock_open(read_data='invalid json')()
        
        with patch('os.path.exists', side_effect=mock_exists):
            with patch('builtins.open', side_effect=mock_open_func):
                is_valid, errors = validate_credentials_files()
                assert is_valid == False
                assert "Invalid JSON in token.json" in errors[0]


class TestValidateAllConfiguration:
    """Test comprehensive configuration validation."""
    
    @patch('config_validator.validate_newsletter_websites_json')
    @patch('config_validator.validate_environment_variables')
    @patch('config_validator.validate_credentials_files')
    def test_validate_all_configuration_all_valid(self, mock_creds, mock_env, mock_websites):
        """Test when all configuration is valid."""
        mock_websites.return_value = (True, [])
        mock_env.return_value = (True, [])
        mock_creds.return_value = (True, [])
        
        is_valid, errors = validate_all_configuration()
        assert is_valid == True
        assert errors == {}
    
    @patch('config_validator.validate_newsletter_websites_json')
    @patch('config_validator.validate_environment_variables')
    @patch('config_validator.validate_credentials_files')
    def test_validate_all_configuration_some_invalid(self, mock_creds, mock_env, mock_websites):
        """Test when some configuration is invalid."""
        mock_websites.return_value = (False, ["Website error"])
        mock_env.return_value = (True, [])
        mock_creds.return_value = (False, ["Credentials error"])
        
        is_valid, errors = validate_all_configuration()
        assert is_valid == False
        assert 'newsletter_websites' in errors
        assert 'credentials' in errors
        assert 'environment' not in errors
        assert errors['newsletter_websites'] == ["Website error"]
        assert errors['credentials'] == ["Credentials error"]


class TestPrintValidationReport:
    """Test validation report printing."""
    
    def test_print_validation_report_no_errors(self, capsys):
        """Test printing when no errors exist."""
        print_validation_report({})
        captured = capsys.readouterr()
        assert "All configuration validation checks passed!" in captured.out
    
    def test_print_validation_report_with_errors(self, capsys):
        """Test printing when errors exist."""
        errors = {
            'newsletter_websites': ['Website error 1', 'Website error 2'],
            'environment': ['Env error 1']
        }
        print_validation_report(errors)
        captured = capsys.readouterr()
        
        assert "Configuration validation failed" in captured.out
        assert "Newsletter Websites:" in captured.out
        assert "Website error 1" in captured.out
        assert "Website error 2" in captured.out
        assert "Environment:" in captured.out
        assert "Env error 1" in captured.out