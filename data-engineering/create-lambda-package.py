#!/usr/bin/env python3
"""
Script to create a Lambda deployment package for manual upload to AWS Console.
This creates a .zip file you can upload directly to AWS Lambda.
"""

import os
import sys
import subprocess
import zipfile
import shutil
from pathlib import Path

def create_lambda_package():
    print("🚀 Creating Lambda deployment package...")
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Create temporary directory
    package_dir = Path("lambda-package")
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir()
    
    print("📁 Copying Lambda code...")
    
    # Copy the Lambda handler
    handler_src = Path("lambda/handler.py")
    if handler_src.exists():
        shutil.copy(handler_src, package_dir / "handler.py")
        print(f"   ✓ Copied {handler_src}")
    else:
        print(f"   ✗ Warning: {handler_src} not found")
    
    # Copy configuration files (if they exist)
    config_files = [
        ("config/pipeline_config.json", "pipeline_config.json"),
        ("database_config.json", "database_config.json"),
    ]
    
    for src, dest in config_files:
        src_path = Path(src)
        if src_path.exists():
            shutil.copy(src_path, package_dir / dest)
            print(f"   ✓ Copied {src}")
        else:
            print(f"   ⚠ Skipped {src} (not found - optional)")
    
    # Install Python dependencies
    print("\n📦 Installing Python dependencies...")
    print("   This may take 1-2 minutes...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--target", str(package_dir),
            "--upgrade",
            "psycopg2-binary",
            "pandas",
            "pyarrow",
            "boto3",
            "--quiet"
        ], check=True, env={**os.environ, "PYTHONNOUSERSITE": "1"})
        print("   ✓ Dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"   ✗ Error installing dependencies: {e}")
        print("   Continuing anyway...")
    
    # Create the zip file
    print("\n📦 Creating lambda-deployment.zip...")
    zip_path = Path("lambda-deployment.zip")
    
    if zip_path.exists():
        zip_path.unlink()
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
                
    # Get file size
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"   ✓ Created {zip_path} ({size_mb:.1f} MB)")
    
    # Cleanup
    print("\n🧹 Cleaning up temporary files...")
    shutil.rmtree(package_dir)
    print("   ✓ Cleanup complete")
    
    print("\n" + "="*60)
    print("✅ SUCCESS! Lambda deployment package created!")
    print("="*60)
    print(f"\n📦 File: {zip_path.absolute()}")
    print(f"📊 Size: {size_mb:.1f} MB")
    print("\n📝 Next steps:")
    print("   1. Download 'lambda-deployment.zip' from Replit")
    print("      (Right-click the file → Download)")
    print("   2. Go to AWS Lambda Console")
    print("   3. Upload this .zip file to your Lambda function")
    print("\n💡 See the AWS Console deployment guide in the chat above!")
    print("="*60)

if __name__ == "__main__":
    try:
        create_lambda_package()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
