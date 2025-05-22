#!/usr/bin/env python3

import os
import yaml
import subprocess
import argparse
from datetime import datetime

def load_config():
    """Load the configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def run_load_test(scenario_name, config):
    """Run a load test with the specified scenario configuration"""
    scenario = config['scenarios'][scenario_name]
    
    # Create timestamp for the report directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_dir = os.path.join(
        config['report']['output_dir'],
        f"{scenario_name}_{timestamp}"
    )
    os.makedirs(report_dir, exist_ok=True)
    
    # Build the locust command
    cmd = [
        "locust",
        "-f", "tests/load/locustfile.py",
        "--host", scenario['host'],
        "--users", str(scenario['users']),
        "--spawn-rate", str(scenario['spawn_rate']),
        "--run-time", scenario['run_time'],
        "--headless",
        "--html", os.path.join(report_dir, "report.html"),
        "--csv", os.path.join(report_dir, "stats")
    ]
    
    print(f"\nRunning {scenario_name} scenario:")
    print(f"Description: {scenario['description']}")
    print(f"Users: {scenario['users']}")
    print(f"Spawn Rate: {scenario['spawn_rate']}")
    print(f"Duration: {scenario['run_time']}")
    print(f"Report Directory: {report_dir}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\nLoad test completed successfully. Reports saved to: {report_dir}")
    except subprocess.CalledProcessError as e:
        print(f"\nError running load test: {e}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Run FormIQ load tests')
    parser.add_argument(
        '--scenario',
        choices=['normal_load', 'peak_load', 'stress_test', 'endurance_test', 'all'],
        default='normal_load',
        help='Load test scenario to run'
    )
    
    args = parser.parse_args()
    config = load_config()
    
    # Create the main reports directory if it doesn't exist
    os.makedirs(config['report']['output_dir'], exist_ok=True)
    
    if args.scenario == 'all':
        scenarios = config['scenarios'].keys()
        results = []
        for scenario in scenarios:
            success = run_load_test(scenario, config)
            results.append((scenario, success))
        
        print("\nTest Summary:")
        for scenario, success in results:
            status = "✓ Passed" if success else "✗ Failed"
            print(f"{scenario}: {status}")
    else:
        run_load_test(args.scenario, config)

if __name__ == "__main__":
    main() 