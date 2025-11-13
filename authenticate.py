#!/usr/bin/env python3
"""
Volvo API Authentication Helper

This script helps you authenticate with the Volvo Cars API for the first time.
It will:
1. Generate an authorization URL
2. Guide you through the browser authentication process
3. Exchange the authorization code for tokens
4. Save tokens for future use

Usage:
    python authenticate.py

Requirements:
    - Valid Volvo Developer Portal application credentials in config
    - Internet connection
    - Web browser access to Volvo ID
"""

import sys
import webbrowser

# Add current directory to path for imports
sys.path.append(".")

from volvo_api import VolvoAuth
from volvo_api.config import VolvoConfig
from volvo_api.exceptions import AuthenticationError


def main():
    """Main authentication flow"""
    print("🔐 Volvo Cars API Authentication Helper")
    print("=" * 50)

    try:
        # Load configuration
        print("📋 Loading configuration...")
        config = VolvoConfig()

        print(f"   Client ID: {config.client_id[:10]}...")
        print(f"   Redirect URI: {config.redirect_uri}")
        print()

        # Initialize authentication
        print("🔧 Initializing authentication...")
        auth = VolvoAuth(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=config.redirect_uri,
            scopes=config.DEFAULT_SCOPES,
            use_pkce=True,
            token_storage_path="tokens.json",
        )

        # Check if already authenticated
        if auth.is_authenticated():
            print("✅ You are already authenticated!")
            print("   Tokens found and are still valid.")
            print()

            choice = (
                input("Do you want to re-authenticate anyway? (y/N): ").strip().lower()
            )
            if choice not in ["y", "yes"]:
                print("👋 Keeping existing authentication. Goodbye!")
                return
            else:
                print("🔄 Proceeding with re-authentication...")
                auth.logout()  # Clear existing tokens
                print()

        # Step 1: Generate authorization URL
        print("🔗 Step 1: Generating authorization URL...")
        auth_url = auth.get_authorization_url()
        print(f"   Authorization URL: {auth_url}")
        print()

        # Step 2: Open browser (optional)
        choice = input("🌐 Open this URL in your browser now? (Y/n): ").strip().lower()
        if choice not in ["n", "no"]:
            try:
                webbrowser.open(auth_url)
                print("   ✅ Browser opened")
            except (OSError, webbrowser.Error) as e:
                print(f"   ⚠️ Could not open browser automatically: {e}")
                print(
                    "   Please copy and paste the URL above into your browser manually."
                )
        else:
            print("   Please copy and paste the URL above into your browser.")

        print()
        print("📝 Instructions:")
        print("   1. In your browser, log in with your Volvo ID credentials")
        print("   2. Grant permission to your application")
        print("   3. You will be redirected to your redirect URI")
        print("   4. Copy the ENTIRE redirect URL from your browser's address bar")
        print("   5. Paste it below")
        print()

        # Step 3: Get callback URL from user
        while True:
            callback_url = input("🔗 Paste the callback URL here: ").strip()

            if not callback_url:
                print("   ❌ Please provide the callback URL")
                continue

            if not callback_url.startswith(("http://", "https://")):
                print("   ❌ URL should start with http:// or https://")
                continue

            # Validate that it contains the expected redirect URI base
            if not callback_url.startswith(config.redirect_uri.split("?")[0]):
                print(
                    f"   ⚠️ URL doesn't start with expected redirect URI: {config.redirect_uri}"
                )
                choice = input("   Continue anyway? (y/N): ").strip().lower()
                if choice not in ["y", "yes"]:
                    continue

            break

        # Step 4: Extract authorization code
        print()
        print("🔍 Step 2: Extracting authorization code...")
        try:
            code, state = VolvoAuth.extract_code_from_callback_url(callback_url)
            print(f"   ✅ Authorization code extracted: {code[:20]}...")
            if state:
                print(f"   State parameter: {state}")
        except AuthenticationError as e:
            print(f"   ❌ Failed to extract authorization code: {e}")
            return

        # Step 5: Exchange code for tokens
        print()
        print("🔄 Step 3: Exchanging code for tokens...")
        try:
            token_data = auth.exchange_code_for_tokens(code)
            print("   ✅ Token exchange successful!")

            # Show token info (without revealing actual tokens)
            access_token = token_data.get("access_token", "")
            refresh_token = token_data.get("refresh_token", "")
            expires_in = token_data.get("expires_in", "Unknown")

            print(
                f"   Access token: {access_token[:20]}..."
                if access_token
                else "   No access token"
            )
            print(
                f"   Refresh token: {refresh_token[:20]}..."
                if refresh_token
                else "   No refresh token"
            )
            print(f"   Expires in: {expires_in} seconds")

        except AuthenticationError as e:
            print(f"   ❌ Token exchange failed: {e}")
            return

        # Step 6: Verify authentication
        print()
        print("✅ Step 4: Verifying authentication...")
        if auth.is_authenticated():
            print("   ✅ Authentication successful!")
            print("   Tokens have been saved to 'tokens.json'")
            print()
            print("🎉 You are now ready to use the Volvo API!")
            print()
            print("💡 Next steps:")
            print("   - Run: python volvo_battery_mqtt.py --test")
            print("   - Or use the API in your own scripts")

        else:
            print("   ❌ Authentication verification failed")
            print("   Please try again or check your credentials")

    except KeyboardInterrupt:
        print("\n👋 Authentication cancelled by user")

    except (ImportError, FileNotFoundError, ValueError) as e:
        print(f"\n❌ Configuration error: {e}")
        print("Please check your configuration and try again")


if __name__ == "__main__":
    main()
