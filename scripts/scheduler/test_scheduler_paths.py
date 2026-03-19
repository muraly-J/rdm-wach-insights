"""Test that scheduler resolves ETL script paths correctly."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import just the path resolution logic
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def script_path_old(script_name):
    return os.path.join(PROJECT_ROOT, "scripts", script_name)

def script_path_new(script_name):
    return os.path.join(PROJECT_ROOT, "scripts", "etl", script_name)

def test_script_paths_exist():
    scripts = ["run_health_etl.py", "run_prediction_etl.py"]
    for s in scripts:
        old_path = script_path_old(s)
        new_path = script_path_new(s)
        assert not os.path.exists(old_path), f"Old path should NOT exist: {old_path}"
        assert os.path.exists(new_path), f"New path MUST exist: {new_path}"
    print("PASS: All ETL scripts found at scripts/etl/")

if __name__ == "__main__":
    test_script_paths_exist()
