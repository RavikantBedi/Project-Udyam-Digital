import subprocess
import sys
sys.path.insert(0, '.')

# run pytest
result = subprocess.run([sys.executable, '-m', 'pytest', '-v'], cwd='backend')
sys.exit(result.returncode)
