# tests/test_models.py
"""Tests for Pydantic models."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from li_extractor.models import LinkedInPost, LinkedInPostsExtraction


class TestLinkedInPost:
    """Test cases for LinkedInPost model."""
    
    def test_valid_post(self):
        """Test valid post creation."""
        post_data = {
            'post_id': 'test-123',
            'author_name': 'John Doe',
            'posted_at': datetime.now(timezone.utc),
            'text': 'Great insights on #AI and #MachineLearning!',
            'hashtags': ['AI', 'MachineLearning'],
            'links': ['https://example.com'],
            'reactions_count': 42,
            'comments_count': 5,
        }
        
        post = LinkedInPost(**post_data)
        
        assert post.post_id == 'test-123'
        assert post.author_name == 'John Doe'
        assert post.hashtags == ['ai', 'machinelearning']
        assert post.reactions_count == 42
    
    def test_minimal_post(self):
        """Test post with minimal required data."""
        post = LinkedInPost(post_id='test-123')
        
        assert post.post_id == 'test-123'
        assert post.author_name is None
        assert post.hashtags == []
        assert post.links == []
    
    def test_hashtag_normalization(self):
        """Test hashtag normalization."""
        test_cases = [
            (['AI', 'ML', 'Tech'], ['ai', 'ml', 'tech']),
            (['#hashtag', 'NoHash'], ['hashtag', 'nohash']),
            (['Duplicate', 'duplicate', 'DUPLICATE'], ['duplicate']),
            ('single_string', ['single_string']),  # String input
        ]
        
        for input_tags, expected in test_cases:
            post = LinkedInPost(post_id='test', hashtags=input_tags)
            assert post.hashtags == expected
    
    def test_links_validation(self):
        """Test links validation."""
        valid_links = [
            'https://example.com',
            'http://test.org',
            'https://github.com/user/repo'
        ]
        
        post = LinkedInPost(post_id='test', links=valid_links)
        assert len(post.links) == 3
        
        # Test deduplication
        duplicate_links = valid_links + ['https://example.com']
        post = LinkedInPost(post_id='test', links=duplicate_links)
        assert len(post.links) == 3
    
    def test_negative_counts(self):
        """Test validation of negative counts."""
        with pytest.raises(ValidationError):
            LinkedInPost(post_id='test', reactions_count=-1)
        
        with pytest.raises(ValidationError):
            LinkedInPost(post_id='test', comments_count=-5)
    
    def test_missing_post_id(self):
        """Test validation fails without post_id."""
        with pytest.raises(ValidationError):
            LinkedInPost()


class TestLinkedInPostsExtraction:
    """Test cases for LinkedInPostsExtraction model."""
    
    def test_valid_extraction(self):
        """Test valid extraction result."""
        posts = [
            LinkedInPost(post_id='1', author_name='User 1'),
            LinkedInPost(post_id='2', author_name='User 2'),
        ]
        
        extraction = LinkedInPostsExtraction(
            profile_url='https://linkedin.com/in/test/',
            fetched_at=datetime.now(timezone.utc),
            total_posts=2,
            posts=posts
        )
        
        assert extraction.total_posts == 2
        assert len(extraction.posts) == 2
    
    def test_total_posts_sync(self):
        """Test total_posts syncs with actual posts count."""
        posts = [LinkedInPost(post_id='1'), LinkedInPost(post_id='2')]
        
        # Even if we provide wrong total_posts, it should sync
        extraction = LinkedInPostsExtraction(
            profile_url='https://linkedin.com/in/test/',
            fetched_at=datetime.now(timezone.utc),
            total_posts=10,  # Wrong count
            posts=posts
        )
        
        assert extraction.total_posts == 2  # Should be corrected
    
    def test_empty_posts(self):
        """Test extraction with no posts."""
        extraction = LinkedInPostsExtraction(
            profile_url='https://linkedin.com/in/test/',
            fetched_at=datetime.now(timezone.utc),
            total_posts=0,
            posts=[]
        )
        
        assert extraction.total_posts == 0
        assert extraction.posts == []
    
    def test_json_schema_export(self):
        """Test JSON schema generation."""
        schema = LinkedInPostsExtraction.get_json_schema()
        
        assert '$schema' in schema
        assert 'properties' in schema
        assert 'profile_url' in schema['properties']
        assert 'posts' in schema['properties']
    
    def test_required_fields(self):
        """Test required fields validation."""
        with pytest.raises(ValidationError):
            LinkedInPostsExtraction()  # Missing required fields
        
        # Should work with minimal required fields
        extraction = LinkedInPostsExtraction(
            profile_url='https://linkedin.com/in/test/',
            fetched_at=datetime.now(timezone.utc),
            total_posts=0
        )
        assert extraction.posts == []