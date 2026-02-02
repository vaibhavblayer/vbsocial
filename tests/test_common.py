"""Tests for common utilities."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from vbsocial.common.config import save_json, load_json, ensure_dir
from vbsocial.common.auth import TokenManager, ConfigManager
from vbsocial.common.http import create_session, with_retry


class TestConfig:
    """Tests for config utilities."""
    
    def test_save_and_load_json(self, tmp_path):
        """Test saving and loading JSON files."""
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "number": 42}
        
        save_json(test_file, test_data)
        
        assert test_file.exists()
        loaded = load_json(test_file)
        assert loaded == test_data
    
    def test_load_json_not_found(self, tmp_path):
        """Test loading non-existent file returns None."""
        result = load_json(tmp_path / "nonexistent.json")
        assert result is None
    
    def test_ensure_dir_creates_directory(self, tmp_path):
        """Test directory creation."""
        new_dir = tmp_path / "new" / "nested" / "dir"
        ensure_dir(new_dir)
        assert new_dir.exists()


class TestTokenManager:
    """Tests for TokenManager."""
    
    def test_is_expired_no_expiry(self):
        """Token without expiry is not expired."""
        manager = TokenManager("test")
        token = {"access_token": "abc123"}
        assert not manager.is_expired(token)
    
    def test_is_expired_future(self):
        """Token with future expiry is not expired."""
        import time
        manager = TokenManager("test")
        token = {
            "access_token": "abc123",
            "expires_at": time.time() + 3600,  # 1 hour from now
        }
        assert not manager.is_expired(token)
    
    def test_is_expired_past(self):
        """Token with past expiry is expired."""
        import time
        manager = TokenManager("test")
        token = {
            "access_token": "abc123",
            "expires_at": time.time() - 3600,  # 1 hour ago
        }
        assert manager.is_expired(token)


class TestHttpSession:
    """Tests for HTTP utilities."""
    
    def test_create_session(self):
        """Test session creation."""
        session = create_session()
        assert session is not None
        # Check retry adapter is mounted
        assert "https://" in session.adapters
    
    def test_with_retry_success(self):
        """Test retry decorator on successful function."""
        call_count = 0
        
        @with_retry(max_attempts=3, delay=0.01)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_func()
        assert result == "success"
        assert call_count == 1
    
    def test_with_retry_eventual_success(self):
        """Test retry decorator with eventual success."""
        call_count = 0
        
        @with_retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert call_count == 3
    
    def test_with_retry_all_fail(self):
        """Test retry decorator when all attempts fail."""
        call_count = 0
        
        @with_retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("permanent error")
        
        with pytest.raises(ValueError):
            always_fails()
        
        assert call_count == 3
