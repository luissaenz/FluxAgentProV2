"""Identity bridge for MCP.
Generates internal JWTs for communication with platform services.
"""

from datetime import datetime, timedelta, UTC
from jose import jwt
from ..config import get_settings

ALGORITHM = "HS256"

def create_internal_token(org_id: str, user_id: str = "mcp-system", expires_delta: timedelta = timedelta(minutes=60)) -> str:
    """
    Creates a JWT token for internal use, signed with the Supabase JWT secret.
    
    Args:
        org_id: The organization ID context.
        user_id: The user ID context (defaults to mcp-system).
        expires_delta: Token lifetime.
        
    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        # SUPUESTO: If secret is missing in dev, use a placeholder to avoid crash, 
        # but log warning if possible. Rason: Allow dev without full env if not doing auth checks.
        secret = "dev-secret-placeholder-change-me"
    else:
        secret = settings.supabase_jwt_secret

    expire = datetime.now(UTC) + expires_delta
    
    to_encode = {
        "exp": expire,
        "sub": user_id,
        "org_id": org_id,
        "role": "service_role", # MCP acts with elevated privileges internally
        "iss": "fluxagentpro-mcp"
    }
    
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=ALGORITHM)
    return encoded_jwt
