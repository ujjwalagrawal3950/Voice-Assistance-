import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__))
result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
print(f"Return code: {result.returncode}")