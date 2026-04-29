#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

def run_curl(url):
    """Run curl and return response text."""
    try:
        result = subprocess.run(['curl', '-s', url], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
        return None
    except Exception as e:
        print(f"Error calling {url}: {e}", file=sys.stderr)
        return None

# ===== 1. Collect metrics from drift-service =====
print("=" * 80)
print("1. COLLECTING METRICS FROM DRIFT-SERVICE")
print("=" * 80)

metrics_response = run_curl('http://localhost:8000/metrics')
metric_names = set()

if metrics_response:
    for line in metrics_response.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            metric_name = line.split('{')[0].split(' ')[0].split('[')[0]
            if metric_name:
                metric_names.add(metric_name)

sorted_metrics = sorted(metric_names)
print(f"Found {len(sorted_metrics)} unique metrics:")
print("\n".join([f"  - {m}" for m in sorted_metrics]))

# ===== 2. Check Prometheus targets =====
print("\n" + "=" * 80)
print("2. PROMETHEUS TARGET DETAILS FOR DRIFT-SERVICE")
print("=" * 80)

targets_response = run_curl('http://localhost:9090/api/v1/targets')

if targets_response:
    try:
        targets_data = json.loads(targets_response)
        if 'data' in targets_data:
            active_targets = targets_data['data'].get('activeTargets', [])
            print(f"Total active targets: {len(active_targets)}\n")
            
            for i, target in enumerate(active_targets):
                print(f"Target {i+1}:")
                print(f"  Health: {target.get('health')}")
                print(f"  Scrape URL: {target.get('scrapeUrl')}")
                print(f"  Last Scrape: {target.get('lastScrape')}")
                print(f"  Scrape Interval: {target.get('scrapeInterval')}")
                print(f"  Last Error: {target.get('lastError', 'None')}")
                print()
    except json.JSONDecodeError:
        print("Failed to parse targets response")
else:
    print("No response from Prometheus targets endpoint")

# ===== 3. Evaluate required queries =====
print("=" * 80)
print("3. REQUIRED QUERIES DATA STATUS")
print("=" * 80)

required_queries = [
    'ml_drift_score',
    'total_predictions',
    'inference_latency_bucket',
    'drift_events_processed_total',
    'drift_alerts_published_total'
]

query_results = {}
for query in required_queries:
    response = run_curl(f'http://localhost:9090/api/v1/query?query={query}')
    status = 'NO DATA'
    if response:
        try:
            data = json.loads(response)
            if data.get('status') == 'success':
                result = data.get('data', {}).get('result', [])
                status = 'HAS DATA' if len(result) > 0 else 'NO DATA'
        except json.JSONDecodeError:
            pass
    query_results[query] = status
    print(f"  {query}: {status}")

# ===== 4. Parse dashboards and check panel data =====
print("\n" + "=" * 80)
print("4. DASHBOARD PANELS AND DATA STATUS")
print("=" * 80)

dashboard_files = [
    'infra/grafana/provisioning/dashboards/drift-monitoring.json',
    'infra/grafana/provisioning/dashboards/prediction-distribution.json',
    'infra/grafana/provisioning/dashboards/system-health.json'
]

panel_results = []
base_path = Path('.')

for dashboard_file in dashboard_files:
    dashboard_path = base_path / dashboard_file
    if not dashboard_path.exists():
        print(f"\n  Dashboard not found: {dashboard_file}")
        continue
    
    try:
        with open(dashboard_path, 'r') as f:
            dashboard_data = json.load(f)
        
        panels = dashboard_data.get('panels', [])
        print(f"\n  Dashboard: {dashboard_file}")
        print(f"  Total panels: {len(panels)}")
        
        for panel in panels:
            panel_title = panel.get('title', 'Untitled')
            targets = panel.get('targets', [])
            
            for target_idx, target in enumerate(targets):
                expr = target.get('expr', '')
                
                if not expr:
                    continue
                
                # Query Prometheus
                has_data = False
                try:
                    prom_response = run_curl(f'http://localhost:9090/api/v1/query?query={quote(expr)}')
                    if prom_response:
                        prom_data = json.loads(prom_response)
                        if prom_data.get('status') == 'success':
                            result = prom_data.get('data', {}).get('result', [])
                            has_data = len(result) > 0
                except:
                    pass
                
                panel_results.append({
                    'dashboard': dashboard_file.split('/')[-1],
                    'panel_title': panel_title,
                    'query': expr,
                    'has_data': 'HAS DATA' if has_data else 'NO DATA'
                })
                
                query_display = expr[:50] + '...' if len(expr) > 50 else expr
                print(f"    Panel: {panel_title}")
                print(f"    Query: {query_display}")
                print(f"    Status: {panel_results[-1]['has_data']}\n")
    
    except FileNotFoundError:
        print(f"  File not found: {dashboard_file}")
    except json.JSONDecodeError as e:
        print(f"  Error parsing {dashboard_file}: {e}")
    except Exception as e:
        print(f"  Error processing {dashboard_file}: {e}")

# ===== 5. Return totals =====
print("=" * 80)
print("5. SUMMARY TOTALS")
print("=" * 80)

total_panels = len(panel_results)
panels_with_data = sum(1 for p in panel_results if p['has_data'] == 'HAS DATA')
panels_empty = sum(1 for p in panel_results if p['has_data'] == 'NO DATA')

print(f"Total Panels:              {total_panels}")
print(f"Panels with Data:          {panels_with_data}")
print(f"Panels Empty (NO DATA):    {panels_empty}")

# ===== STRUCTURED OUTPUT TABLE =====
print("\n" + "=" * 80)
print("DETAILED PANEL RESULTS TABLE")
print("=" * 80)

if panel_results:
    print(f"\n{'Dashboard':<35} | {'Panel Title':<35} | {'Has Data':<10}")
    print("-" * 85)
    
    for row in panel_results:
        dashboard = row['dashboard']
        title = row['panel_title'][:32] + '...' if len(row['panel_title']) > 32 else row['panel_title']
        status = row['has_data']
        print(f"{dashboard:<35} | {title:<35} | {status:<10}")
else:
    print("No panels found in dashboards")

print("\n" + "=" * 80)
