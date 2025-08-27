# scripts/validate_output.py
#!/usr/bin/env python3
"""Validate extractor output against schema."""

import json
import sys
from pathlib import Path
from typing import Any, Dict

from li_extractor.models import LinkedInPostsExtraction
from pydantic import ValidationError


def validate_output(file_path: Path) -> bool:
    """Validate JSON output file against schema."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate against Pydantic model
        extraction = LinkedInPostsExtraction(**data)
        
        print(f"Validation successful!")
        print(f"   Profile: {extraction.profile_url}")
        print(f"   Posts: {extraction.total_posts}")
        print(f"   Fetched: {extraction.fetched_at}")
        print(f"   Duration: {extraction.extraction_duration_seconds}s")
        
        # Additional checks
        if extraction.total_posts != len(extraction.posts):
            print("Warning: total_posts mismatch with actual posts count")
        
        # Check for missing data
        missing_fields = []
        for i, post in enumerate(extraction.posts):
            if not post.author_name:
                missing_fields.append(f"Post {i+1}: missing author_name")
            if not post.posted_at:
                missing_fields.append(f"Post {i+1}: missing posted_at")
            if not post.text:
                missing_fields.append(f"Post {i+1}: missing text")
        
        if missing_fields:
            print("Missing fields detected:")
            for field in missing_fields[:5]:  # Show first 5
                print(f"   {field}")
            if len(missing_fields) > 5:
                print(f"   ... and {len(missing_fields) - 5} more")
        
        return True
        
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return False
    except ValidationError as e:
        print(f"Schema validation failed:")
        for error in e.errors():
            print(f"   {error['loc']}: {error['msg']}")
        return False
    except Exception as e:
        print(f"Validation error: {e}")
        return False


def main():
    """Main validation function."""
    if len(sys.argv) != 2:
        print("Usage: python validate_output.py <output_file.json>")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    success = validate_output(file_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()