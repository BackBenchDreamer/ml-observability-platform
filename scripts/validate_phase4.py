#!/usr/bin/env python3
"""
Quick Phase 4 Validation Script
Performs lightweight checks on drift-service deployment
"""

import sys
import time
import re
import requests
import redis
from typing import Dict, Tuple, Optional

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
DRIFT_SERVICE_URL = 'http://localhost:8000'
STREAM_NAME = 'ml-events'
CONSUMER_GROUP = 'drift-detector'
TIMEOUT = 5


def print_status(check_name: str, passed: bool, message: str = ""):
    """Print check status with color"""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {check_name}")
    if message:
        print(f"      {message}")


def print_warning(check_name: str, message: str):
    """Print warning status"""
    print(f"{YELLOW}⚠ WARN{RESET} - {check_name}")
    if message:
        print(f"      {message}")


def check_redis_connection() -> Tuple[bool, Optional[redis.Redis]]:
    """Check 1: Redis connection and stream"""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        
        # Check if stream exists
        stream_length = r.xlen(STREAM_NAME)
        print_status("Redis Connection", True, f"Stream {STREAM_NAME} exists with {stream_length} events")
        
        return True, r
    except redis.ConnectionError as e:
        print_status("Redis Connection", False, f"Failed to connect: {e}")
        return False, None
    except Exception as e:
        print_status("Redis Connection", False, f"Error: {e}")
        return False, None


def check_consumer_group(r: redis.Redis) -> bool:
    """Check consumer group exists"""
    try:
        groups = r.xinfo_groups(STREAM_NAME)
        group_names = [g['name'] for g in groups]
        
        if CONSUMER_GROUP in group_names:
            print_status("Consumer Group", True, f"{CONSUMER_GROUP} group exists")
            return True
        else:
            print_status("Consumer Group", False, f"{CONSUMER_GROUP} group not found")
            return False
    except Exception as e:
        print_status("Consumer Group", False, f"Error: {e}")
        return False


def check_drift_service_health() -> bool:
    """Check 2: Drift service health endpoint"""
    try:
        response = requests.get(f"{DRIFT_SERVICE_URL}/health", timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                print_status("Drift Service Health", True, "Service is healthy")
                return True
            else:
                print_status("Drift Service Health", False, f"Unhealthy status: {data}")
                return False
        else:
            print_status("Drift Service Health", False, f"HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_status("Drift Service Health", False, "Cannot connect to service")
        return False
    except Exception as e:
        print_status("Drift Service Health", False, f"Error: {e}")
        return False


def parse_prometheus_metrics(text: str) -> Dict[str, float]:
    """Parse Prometheus text format metrics"""
    metrics = {}
    
    # Pattern to match metric lines (not comments or empty lines)
    pattern = r'^([a-zA-Z_:][a-zA-Z0-9_:]*(?:\{[^}]*\})?) ([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)'
    
    for line in text.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            match = re.match(pattern, line)
            if match:
                metric_name = match.group(1)
                metric_value = float(match.group(2))
                # Store without labels for simplicity
                base_name = metric_name.split('{')[0]
                metrics[base_name] = metric_value
    
    return metrics


def check_metrics_endpoint() -> Tuple[bool, Dict]:
    """Check 3: Metrics endpoint and key metrics"""
    try:
        response = requests.get(f"{DRIFT_SERVICE_URL}/metrics", timeout=TIMEOUT)
        
        if response.status_code != 200:
            print_status("Metrics Endpoint", False, f"HTTP {response.status_code}")
            return False, {}
        
        metrics = parse_prometheus_metrics(response.text)
        
        # Check for key metrics
        expected_metrics = [
            'events_processed_total',
            'drift_score_feature_1',
            'drift_score_feature_2',
            'drift_score_feature_3',
            'baseline_window_status',
            'sliding_window_status'
        ]
        
        missing_metrics = [m for m in expected_metrics if m not in metrics]
        
        if not missing_metrics:
            print_status("Metrics Endpoint", True, "All key metrics present")
            return True, metrics
        else:
            print_status("Metrics Endpoint", False, f"Missing metrics: {', '.join(missing_metrics)}")
            return False, metrics
    except requests.exceptions.ConnectionError:
        print_status("Metrics Endpoint", False, "Cannot connect to service")
        return False, {}
    except Exception as e:
        print_status("Metrics Endpoint", False, f"Error: {e}")
        return False, {}


def check_consumption_rate(initial_metrics: Dict) -> Tuple[bool, float]:
    """Check 4: Event consumption rate"""
    try:
        initial_count = initial_metrics.get('events_processed_total', 0)
        
        # Wait 5 seconds
        time.sleep(5)
        
        # Get metrics again
        response = requests.get(f"{DRIFT_SERVICE_URL}/metrics", timeout=TIMEOUT)
        if response.status_code != 200:
            print_status("Consumption Rate", False, "Cannot fetch metrics")
            return False, 0.0
        
        final_metrics = parse_prometheus_metrics(response.text)
        final_count = final_metrics.get('events_processed_total', 0)
        
        # Calculate rate
        delta = final_count - initial_count
        rate = delta / 5.0
        
        if rate > 0:
            print_status("Consumption Rate", True, f"Processing {rate:.1f} events/sec")
            return True, rate
        else:
            print_status("Consumption Rate", False, "No events being processed")
            return False, 0.0
    except Exception as e:
        print_status("Consumption Rate", False, f"Error: {e}")
        return False, 0.0


def check_consumer_lag(r: redis.Redis) -> Tuple[bool, int]:
    """Check 5: Consumer group lag"""
    try:
        # Get pending messages count
        pending_info = r.xpending(STREAM_NAME, CONSUMER_GROUP)
        pending_count = pending_info['pending']
        
        if pending_count == 0:
            print_status("Consumer Lag", True, "0 pending messages")
            return True, 0
        elif pending_count < 100:
            print_warning("Consumer Lag", f"{pending_count} pending messages (acceptable)")
            return True, pending_count
        else:
            print_status("Consumer Lag", False, f"{pending_count} pending messages (high lag)")
            return False, pending_count
    except Exception as e:
        print_status("Consumer Lag", False, f"Error: {e}")
        return False, -1


def check_memory_usage() -> Tuple[bool, str]:
    """Check 6: Basic memory check using docker stats"""
    try:
        import subprocess
        
        # Try to get memory usage from docker stats
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format', '{{.Name}}\t{{.MemUsage}}', 'drift-service'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout:
            output = result.stdout.strip()
            if output:
                parts = output.split('\t')
                if len(parts) >= 2:
                    mem_usage = parts[1]
                    print_warning("Memory Usage", f"Using {mem_usage}")
                    return True, mem_usage
        
        # If docker command fails, skip memory check
        print_warning("Memory Usage", "Cannot check (docker not available or container not running)")
        return True, "N/A"
    except Exception as e:
        print_warning("Memory Usage", f"Cannot check: {e}")
        return True, "N/A"


def main():
    """Run all validation checks"""
    print("\n" + "="*60)
    print("Phase 4 Quick Validation")
    print("="*60 + "\n")
    
    all_passed = True
    
    # Check 1: Redis Connection
    redis_ok, r = check_redis_connection()
    all_passed = all_passed and redis_ok
    
    if not redis_ok:
        print(f"\n{RED}Cannot proceed without Redis connection{RESET}")
        sys.exit(1)
    
    # Check 2: Consumer Group
    group_ok = check_consumer_group(r)
    all_passed = all_passed and group_ok
    
    # Check 3: Drift Service Health
    health_ok = check_drift_service_health()
    all_passed = all_passed and health_ok
    
    # Check 4: Metrics Endpoint
    metrics_ok, metrics = check_metrics_endpoint()
    all_passed = all_passed and metrics_ok
    
    if not metrics_ok:
        print(f"\n{RED}Cannot proceed without metrics endpoint{RESET}")
        sys.exit(1)
    
    # Check 5: Consumption Rate
    rate_ok, rate = check_consumption_rate(metrics)
    all_passed = all_passed and rate_ok
    
    # Check 6: Consumer Lag
    lag_ok, pending = check_consumer_lag(r)
    all_passed = all_passed and lag_ok
    
    # Check 7: Memory Usage (warning only)
    check_memory_usage()
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print(f"{GREEN}All checks passed! ✓{RESET}")
        print("\nDrift service is operational and consuming events.")
        sys.exit(0)
    else:
        print(f"{RED}Some checks failed! ✗{RESET}")
        print("\nPlease review the failed checks above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
