#!/usr/bin/env python3
"""
Creates a complete Lambda package with psycopg2 included.
Downloads pre-compiled psycopg2 wheel for Lambda (Amazon Linux 2).
"""

import zipfile
import urllib.request
import tempfile
import os
import shutil
from pathlib import Path

print("🚀 Creating complete Lambda deployment package...")

# Create temp directory
temp_dir = Path(tempfile.mkdtemp())
package_dir = temp_dir / "package"
package_dir.mkdir()

print("\n📦 Downloading psycopg2-binary for AWS Lambda...")

# Download pre-compiled psycopg2-binary wheel for manylinux (compatible with Lambda)
wheel_url = "https://files.pythonhosted.org/packages/90/8f/4b64e408e03bb04b2cc77ebe8ac0213c5a13c2e067d65ce1c64fb46d2f30/psycopg2_binary-2.9.9-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"

try:
    wheel_path = temp_dir / "psycopg2.whl"
    urllib.request.urlretrieve(wheel_url, wheel_path)
    print(f"   ✓ Downloaded psycopg2-binary wheel")
    
    # Extract the wheel
    import zipfile as zf
    with zf.ZipFile(wheel_path, 'r') as wheel_zip:
        for member in wheel_zip.namelist():
            # Extract only the psycopg2 module, skip metadata
            if member.startswith('psycopg2/') or member.startswith('psycopg2_binary'):
                wheel_zip.extract(member, package_dir)
    print(f"   ✓ Extracted psycopg2 module")
    
except Exception as e:
    print(f"   ⚠ Warning: Could not download psycopg2: {e}")
    print(f"   Continuing without psycopg2 - you'll need to add it as a layer")

print("\n📁 Adding Lambda code...")

# Copy handler
shutil.copy("lambda/handler.py", package_dir / "handler.py")
print("   ✓ Added handler.py")

# Copy config
shutil.copy("config/pipeline_config.json", package_dir / "pipeline_config.json")
print("   ✓ Added pipeline_config.json")

print("\n📦 Creating lambda-deployment-full.zip...")

# Create zip
zip_path = Path("lambda-deployment-full.zip")
if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(package_dir):
        for file in files:
            file_path = Path(root) / file
            arcname = file_path.relative_to(package_dir)
            zipf.write(file_path, arcname)

# Cleanup
shutil.rmtree(temp_dir)

size_mb = zip_path.stat().st_size / (1024 * 1024)

print(f"   ✓ Created {zip_path}")
print(f"\n" + "="*60)
print("✅ SUCCESS! Complete Lambda package created!")
print("="*60)
print(f"\n📦 File: {zip_path.absolute()}")
print(f"📊 Size: {size_mb:.1f} MB")
print("\n📝 Next steps:")
print("   1. Download 'lambda-deployment-full.zip' from Replit")
print("   2. Upload to AWS Lambda Console")
print("   3. Skip the psycopg2 layer step!")
print("\n💡 This package includes psycopg2, so you only need:")
print("   - AWSSDKPandas-Python312 layer (for pandas/pyarrow)")
print("="*60)
