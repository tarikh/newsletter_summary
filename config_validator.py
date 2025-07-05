"""
Configuration validation module for newsletter summary application.

This module provides validation functions for JSON configuration files
and environment variables to ensure the application has proper setup.
"""

import json
import os
import re
from typing import Dict, List, Tuple, Any
from urllib.parse import urlparse


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails."""
    pass


def validate_url(url: str) -> bool:
    """
    Validate that a URL is properly formatted.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except Exception:
        return False


def validate_newsletter_websites_json(file_path: str = 'newsletter_websites.json') -> Tuple[bool, List[str]]:
    """
    Validate the newsletter websites JSON configuration file.
    
    Args:
        file_path: Path to the newsletter websites JSON file
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not os.path.exists(file_path):
        errors.append(f"Newsletter websites file not found: {file_path}")
        return False, errors
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in {file_path}: {str(e)}")
        return False, errors
    except Exception as e:
        errors.append(f"Error reading {file_path}: {str(e)}")
        return False, errors
    
    if not isinstance(data, dict):
        errors.append(f"Root element must be a dictionary in {file_path}")
        return False, errors
    
    # Track URLs to check for duplicates
    url_to_names = {}
    
    for name, config in data.items():
        # Validate name
        if not isinstance(name, str) or not name.strip():
            errors.append(f"Newsletter name must be a non-empty string: {repr(name)}")
            continue
            
        # Check for problematic characters in name
        if name != name.strip():
            errors.append(f"Newsletter name has leading/trailing whitespace: {repr(name)}")
        
        # Validate config structure
        if not isinstance(config, dict):
            errors.append(f"Configuration for '{name}' must be a dictionary")
            continue
            
        # Check required fields
        if 'url' not in config:
            errors.append(f"Missing 'url' field for newsletter '{name}'")
            continue
            
        if 'verified' not in config:
            errors.append(f"Missing 'verified' field for newsletter '{name}'")
            continue
        
        # Validate URL
        url = config['url']
        if not isinstance(url, str):
            errors.append(f"URL for '{name}' must be a string: {repr(url)}")
            continue
            
        if not validate_url(url):
            errors.append(f"Invalid URL for '{name}': {url}")
            continue
        
        # Check for tracking URLs or other problematic patterns
        tracking_patterns = [
            'track', 'utm_', 'pixel', 'open?token=', 'viewform',
            'unsubscribe', 'cdn-cgi', 'jwt_token'
        ]
        if any(pattern in url.lower() for pattern in tracking_patterns):
            errors.append(f"URL for '{name}' appears to be a tracking/temporary URL: {url}")
        
        # Check for generic domains that should be more specific
        generic_domains = ['substack.com', 'gmail.com', 'yahoo.com', 'outlook.com']
        parsed_url = urlparse(url)
        if parsed_url.netloc.lower() in generic_domains and parsed_url.path in ['', '/']:
            errors.append(f"URL for '{name}' is too generic, should be more specific: {url}")
        
        # Track duplicate URLs
        if url in url_to_names:
            errors.append(f"Duplicate URL found: '{name}' and '{url_to_names[url]}' both use {url}")
        else:
            url_to_names[url] = name
        
        # Validate verified field
        verified = config['verified']
        if not isinstance(verified, bool):
            errors.append(f"'verified' field for '{name}' must be a boolean: {repr(verified)}")
    
    return len(errors) == 0, errors


def validate_environment_variables() -> Tuple[bool, List[str]]:
    """
    Validate required environment variables for the application.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check USE_OPENROUTER setting
    use_openrouter = os.environ.get("USE_OPENROUTER", "true").lower()
    if use_openrouter in ("true", "1", "yes"):
        # OpenRouter is enabled, check for OpenRouter API key
        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_key:
            errors.append("OPENROUTER_API_KEY environment variable is required when USE_OPENROUTER is enabled")
        elif not openrouter_key.strip():
            errors.append("OPENROUTER_API_KEY cannot be empty")
    else:
        # OpenRouter is disabled, check for direct API keys
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")
        
        if not anthropic_key and not openai_key:
            errors.append("Either ANTHROPIC_API_KEY or OPENAI_API_KEY is required when USE_OPENROUTER is disabled")
        
        if anthropic_key and not anthropic_key.strip():
            errors.append("ANTHROPIC_API_KEY cannot be empty")
        
        if openai_key and not openai_key.strip():
            errors.append("OPENAI_API_KEY cannot be empty")
    
    # Check cost log file path if specified
    cost_log_path = os.environ.get("OPENROUTER_COST_LOG")
    if cost_log_path:
        cost_log_dir = os.path.dirname(cost_log_path)
        if cost_log_dir and not os.path.exists(cost_log_dir):
            errors.append(f"Directory for OPENROUTER_COST_LOG does not exist: {cost_log_dir}")
    
    # Check output directory if specified
    output_dir = os.environ.get("NEWSLETTER_SUMMARY_OUTPUT_DIR")
    if output_dir and not os.path.exists(output_dir):
        errors.append(f"NEWSLETTER_SUMMARY_OUTPUT_DIR does not exist: {output_dir}")
    
    return len(errors) == 0, errors


def validate_credentials_files() -> Tuple[bool, List[str]]:
    """
    Validate Gmail credentials files.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check for credentials.json
    if not os.path.exists('credentials.json'):
        errors.append("Gmail credentials file 'credentials.json' not found")
    else:
        try:
            with open('credentials.json', 'r', encoding='utf-8') as f:
                creds_data = json.load(f)
                
            # Basic structure validation
            if 'installed' not in creds_data and 'web' not in creds_data:
                errors.append("credentials.json missing required OAuth client configuration")
            
            # Check for required fields in the client config
            client_config = creds_data.get('installed') or creds_data.get('web', {})
            required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            
            for field in required_fields:
                if field not in client_config:
                    errors.append(f"credentials.json missing required field: {field}")
                    
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in credentials.json: {str(e)}")
        except Exception as e:
            errors.append(f"Error reading credentials.json: {str(e)}")
    
    # Check token.json if it exists (optional file)
    if os.path.exists('token.json'):
        try:
            with open('token.json', 'r', encoding='utf-8') as f:
                token_data = json.load(f)
                
            # Basic validation of token structure
            if not isinstance(token_data, dict):
                errors.append("token.json must contain a JSON object")
            elif 'token' not in token_data:
                errors.append("token.json missing 'token' field")
                
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in token.json: {str(e)}")
        except Exception as e:
            errors.append(f"Error reading token.json: {str(e)}")
    
    return len(errors) == 0, errors


def validate_all_configuration() -> Tuple[bool, Dict[str, List[str]]]:
    """
    Validate all configuration aspects of the application.
    
    Returns:
        Tuple of (is_valid, dict_of_errors_by_category)
    """
    all_errors = {}
    all_valid = True
    
    # Validate newsletter websites
    valid, errors = validate_newsletter_websites_json()
    if errors:
        all_errors['newsletter_websites'] = errors
        all_valid = False
    
    # Validate environment variables
    valid, errors = validate_environment_variables()
    if errors:
        all_errors['environment'] = errors
        all_valid = False
    
    # Validate credentials files
    valid, errors = validate_credentials_files()
    if errors:
        all_errors['credentials'] = errors
        all_valid = False
    
    return all_valid, all_errors


def print_validation_report(errors_by_category: Dict[str, List[str]]) -> None:
    """
    Print a formatted validation report.
    
    Args:
        errors_by_category: Dictionary of error lists by category
    """
    if not errors_by_category:
        print("✅ All configuration validation checks passed!")
        return
    
    print("❌ Configuration validation failed:")
    print()
    
    for category, errors in errors_by_category.items():
        print(f"📁 {category.replace('_', ' ').title()}:")
        for error in errors:
            print(f"   • {error}")
        print()
    
    print("Please fix the above issues before running the application.")


if __name__ == "__main__":
    """Run configuration validation when script is executed directly."""
    print("Validating newsletter summary configuration...")
    print()
    
    is_valid, errors = validate_all_configuration()
    print_validation_report(errors)
    
    if not is_valid:
        exit(1)
    
    print("Configuration validation completed successfully!")