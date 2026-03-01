import os
from supabase import create_client, Client
from typing import Optional

class DatabaseClient:
    """Shared database client for all microservices"""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client instance"""
        if cls._instance is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            if not supabase_url or not supabase_key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

            cls._instance = create_client(supabase_url, supabase_key)

        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the client instance (useful for testing)"""
        cls._instance = None
