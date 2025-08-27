# scripts/analyze_logs.py
#!/usr/bin/env python3
"""Analyze extraction logs for insights and debugging."""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime


def analyze_logs(log_file: Path) -> None:
    """Analyze JSONL log file."""
    if not log_file.exists():
        print(f" Log file not found: {log_file}")
        return
    
    events = []
    errors = []
    metrics_data = []
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line.strip())
                    events.append(entry)
                    
                    if entry.get('level') == 'ERROR':
                        errors.append(entry)
                    
                    if 'metrics' in entry:
                        metrics_data.append(entry['metrics'])
                        
                except json.JSONDecodeError:
                    print(f"  Invalid JSON on line {line_num}")
    
    except Exception as e:
        print(f" Error reading log file: {e}")
        return
    
    print(f" Log Analysis for {log_file}")
    print(f"{'='*50}")
    
    # Basic stats
    print(f"Total log entries: {len(events)}")
    print(f"Errors: {len(errors)}")
    print(f"Entries with metrics: {len(metrics_data)}")
    
    # Event code distribution
    event_codes = [e.get('event_code') for e in events if e.get('event_code')]
    if event_codes:
        print(f"\  Event Code Distribution:")
        code_counts = Counter(event_codes)
        for code, count in code_counts.most_common():
            print(f"   {code}: {count}")
    
    # Error analysis
    if errors:
        print(f"\n Error Analysis:")
        error_messages = [e.get('message', '')[:100] for e in errors]
        error_counts = Counter(error_messages)
        for msg, count in error_counts.most_common(3):
            print(f"   {count}x: {msg}...")
    
    # Performance metrics
    if metrics_data:
        print(f"\n Performance Metrics:")
        
        # Action rates
        action_rates = [m.get('actions_per_second') for m in metrics_data if m.get('actions_per_second')]
        if action_rates:
            avg_rate = sum(action_rates) / len(action_rates)
            print(f"   Average action rate: {avg_rate:.2f} actions/sec")
        
        # Posts found
        posts_counts = [m.get('total_posts', m.get('posts_found', 0)) for m in metrics_data]
        max_posts = max(posts_counts) if posts_counts else 0
        print(f"   Max posts found: {max_posts}")
        
        # Duration data
        durations = [m.get('duration_ms') for m in metrics_data if m.get('duration_ms')]
        if durations:
            avg_duration = sum(durations) / len(durations)
            print(f"   Average action duration: {avg_duration:.2f}ms")
    
    # Timeline analysis
    print(f"\n Timeline:")
    start_time = None
    end_time = None
    
    for event in events:
        if 'ts' in event:
            try:
                ts = datetime.fromisoformat(event['ts'].replace('Z', '+00:00'))
                if start_time is None or ts < start_time:
                    start_time = ts
                if end_time is None or ts > end_time:
                    end_time = ts
            except:
                pass
    
    if start_time and end_time:
        duration = end_time - start_time
        print(f"   Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Total duration: {duration.total_seconds():.2f} seconds")
    
    # Recommendations
    print(f"\n Recommendations:")
    
    if len(errors) > 0:
        print("   - Review error messages for common issues")
    
    if event_codes:
        if 'LI102' in event_codes:  # Load timeout
            print("   - Consider increasing --max-seconds for better post coverage")
        if 'LI204' in [e.get('event_code') for e in events]:  # Field missing
            print("   - LinkedIn UI may have changed, review selectors")
    
    if metrics_data:
        action_rates = [m.get('actions_per_second', 0) for m in metrics_data]
        if action_rates and max(action_rates) > 2.0:
            print("   - Action rate seems high, consider increasing jitter")


def main():
    """Main analysis function."""
    if len(sys.argv) != 2:
        print("Usage: python analyze_logs.py <run.log>")
        sys.exit(1)
    
    log_file = Path(sys.argv[1])
    analyze_logs(log_file)


if __name__ == "__main__":
    main()