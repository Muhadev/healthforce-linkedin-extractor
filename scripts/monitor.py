# scripts/monitor.py
#!/usr/bin/env python3
"""Monitor extraction runs and send alerts."""

import json
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional


def check_extraction_health(
    output_dir: Path,
    max_age_hours: int = 24
) -> Dict[str, any]:
    """Check health of recent extractions."""
    
    health_status = {
        "status": "healthy",
        "issues": [],
        "last_run": None,
        "posts_extracted": 0,
        "error_count": 0,
        "recommendations": []
    }
    
    # Check for recent output file
    json_files = list(output_dir.glob("li_posts*.json"))
    if not json_files:
        health_status["status"] = "critical"
        health_status["issues"].append("No output files found")
        return health_status
    
    # Get most recent output
    latest_output = max(json_files, key=lambda f: f.stat().st_mtime)
    file_age = datetime.now() - datetime.fromtimestamp(latest_output.stat().st_mtime)
    
    if file_age > timedelta(hours=max_age_hours):
        health_status["status"] = "warning"
        health_status["issues"].append(f"Latest output is {file_age.total_seconds()/3600:.1f} hours old")
    
    # Parse output file
    try:
        with open(latest_output, 'r') as f:
            data = json.load(f)
            health_status["last_run"] = data.get("fetched_at")
            health_status["posts_extracted"] = data.get("total_posts", 0)
            
            if health_status["posts_extracted"] == 0:
                health_status["status"] = "warning"
                health_status["issues"].append("No posts extracted in latest run")
    
    except Exception as e:
        health_status["status"] = "critical"
        health_status["issues"].append(f"Could not parse output file: {e}")
    
    # Check log file
    log_files = list(output_dir.glob("run*.log"))
    if log_files:
        latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
        
        try:
            error_count = 0
            warning_count = 0
            
            with open(latest_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("level") == "ERROR":
                            error_count += 1
                        elif entry.get("level") == "WARNING":
                            warning_count += 1
                    except:
                        pass
            
            health_status["error_count"] = error_count
            
            if error_count > 0:
                health_status["status"] = "warning" if health_status["status"] == "healthy" else health_status["status"]
                health_status["issues"].append(f"{error_count} errors in latest run")
            
            if warning_count > 5:
                health_status["issues"].append(f"{warning_count} warnings in latest run")
                health_status["recommendations"].append("Review warnings for data quality issues")
        
        except Exception as e:
            health_status["issues"].append(f"Could not analyze log file: {e}")
    
    # Generate recommendations
    if health_status["posts_extracted"] < 5:
        health_status["recommendations"].append("Consider increasing --max-seconds for more posts")
    
    if health_status["error_count"] > 0:
        health_status["recommendations"].append("Check logs with: python scripts/analyze_logs.py out/run.log")
    
    return health_status


def send_alert(
    health_status: Dict,
    smtp_config: Dict,
    to_emails: List[str]
) -> bool:
    """Send email alert about extraction health."""
    
    if health_status["status"] == "healthy":
        return True  # No alert needed
    
    subject = f"LinkedIn Extractor Alert - {health_status['status'].upper()}"
    
    body_lines = [
        f"LinkedIn Posts Extractor Health Report",
        f"Status: {health_status['status'].upper()}",
        f"Timestamp: {datetime.now().isoformat()}",
        "",
        f"Issues Detected:",
    ]
    
    for issue in health_status["issues"]:
        body_lines.append(f"  • {issue}")
    
    if health_status["recommendations"]:
        body_lines.extend(["", "Recommendations:"])
        for rec in health_status["recommendations"]:
            body_lines.append(f"  • {rec}")
    
    body_lines.extend([
        "",
        f"Last successful run: {health_status.get('last_run', 'Unknown')}",
        f"Posts extracted: {health_status['posts_extracted']}",
        f"Errors: {health_status['error_count']}",
    ])
    
    body = "\n".join(body_lines)
    
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = smtp_config['from_email']
        msg['To'] = ', '.join(to_emails)
        
        with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
            if smtp_config.get('use_tls'):
                server.starttls()
            if smtp_config.get('username'):
                server.login(smtp_config['username'], smtp_config['password'])
            
            server.send_message(msg)
        
        print(f" Alert sent to {len(to_emails)} recipients")
        return True
        
    except Exception as e:
        print(f" Failed to send alert: {e}")
        return False


def main():
    """Main monitoring function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor extraction health")
    parser.add_argument("--output-dir", type=Path, default="out",
                       help="Output directory to monitor")
    parser.add_argument("--max-age-hours", type=int, default=24,
                       help="Maximum age for output files in hours")
    parser.add_argument("--config", type=Path,
                       help="Configuration file for email alerts")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Check extraction health
    health_status = check_extraction_health(args.output_dir, args.max_age_hours)
    
    # Print status
    status_emoji = {
        "healthy": "✅",
        "warning": "⚠️",
        "critical": "❌"
    }
    
    emoji = status_emoji.get(health_status["status"], "")
    print(f"{emoji} Status: {health_status['status'].upper()}")
    
    if health_status["issues"]:
        print("Issues:")
        for issue in health_status["issues"]:
            print(f"  • {issue}")
    
    if health_status["recommendations"]:
        print("Recommendations:")
        for rec in health_status["recommendations"]:
            print(f"  • {rec}")
    
    if args.verbose:
        print(f"\nDetails:")
        print(f"  Last run: {health_status.get('last_run', 'Unknown')}")
        print(f"  Posts extracted: {health_status['posts_extracted']}")
        print(f"  Errors: {health_status['error_count']}")
    
    # Send email alert if configured
    if args.config and args.config.exists():
        try:
            with open(args.config) as f:
                config = json.load(f)
            
            if 'smtp' in config and 'alerts' in config:
                send_alert(health_status, config['smtp'], config['alerts']['to_emails'])
        
        except Exception as e:
            print(f"  Could not send alert: {e}")
    
    # Exit with appropriate code
    exit_codes = {"healthy": 0, "warning": 1, "critical": 2}
    sys.exit(exit_codes.get(health_status["status"], 1))


if __name__ == "__main__":
    main()