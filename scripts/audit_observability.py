#!/usr/bin/env python3
"""
Runtime Observability Audit Script
Verifies metrics emission and scrape/query status in the ML Observability Platform
"""

import subprocess
import time
import os
import sys
import json
import signal
import shutil
import shlex
from pathlib import Path
import urllib.request
import urllib.error

def run_command(cmd, cwd=None, shell=True):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1

def setup_env():
    """Ensure .env exists in infra directory"""
    repo_root = Path(__file__).parent
    infra_dir = repo_root / "infra"
    env_file = infra_dir / ".env"
    env_example = repo_root / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        print("[SETUP] Copying .env.example to infra/.env...")
        shutil.copy(env_example, env_file)
        print(f"[SETUP] Created: {env_file}")
        return True
    elif env_file.exists():
        print(f"[SETUP] {env_file} already exists")
        return True
    else:
        print(f"[SETUP] ERROR: .env.example not found at {env_example}")
        return False

def detect_runtime(repo_root: Path):
    """Load container runtime details from scripts/runtime.sh"""
    runtime_script = repo_root / "scripts" / "runtime.sh"
    if not runtime_script.exists():
        print(f"[SETUP] ERROR: runtime script not found at {runtime_script}")
        return None

    shell_cmd = (
        f"source {shlex.quote(str(runtime_script))} && "
        "printf '%s\\n' \"$CONTAINER_RUNTIME\" \"$COMPOSE_CMD\" \"$EXEC_CMD\" \"$COMPOSE_FILE\""
    )
    try:
        result = subprocess.run(
            ["bash", "-lc", shell_cmd],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        print("[SETUP] ERROR: bash not found; cannot source scripts/runtime.sh")
        return None

    if result.returncode != 0:
        print(f"[SETUP] ERROR: failed to detect runtime:\n{result.stderr.strip()}")
        return None

    values = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(values) != 4:
        print("[SETUP] ERROR: runtime script did not return expected values")
        return None

    return {
        "container_runtime": values[0],
        "compose_cmd": values[1],
        "exec_cmd": values[2],
        "compose_file": values[3],
    }

def start_stack(runtime):
    """Start the runtime compose stack"""
    infra_dir = Path(__file__).parent / "infra"
    
    print("\n" + "="*70)
    print("STEP 1: Starting Compose Stack")
    print("="*70)
    
    print(f"[STACK] Runtime: {runtime['container_runtime']}")
    print(f"[STACK] Running: {runtime['compose_cmd']} -f {runtime['compose_file']} up -d")
    stdout, stderr, rc = run_command(
        f"{runtime['compose_cmd']} -f {runtime['compose_file']} up -d",
        cwd=infra_dir
    )
    
    if rc == 0:
        print("[STACK] ✓ Started successfully")
    else:
        print(f"[STACK] ✗ Failed to start:\n{stderr}")
        return False
    
    # Wait for services to be ready
    print("[STACK] Waiting 15 seconds for services to stabilize...")
    time.sleep(15)
    
    # Check status
    print("[STACK] Checking container status...")
    stdout, stderr, rc = run_command(
        f"{runtime['compose_cmd']} -f {runtime['compose_file']} ps",
        cwd=infra_dir
    )
    
    if rc == 0:
        print("[STACK] Container status:\n" + stdout)
    else:
        print(f"[STACK] Failed to get status: {stderr}")
    
    return True

def generate_events():
    """Generate events using data-generator"""
    repo_root = Path(__file__).parent
    generator_dir = repo_root / "data-generator"
    
    print("\n" + "="*70)
    print("STEP 2: Generating Event Stream (20 seconds)")
    print("="*70)
    
    # Start data-generator in background
    print("[GENERATOR] Starting data-generator for 20 seconds...")
    try:
        # Run with REDIS_HOST=localhost
        proc = subprocess.Popen(
            ["python3", "generator.py"],
            cwd=generator_dir,
            env={**os.environ, "REDIS_HOST": "localhost"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Let it run for 20 seconds
        time.sleep(20)
        
        # Stop it
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
        
        print("[GENERATOR] ✓ Generated events for 20 seconds")
        if "Published" in stdout:
            print(f"[GENERATOR] Output: {[line for line in stdout.split(chr(10)) if 'Published' in line]}")
        
        return True
    except Exception as e:
        print(f"[GENERATOR] ✗ Error: {e}")
        return False

def fetch_metrics(url):
    """Fetch metrics from endpoint"""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.read().decode('utf-8'), None
    except urllib.error.URLError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)

def parse_prometheus_metrics(metrics_text):
    """Parse Prometheus metrics text format"""
    metrics = {}
    for line in metrics_text.split('\n'):
        if not line or line.startswith('#'):
            continue
        # Extract metric name (everything before { or space)
        parts = line.split('{')
        if len(parts) > 1:
            metric_name = parts[0]
        else:
            metric_name = line.split()[0] if ' ' in line else line
        
        if metric_name not in metrics:
            metrics[metric_name] = True
    
    return sorted(list(metrics))

def step_3_fetch_metrics():
    """Step 3: Fetch source metrics endpoint"""
    print("\n" + "="*70)
    print("STEP 3: Fetching Metrics from Drift Service (Port 8000)")
    print("="*70)
    
    url = "http://localhost:8000/metrics"
    print(f"[METRICS] Fetching: {url}")
    
    metrics_text, error = fetch_metrics(url)
    if error:
        print(f"[METRICS] ✗ Error: {error}")
        return None
    
    metric_names = parse_prometheus_metrics(metrics_text)
    print(f"[METRICS] ✓ Retrieved {len(metric_names)} metrics")
    print(f"[METRICS] Metric names present:")
    for name in metric_names:
        if name:
            print(f"  - {name}")
    
    return metrics_text

def step_4_prometheus_targets():
    """Step 4: Check Prometheus targets and scrape status"""
    print("\n" + "="*70)
    print("STEP 4: Checking Prometheus Targets & Scrape Status")
    print("="*70)
    
    url = "http://localhost:9090/api/v1/targets"
    print(f"[PROMETHEUS] Fetching: {url}")
    
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        print(f"[PROMETHEUS] ✓ Retrieved targets")
        
        # Look for drift-service target
        active_targets = data.get('data', {}).get('activeTargets', [])
        for target in active_targets:
            labels = target.get('labels', {})
            job_name = labels.get('job', 'unknown')
            instance = labels.get('instance', 'unknown')
            
            if job_name == 'drift-service':
                print(f"\n[PROMETHEUS] Drift-Service Target Details:")
                print(f"  Job: {job_name}")
                print(f"  Instance: {instance}")
                print(f"  Last Scrape: {target.get('lastScrape', 'N/A')}")
                print(f"  Scrape Duration: {target.get('scrapeDuration', 'N/A')}")
                
                # Check for errors
                if target.get('lastError'):
                    print(f"  ⚠ Last Error: {target.get('lastError')}")
                else:
                    print(f"  ✓ No scrape errors")
    
    except Exception as e:
        print(f"[PROMETHEUS] ✗ Error: {e}")
        return False
    
    return True

def step_5_promql_queries():
    """Step 5: Run PromQL queries"""
    print("\n" + "="*70)
    print("STEP 5: Running PromQL Queries")
    print("="*70)
    
    queries = [
        "ml_drift_score",
        "total_predictions",
        "inference_latency_bucket",
        "drift_events_processed_total",
        "drift_alerts_published_total"
    ]
    
    for query in queries:
        url = f"http://localhost:9090/api/v1/query?query={query}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            result = data.get('data', {}).get('result', [])
            status = "HAS DATA" if result else "NO DATA"
            print(f"[PROMQL] {query:40s} -> {status}")
            
            if result and len(result) > 0:
                # Print first result as sample
                first = result[0]
                if 'value' in first:
                    print(f"         Sample value: {first['value'][1]}")
        
        except Exception as e:
            print(f"[PROMQL] {query:40s} -> ERROR: {e}")

def step_6_dashboard_queries():
    """Step 6: Run dashboard panel queries"""
    print("\n" + "="*70)
    print("STEP 6: Running Dashboard Panel Queries")
    print("="*70)
    
    queries = [
        ("rate(total_predictions[1m])", "Prediction rate"),
        ("histogram_quantile(0.50, sum(rate(inference_latency_bucket[5m])) by (le))", "Latency P50"),
        ("histogram_quantile(0.95, sum(rate(inference_latency_bucket[5m])) by (le))", "Latency P95"),
        ("ml_drift_score", "Drift score")
    ]
    
    for query, desc in queries:
        # URL encode the query
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        url = f"http://localhost:9090/api/v1/query?query={encoded_query}"
        
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            result = data.get('data', {}).get('result', [])
            status = "HAS DATA" if result else "NO DATA"
            print(f"[DASHBOARD] {desc:20s} -> {status}")
            
            if result and len(result) > 0:
                first = result[0]
                if 'value' in first:
                    print(f"           Sample value: {first['value'][1]}")
        
        except Exception as e:
            print(f"[DASHBOARD] {desc:20s} -> ERROR: {str(e)[:40]}")

def main():
    """Main audit function"""
    print("\n" + "="*70)
    print("ML OBSERVABILITY PLATFORM - RUNTIME AUDIT")
    print("="*70)
    
    # Step 0: Setup
    if not setup_env():
        print("[ERROR] Setup failed")
        sys.exit(1)

    runtime = detect_runtime(Path(__file__).parent)
    if runtime is None:
        print("[ERROR] Runtime detection failed")
        sys.exit(1)
    
    # Step 1: Start stack
    if not start_stack(runtime):
        print("[ERROR] Failed to start stack")
        sys.exit(1)
    
    # Step 2: Generate events
    if not generate_events():
        print("[WARNING] Event generation had issues, continuing...")
    
    # Step 3: Fetch metrics
    metrics_text = step_3_fetch_metrics()
    
    # Step 4: Check Prometheus
    step_4_prometheus_targets()
    
    # Step 5: Run PromQL queries
    step_5_promql_queries()
    
    # Step 6: Run dashboard queries
    step_6_dashboard_queries()
    
    print("\n" + "="*70)
    print("AUDIT COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
