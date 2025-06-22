import subprocess

# Load your requirements.txt
with open("requirements.txt") as f:
    packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]

print(f"📦 Installing {len(packages)} packages...\n")

successes = []
failures = []

for pkg in packages:
    print(f"🔧 Installing: {pkg} ... ", end="")
    try:
        subprocess.run(["pip", "install", pkg], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅")
        successes.append(pkg)
    except subprocess.CalledProcessError:
        print("❌ (skipped)")
        failures.append(pkg)

# Summary
print("\n✅ Installed:", len(successes))
print("❌ Skipped:", len(failures))
if failures:
    print("Skipped packages:")
    for f in failures:
        print(f"  - {f}")


# --------------------------------------
# Overview of the Installation Process
# Date: 2023-10-01 
# --------------------------------------
"""
✅ Installed: 369
❌ Skipped: 18
Skipped packages:
  - anaconda-anon-usage==0.4.4
  - anaconda-client==1.12.3
  - anaconda-navigator==2.6.0
  - anaconda-project==0.11.1
  - conda==24.5.0
  - conda-build==24.5.1
  - conda-content-trust==0.2.0
  - conda_index==0.5.0
  - conda-libmamba-solver==24.1.0
  - conda-repo-cli==1.0.88
  - conda-token==0.5.0+1.g2209e04
  - imagecodecs==2023.1.23
  - libmambapy==1.5.8
  - menuinst==2.1.1
  - navigator-updater==0.5.1
  - python-snappy==0.6.1
  - ruamel-yaml-conda==0.17.21
  - tables==3.9.2
"""

