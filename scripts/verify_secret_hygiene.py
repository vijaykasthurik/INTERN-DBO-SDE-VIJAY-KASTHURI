import subprocess
import os
import sys

if not os.path.exists(".env"):
    print(".env not found")
    sys.exit(0)

with open(".env") as f:
    env_lines = f.readlines()

real_secrets = []
for line in env_lines:
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        v = v.strip("\"'")
        if any(term in k.upper() for term in ("KEY", "SECRET", "PASS", "TOKEN")):
            real_secrets.append((k, v))

out = subprocess.check_output(["git", "log", "-p", "--all"], encoding="utf-8", errors="ignore")

found_leaks = []
for k, s in real_secrets:
    if s in out:
        found_leaks.append(k)

if found_leaks:
    print("CRITICAL LEAK DETECTED for env vars:", found_leaks)
    sys.exit(1)
else:
    print(f"CLEAN: Scanned {len(real_secrets)} active environment secrets. Exactly 0 leaked in git history!")
