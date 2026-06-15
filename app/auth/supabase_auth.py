import os
import requests

# Retrieve Supabase Credentials from Environment Variables
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')

class SupabaseAuth:
    @staticmethod
    def is_configured():
        """Returns True if Supabase is configured in .env"""
        return bool(SUPABASE_URL and SUPABASE_ANON_KEY)

    @staticmethod
    def verify_token(access_token):
        """
        Verifies client-supplied Supabase JWT.
        Sends a request to Supabase API to retrieve user metadata.
        Returns User info dict if token is valid, else None.
        """
        if not SupabaseAuth.is_configured():
            return None
            
        # Standard Supabase endpoint for authenticated user retrieval
        endpoint = f"{SUPABASE_URL.rstrip('/')}/auth/v1/user"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'apikey': SUPABASE_ANON_KEY
        }
        
        try:
            res = requests.get(endpoint, headers=headers, timeout=5)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"Supabase token verification error: {e}")
            
        return None
