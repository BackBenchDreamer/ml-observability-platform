#!/usr/bin/env python3
"""
Quick observability verification - checks if services and metrics are available
"""

import urllib.request
import urllib.error
import json
import sys

def check_endpoint(url, desc):
    """Check if an endpoint is reachable"""
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            status = response.getcode()
            print(f"✓ {desc:40s} (HTTP {status})")
            return True
    except urllib.error.URLError as e:
        print(f"✗ {desc:40s} (Connection failed: {str(e)[:30]}...)")
        return False
    except Exception as e:
        print(f"✗ {desc:40s} (Error: {str(e)[:30]}...)")
        return False

def check_metrics():
    """Check metrics endpoints"""
    print("\n" + "="*70)
    print("RUNTIME OBSERVABILITY VERIFICATION")
    print("="*70)
    
    print("\n[1] Service Health Checks:")
    checks = [
        ("http://localhost:8000/health", "Drift Service Health"),
        ("http://localhost:8001/health", "Inference API Health"),
        ("http://localhost:9090/-/healthy", "Prometheus Health"),
        ("http://localhost:9093/-/healthy", "AlertManager Health"),
        ("http://localhost:3000/api/health", "Grafana Health"),
    ]
    
    services_ok = 0
    for url, desc in checks:
        if check_endpoint(url, desc):
            services_ok += 1
    
    print("\n[2] Metrics Endpoints:")
    metrics_ok = 0
    metric_endpoints = [
        ("http://localhost:8000/metrics", "Drift Service /metrics"),
        ("http://localhost:8001/metrics", "Inference API /metrics"),
    ]
    
    for url, desc in metric_endpoints:
        if check_endpoint(url, desc):
            metrics_ok += 1
    
    print("\n[3] Prometheus API:")
    prometheus_ok = check_endpoint("http://localhost:9090/api/v1/targets", "Prometheus /api/v1/targets")
    
    if services_ok >= 4:
        print("\n✓ Most services are healthy")
    else:
        print("\n✗ Some services are not responding - may not be running")
        print("  Have you run: cd infra && podman-compose -f podman-compose.yml up -d")
        sys.exit(1)
    
    # Try to fetch actual metrics if available
    print("\n[4] Sample Metrics from Drift Service:")
    try:
        with urllib.request.urlopen("http://localhost:8000/metrics", timeout=3) as response:
            metrics_text = response.read().decode('utf-8')
            
            # Parse metric names
            metric_names = set()
            for line in metrics_text.split('\n'):
                if not line or line.startswith('#'):
                    continue
                parts = line.split('{')
                if len(parts) > 1:
                    metric_name = parts[0]
                else:
                    metric_name = line.split()[0] if ' ' in line else line
                if metric_name:
                    metric_names.add(metric_name)
            
            print(f"  Found {len(metric_names)} unique metrics:")
            for name in sorted(list(metric_names))[:10]:
                print(f"    - {name}")
            if len(metric_names) > 10:
                print(f"    ... and {len(metric_names) - 10} more")
    
    except Exception as e:
        print(f"  Could not fetch metrics: {e}")
    
    print("\n[5] Prometheus Query Status:")
    try:
        url = "http://localhost:9090/api/v1/query?query=up"
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            result = data.get('data', {}).get('result', [])
            print(f"  Sample query 'up' returned {len(result)} time series")
            for r in result[:3]:
                labels = r.get('metric', {})
                job = labels.get('job', 'unknown')
                instance = labels.get('instance', 'unknown')
                value = r.get('value', ['?', '?'])[1]
                print(f"    {job:20s} {instance:30s} = {value}")
    except Exception as e:
        print(f"  Prometheus query failed: {e}")
    
    print("\n[6] Target Scrape Status:")
    try:
        url = "http://localhost:9090/api/v1/targets"
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode('utf-8'))
            targets = data.get('data', {}).get('activeTargets', [])
            
            print(f"  Total active targets: {len(targets)}")
            for target in targets:
                labels = target.get('labels', {})
                job = labels.get('job', 'unknown')
                instance = labels.get('instance', 'unknown')
                last_scrape = target.get('lastScrape', 'never')
                
                # Parse ISO timestamp to see if recent
                if 'T' in last_scrape:
                    last_scrape_short = last_scrape.split('T')[1][:8]
                else:
                    last_scrape_short = last_scrape
                
                error = target.get('lastError', '')
                error_str = f" (ERROR: {error[:30]}...)" if error else ""
                
                print(f"    {job:20s} {instance:30s} Last: {last_scrape_short}{error_str}")
    except Exception as e:
        print(f"  Could not fetch targets: {e}")

if __name__ == "__main__":
    check_metrics()
