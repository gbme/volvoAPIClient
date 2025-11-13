#!/usr/bin/env python3
"""
Setup script for Volvo API project
"""

import os
import subprocess
import sys


def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing Python dependencies...")

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_environment():
    """Set up environment configuration"""
    print("⚙️  Setting up environment...")

    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            import shutil

            shutil.copy(".env.example", ".env")
            print("✅ Created .env from .env.example")
        else:
            print("❌ .env.example not found")
            return False
    else:
        print("✅ .env file already exists")

    return True


def validate_setup():
    """Validate the setup"""
    print("🔍 Validating setup...")

    try:
        from volvo_api.config import VolvoConfig

        config = VolvoConfig()
        missing = config.validate()

        if missing:
            print("❌ Missing required configuration:")
            for field in missing:
                print(f"   - {field}")
            print("\n📝 Please edit .env with your actual credentials")
            return False
        else:
            print("✅ Configuration is valid")
            return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def main():
    """Main setup function"""
    print("🚗 Volvo API Project Setup")
    print("=" * 30)

    # Step 1: Install dependencies
    if not install_dependencies():
        return

    # Step 2: Set up environment
    if not setup_environment():
        return

    # Step 3: Validate setup
    if not validate_setup():
        print("\n📝 Next steps:")
        print("1. Edit .env with your Volvo API credentials")
        print("2. Run: python example.py")
        return

    print("\n🎉 Setup complete!")
    print("\n🚀 Ready to use:")
    print("   python example.py    - Run the complete example")
    print("   python test.py       - Run the test script")

    print("\n📚 Documentation:")
    print("   README.md           - Complete documentation")
    print("   .env                - Configuration file")


if __name__ == "__main__":
    main()
