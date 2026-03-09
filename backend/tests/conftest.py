"""
Pytest configuration and fixtures
"""
import sys
import os
from unittest.mock import MagicMock
import pytest

# Set required environment variables for testing
os.environ.setdefault('OPENAI_API_KEY', 'test-key-for-testing')
os.environ.setdefault('CHROMA_API_KEY', 'test-chroma-key')
os.environ.setdefault('CHROMA_TENANT', 'test-tenant')
os.environ.setdefault('CHROMA_DATABASE', 'test-db')

# Mock chromadb before any imports to avoid initialization issues
chromadb_mock = MagicMock()
chromadb_mock.config.Settings = MagicMock
sys.modules['chromadb'] = chromadb_mock
sys.modules['chromadb.config'] = chromadb_mock.config


@pytest.fixture(scope="session", autouse=True)
def mock_chromadb():
    """Mock chromadb for all tests to avoid initialization issues"""
    return chromadb_mock
