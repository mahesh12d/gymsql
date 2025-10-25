#!/usr/bin/env python3
"""
Creates a minimal Lambda package with just the code (no dependencies).
AWS Lambda has boto3 built-in, and we'll use Lambda Layers for other dependencies.
"""

import zipfile
import shutil
from pathlib import Path

print("🚀 Creating minimal Lambda package...")

# Create zip file with just the code
zip_path = Path("lambda-deployment.zip")

if zip_path.exists():
    zip_path.unlink()

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add handler
    zipf.write("lambda/handler.py", "handler.py")
    
    # Add config
    zipf.write("config/pipeline_config.json", "pipeline_config.json")
    
print(f"✅ Created {zip_path}")
print(f"📊 Size: {zip_path.stat().st_size / 1024:.1f} KB")
print("\n📝 Next steps:")
print("   1. Download 'lambda-deployment.zip' from Replit")
print("   2. Upload to AWS Lambda Console")
print("   3. Add dependencies via Lambda Layers (see instructions below)")
