import pytest
import json
import os
import tempfile
from unittest.mock import patch, mock_open, MagicMock
from auth import authenticate_gmail, SCOPES


class TestAuthenticateGmail:
    """Test the Gmail authentication function."""
    
    def test_authenticate_gmail_with_valid_token(self):
        """Test authentication with valid existing token."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_service = MagicMock()
        
        token_data = {
            "token": "test_token",
            "refresh_token": "test_refresh",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret"
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(token_data))):
                with patch('auth.Credentials.from_authorized_user_info', return_value=mock_creds):
                    with patch('auth.build', return_value=mock_service):
                        service = authenticate_gmail()
                        
                        assert service == mock_service
                        # Should not write new token since creds are valid
                        mock_creds.refresh.assert_not_called()
    
    def test_authenticate_gmail_with_expired_token_refresh_success(self):
        """Test authentication with expired token that can be refreshed."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "test_refresh_token"
        mock_creds.to_json.return_value = '{"token": "refreshed_token"}'
        mock_service = MagicMock()
        
        token_data = {
            "token": "expired_token",
            "refresh_token": "test_refresh_token"
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(token_data))):
                with patch('auth.Credentials.from_authorized_user_info', return_value=mock_creds):
                    with patch('auth.Request'):
                        with patch('auth.build', return_value=mock_service):
                            service = authenticate_gmail()
                            
                            assert service == mock_service
                            mock_creds.refresh.assert_called_once()
    
    def test_authenticate_gmail_with_expired_token_refresh_failure(self):
        """Test authentication with expired token that cannot be refreshed."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "test_refresh_token"
        mock_creds.refresh.side_effect = Exception("Refresh failed")
        
        token_data = {
            "token": "expired_token",
            "refresh_token": "test_refresh_token"
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(token_data))):
                with patch('auth.Credentials.from_authorized_user_info', return_value=mock_creds):
                    with patch('auth.Request'):
                        with patch('builtins.print') as mock_print:
                            with pytest.raises(Exception, match="Refresh failed"):
                                authenticate_gmail()
                            
                            # Check that error message was printed
                            mock_print.assert_called()
                            assert "Error refreshing credentials" in mock_print.call_args_list[0][0][0]
                            assert "Delete token.json and reauthenticate" in mock_print.call_args_list[1][0][0]
    
    def test_authenticate_gmail_no_existing_token(self):
        """Test authentication when no token file exists."""
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "new_token"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_service = MagicMock()
        
        with patch('os.path.exists', return_value=False):
            with patch('auth.InstalledAppFlow.from_client_secrets_file', return_value=mock_flow):
                with patch('builtins.open', mock_open()) as mock_file:
                    with patch('auth.build', return_value=mock_service):
                        service = authenticate_gmail()
                        
                        assert service == mock_service
                        mock_flow.run_local_server.assert_called_once_with(port=0)
                        # Check that token was saved
                        mock_file.assert_called_with('token.json', 'w')
    
    def test_authenticate_gmail_corrupted_token_file(self):
        """Test authentication with corrupted token file."""
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='invalid json')):
                with patch('auth.Credentials.from_authorized_user_info', side_effect=Exception("Invalid JSON")):
                    with patch('builtins.print') as mock_print:
                        with pytest.raises(Exception, match="Invalid JSON"):
                            authenticate_gmail()
                        
                        # Check that error message was printed
                        mock_print.assert_called()
                        assert "Error loading credentials from token.json" in mock_print.call_args_list[0][0][0]
                        assert "Delete token.json and reauthenticate" in mock_print.call_args_list[1][0][0]
    
    def test_authenticate_gmail_missing_credentials_file(self):
        """Test authentication when credentials.json is missing."""
        with patch('os.path.exists', return_value=False):
            with patch('auth.InstalledAppFlow.from_client_secrets_file', side_effect=FileNotFoundError("credentials.json not found")):
                with pytest.raises(FileNotFoundError, match="credentials.json not found"):
                    authenticate_gmail()
    
    def test_authenticate_gmail_invalid_credentials_file(self):
        """Test authentication with invalid credentials.json."""
        with patch('os.path.exists', return_value=False):
            with patch('auth.InstalledAppFlow.from_client_secrets_file', side_effect=Exception("Invalid credentials format")):
                with pytest.raises(Exception, match="Invalid credentials format"):
                    authenticate_gmail()
    
    def test_authenticate_gmail_new_credentials_flow(self):
        """Test complete new authentication flow."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = False
        mock_creds.refresh_token = None
        
        mock_new_creds = MagicMock()
        mock_new_creds.to_json.return_value = '{"token": "new_token"}'
        
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_new_creds
        mock_service = MagicMock()
        
        token_data = {
            "token": "invalid_token",
            "refresh_token": None
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(token_data))):
                with patch('auth.Credentials.from_authorized_user_info', return_value=mock_creds):
                    with patch('auth.InstalledAppFlow.from_client_secrets_file', return_value=mock_flow):
                        with patch('auth.build', return_value=mock_service):
                            service = authenticate_gmail()
                            
                            assert service == mock_service
                            mock_flow.run_local_server.assert_called_once_with(port=0)
    
    def test_authenticate_gmail_scope_configuration(self):
        """Test that correct scopes are used."""
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "new_token"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_service = MagicMock()
        
        with patch('os.path.exists', return_value=False):
            with patch('auth.InstalledAppFlow.from_client_secrets_file', return_value=mock_flow) as mock_flow_create:
                with patch('builtins.open', mock_open()):
                    with patch('auth.build', return_value=mock_service):
                        authenticate_gmail()
                        
                        # Check that correct scopes were used
                        mock_flow_create.assert_called_once_with('credentials.json', SCOPES)
    
    def test_authenticate_gmail_service_creation(self):
        """Test that Gmail service is created with correct parameters."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_service = MagicMock()
        
        token_data = {"token": "test_token"}
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(token_data))):
                with patch('auth.Credentials.from_authorized_user_info', return_value=mock_creds):
                    with patch('auth.build', return_value=mock_service) as mock_build:
                        service = authenticate_gmail()
                        
                        assert service == mock_service
                        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)
    
    def test_authenticate_gmail_token_file_permissions(self):
        """Test that token file is written with appropriate content."""
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "new_token", "refresh_token": "refresh"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_service = MagicMock()
        
        with patch('os.path.exists', return_value=False):
            with patch('auth.InstalledAppFlow.from_client_secrets_file', return_value=mock_flow):
                with patch('builtins.open', mock_open()) as mock_file:
                    with patch('auth.build', return_value=mock_service):
                        authenticate_gmail()
                        
                        # Check that token was written to file
                        mock_file.assert_called_with('token.json', 'w')
                        handle = mock_file.return_value.__enter__.return_value
                        handle.write.assert_called_once_with('{"token": "new_token", "refresh_token": "refresh"}')
    
    def test_authenticate_gmail_file_paths(self):
        """Test that correct file paths are used."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_service = MagicMock()
        
        token_data = {"token": "test_token"}
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('builtins.open', mock_open(read_data=json.dumps(token_data))):
                with patch('auth.Credentials.from_authorized_user_info', return_value=mock_creds):
                    with patch('auth.build', return_value=mock_service):
                        authenticate_gmail()
                        
                        # Check that correct file path was checked
                        mock_exists.assert_called_with('token.json')
    
    def test_authenticate_gmail_local_server_port(self):
        """Test that local server is started with correct port configuration."""
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "new_token"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_service = MagicMock()
        
        with patch('os.path.exists', return_value=False):
            with patch('auth.InstalledAppFlow.from_client_secrets_file', return_value=mock_flow):
                with patch('builtins.open', mock_open()):
                    with patch('auth.build', return_value=mock_service):
                        authenticate_gmail()
                        
                        # Check that port=0 was used (allows system to choose available port)
                        mock_flow.run_local_server.assert_called_once_with(port=0)


class TestScopesConfiguration:
    """Test the scopes configuration."""
    
    def test_scopes_readonly_only(self):
        """Test that only readonly scope is configured."""
        assert SCOPES == ['https://www.googleapis.com/auth/gmail.readonly']
        assert len(SCOPES) == 1
        assert 'readonly' in SCOPES[0]
    
    def test_scopes_format(self):
        """Test that scopes are properly formatted."""
        for scope in SCOPES:
            assert scope.startswith('https://www.googleapis.com/auth/')
            assert isinstance(scope, str)
            assert len(scope) > 0


class TestIntegration:
    """Integration-like tests for authentication flow."""
    
    def test_full_authentication_flow_new_user(self):
        """Test complete authentication flow for new user."""
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "new_token"}'
        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_service = MagicMock()
        
        with patch('os.path.exists', return_value=False):
            with patch('auth.InstalledAppFlow.from_client_secrets_file', return_value=mock_flow):
                with patch('builtins.open', mock_open()) as mock_file:
                    with patch('auth.build', return_value=mock_service):
                        service = authenticate_gmail()
                        
                        # Verify complete flow
                        assert service == mock_service
                        mock_flow.run_local_server.assert_called_once()
                        mock_file.assert_called_with('token.json', 'w')
    
    def test_full_authentication_flow_returning_user(self):
        """Test complete authentication flow for returning user."""
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_service = MagicMock()
        
        token_data = {"token": "existing_token"}
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(token_data))):
                with patch('auth.Credentials.from_authorized_user_info', return_value=mock_creds):
                    with patch('auth.build', return_value=mock_service):
                        service = authenticate_gmail()
                        
                        # Verify streamlined flow for returning user
                        assert service == mock_service
                        # Should not create new flow since creds are valid
                        mock_creds.refresh.assert_not_called()
    
    def test_error_handling_chain(self):
        """Test that error handling provides helpful guidance."""
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "test_refresh"
        mock_creds.refresh.side_effect = Exception("Token refresh failed")
        
        token_data = {"token": "expired_token", "refresh_token": "test_refresh"}
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(token_data))):
                with patch('auth.Credentials.from_authorized_user_info', return_value=mock_creds):
                    with patch('auth.Request'):
                        with patch('builtins.print') as mock_print:
                            with pytest.raises(Exception):
                                authenticate_gmail()
                            
                            # Verify helpful error messages
                            print_calls = [call[0][0] for call in mock_print.call_args_list]
                            assert any("Error refreshing credentials" in msg for msg in print_calls)
                            assert any("Delete token.json and reauthenticate" in msg for msg in print_calls)