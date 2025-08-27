# scripts/cleanup.py
#!/usr/bin/env python3
"""Cleanup old extraction artifacts."""

import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path


def cleanup_artifacts(
    output_dir: Path,
    days_to_keep: int = 7,
    keep_sessions: bool = True,
    dry_run: bool = False
) -> None:
    """Clean up old extraction artifacts."""
    
    if not output_dir.exists():
        print(f" Output directory not found: {output_dir}")
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    print(f" Cleaning files older than {cutoff_date.strftime('%Y-%m-%d')}")
    
    files_removed = 0
    bytes_freed = 0
    
    # Clean log files
    for log_file in output_dir.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_date.timestamp():
            size = log_file.stat().st_size
            print(f"     Remove log: {log_file.name} ({size} bytes)")
            
            if not dry_run:
                log_file.unlink()
            
            files_removed += 1
            bytes_freed += size
    
    # Clean JSON outputs (keep latest few)
    json_files = list(output_dir.glob("*.json"))
    json_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    # Keep latest 3 JSON files, remove older ones
    for json_file in json_files[3:]:
        if json_file.stat().st_mtime < cutoff_date.timestamp():
            size = json_file.stat().st_size
            print(f"     Remove JSON: {json_file.name} ({size} bytes)")
            
            if not dry_run:
                json_file.unlink()
            
            files_removed += 1
            bytes_freed += size
    
    # Clean session files (optional)
    if not keep_sessions:
        session_dir = output_dir / "session"
        if session_dir.exists():
            for session_file in session_dir.rglob("*"):
                if session_file.is_file() and session_file.stat().st_mtime < cutoff_date.timestamp():
                    size = session_file.stat().st_size
                    print(f"     Remove session: {session_file.name} ({size} bytes)")
                    
                    if not dry_run:
                        session_file.unlink()
                    
                    files_removed += 1
                    bytes_freed += size
    
    # Clean cache directories
    cache_dirs = [
        output_dir / "__pycache__",
        output_dir / ".pytest_cache",
        output_dir / ".mypy_cache",
    ]
    
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
            print(f"     Remove cache: {cache_dir.name}/ ({size} bytes)")
            
            if not dry_run:
                shutil.rmtree(cache_dir)
            
            files_removed += 1
            bytes_freed += size
    
    print(f"\n Cleanup Summary:")
    print(f"   Files removed: {files_removed}")
    print(f"   Bytes freed: {bytes_freed:,} ({bytes_freed/1024/1024:.2f} MB)")
    
    if dry_run:
        print("   (Dry run - no files were actually deleted)")


def main():
    """Main cleanup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up extraction artifacts")
    parser.add_argument("output_dir", type=Path, default="out", nargs="?", 
                       help="Output directory to clean (default: out)")
    parser.add_argument("--days", type=int, default=7,
                       help="Keep files newer than N days (default: 7)")
    parser.add_argument("--remove-sessions", action="store_true",
                       help="Also remove old session files")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be deleted without actually deleting")
    
    args = parser.parse_args()
    
    cleanup_artifacts(
        output_dir=args.output_dir,
        days_to_keep=args.days,
        keep_sessions=not args.remove_sessions,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()