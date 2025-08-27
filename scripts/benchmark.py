# scripts/benchmark.py
#!/usr/bin/env python3
"""Benchmark extraction performance across different profiles."""

import asyncio
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from li_extractor.browser import BrowserManager
from li_extractor.logging_ import StructuredLogger
from li_extractor.navigator import LinkedInNavigator


async def benchmark_profile(
    profile_url: str,
    min_posts: int,
    max_seconds: int,
    storage_state: Path,
    logger: StructuredLogger
) -> Dict:
    """Benchmark extraction for a single profile."""
    
    start_time = time.time()
    browser_manager = None
    
    try:
        browser_manager = BrowserManager(logger)
        navigator = LinkedInNavigator(logger)
        
        # Start browser
        page = await browser_manager.start_browser(storage_state, headless=True)
        
        # Navigate to posts
        nav_start = time.time()
        nav_success = await navigator.navigate_to_posts(page, profile_url)
        nav_time = time.time() - nav_start
        
        if not nav_success:
            return {
                "profile_url": profile_url,
                "success": False,
                "error": "Navigation failed",
                "total_time": time.time() - start_time
            }
        
        # Load posts
        load_start = time.time()
        post_elements = await navigator.load_posts(page, min_posts, max_seconds)
        load_time = time.time() - load_start
        
        # Extract data
        extract_start = time.time()
        posts_data = await navigator.extract_posts_data(post_elements, page)
        extract_time = time.time() - extract_start
        
        total_time = time.time() - start_time
        
        # Get action metrics
        action_metrics = navigator.action_tracker.get_metrics()
        
        return {
            "profile_url": profile_url,
            "success": True,
            "total_time": total_time,
            "navigation_time": nav_time,
            "loading_time": load_time,
            "extraction_time": extract_time,
            "posts_found": len(post_elements),
            "posts_extracted": len(posts_data),
            "action_metrics": action_metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "profile_url": profile_url,
            "success": False,
            "error": str(e),
            "total_time": time.time() - start_time
        }
    
    finally:
        if browser_manager:
            await browser_manager.close()


async def run_benchmark(
    profiles: List[str],
    min_posts: int = 10,
    max_seconds: int = 60,
    output_dir: Path = Path("benchmark"),
    storage_state: Path = Path("out/session/storage.json")
) -> None:
    """Run benchmark across multiple profiles."""
    
    output_dir.mkdir(exist_ok=True)
    log_file = output_dir / f"benchmark_{int(time.time())}.log"
    results_file = output_dir / f"benchmark_{int(time.time())}.json"
    
    logger = StructuredLogger("benchmark", log_file, "INFO")

    print(f" Starting benchmark with {len(profiles)} profiles")
    print(f" Results will be saved to: {results_file}")
    
    results = []
    
    for i, profile_url in enumerate(profiles, 1):
        print(f"\n [{i}/{len(profiles)}] Benchmarking: {profile_url}")
        
        result = await benchmark_profile(
            profile_url, min_posts, max_seconds, storage_state, logger
        )
        
        results.append(result)
        
        if result["success"]:
            print(f"    Success: {result['posts_extracted']} posts in {result['total_time']:.2f}s")
        else:
            print(f"    Failed: {result['error']}")
        
        # Small delay between profiles
        await asyncio.sleep(2)
    
    # Calculate summary statistics
    successful_results = [r for r in results if r["success"]]
    
    if successful_results:
        total_times = [r["total_time"] for r in successful_results]
        posts_counts = [r["posts_extracted"] for r in successful_results]
        
        summary = {
            "benchmark_timestamp": datetime.now().isoformat(),
            "total_profiles": len(profiles),
            "successful_profiles": len(successful_results),
            "success_rate": len(successful_results) / len(profiles),
            "performance_stats": {
                "avg_total_time": statistics.mean(total_times),
                "median_total_time": statistics.median(total_times),
                "min_total_time": min(total_times),
                "max_total_time": max(total_times),
                "avg_posts_extracted": statistics.mean(posts_counts),
                "total_posts_extracted": sum(posts_counts)
            },
            "individual_results": results
        }
    else:
        summary = {
            "benchmark_timestamp": datetime.now().isoformat(),
            "total_profiles": len(profiles),
            "successful_profiles": 0,
            "success_rate": 0.0,
            "error": "No successful extractions",
            "individual_results": results
        }
    
    # Save results
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print summary
    print(f"\n Benchmark Summary:")
    print(f"   Profiles tested: {summary['total_profiles']}")
    print(f"   Success rate: {summary['success_rate']:.2%}")
    
    if successful_results:
        stats = summary["performance_stats"]
        print(f"   Average time: {stats['avg_total_time']:.2f}s")
        print(f"   Average posts: {stats['avg_posts_extracted']:.1f}")
        print(f"   Total posts extracted: {stats['total_posts_extracted']}")
    
    print(f"\n Detailed results saved to: {results_file}")


def main():
    """Main benchmark function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark LinkedIn extraction")
    parser.add_argument("profiles", nargs="+", help="LinkedIn profile URLs to benchmark")
    parser.add_argument("--min-posts", type=int, default=10, help="Minimum posts per profile")
    parser.add_argument("--max-seconds", type=int, default=60, help="Maximum time per profile")
    parser.add_argument("--output-dir", type=Path, default="benchmark", help="Output directory")
    parser.add_argument("--storage-state", type=Path, default="out/session/storage.json", 
                       help="Browser storage state file")
    
    args = parser.parse_args()
    
    # Validate profile URLs
    valid_profiles = []
    for url in args.profiles:
        if "linkedin.com/in/" in url:
            valid_profiles.append(url)
        else:
            print(f"  Skipping invalid profile URL: {url}")
    
    if not valid_profiles:
        print(" No valid LinkedIn profile URLs provided")
        sys.exit(1)
    
    # Check storage state
    if not args.storage_state.exists():
        print(f" Storage state not found: {args.storage_state}")
        print("  Run a regular extraction first to create session")
        sys.exit(1)
    
    # Run benchmark
    try:
        asyncio.run(run_benchmark(
            profiles=valid_profiles,
            min_posts=args.min_posts,
            max_seconds=args.max_seconds,
            output_dir=args.output_dir,
            storage_state=args.storage_state
        ))
    except KeyboardInterrupt:
        print("\n Benchmark cancelled by user")
        sys.exit(1)


if __name__ == "__main__":
    main()