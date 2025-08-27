# tests/test_output.py
"""Tests for output generation and validation."""

import json
import pytest
from datetime import datetime, timezone

from li_extractor.output import OutputManager
from li_extractor.models import LinkedInPost


class TestOutputManager:
    """Test cases for OutputManager."""
    
    def test_write_results_success(self, mock_logger, temp_output_dir, sample_post_data):
        """Test successful results writing."""
        manager = OutputManager(mock_logger)
        output_file = temp_output_dir / "test_output.json"
        
        success = manager.write_results(
            posts_data=[sample_post_data],
            profile_url="https://linkedin.com/in/test/",
            output_path=output_file,
            extraction_duration=45.5,
            reason="completed"
        )
        
        assert success
        assert output_file.exists()
        
        # Verify content
        with open(output_file) as f:
            data = json.load(f)
        
        assert data["profile_url"] == "https://linkedin.com/in/test/"
        assert data["total_posts"] == 1
        assert len(data["posts"]) == 1
        assert data["extraction_duration_seconds"] == 45.5
        assert data["reason"] == "completed"
    
    def test_write_results_validation_errors(self, mock_logger, temp_output_dir):
        """Test handling of validation errors."""
        manager = OutputManager(mock_logger)
        output_file = temp_output_dir / "test_output.json"
        
        # Invalid post data (negative reaction count)
        invalid_post = {
            "post_id": "test",
            "reactions_count": -5  # Invalid
        }
        
        success = manager.write_results(
            posts_data=[invalid_post],
            profile_url="https://linkedin.com/in/test/",
            output_path=output_file,
            extraction_duration=10.0
        )
        
        # Should still succeed but with fewer posts
        assert success
        
        with open(output_file) as f:
            data = json.load(f)
        
        assert data["total_posts"] == 0  # Invalid post filtered out
    
    def test_export_schema(self, mock_logger, temp_output_dir):
        """Test JSON schema export."""
        manager = OutputManager(mock_logger)
        schema_file = temp_output_dir / "schema.json"
        
        success = manager.export_schema(schema_file)
        
        assert success
        assert schema_file.exists()
        
        with open(schema_file) as f:
            schema = json.load(f)
        
        assert "$schema" in schema
        assert "properties" in schema
        assert "profile_url" in schema["properties"]