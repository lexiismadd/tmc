from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.settings import settings
from ipaddress import ip_address, ip_network
import logging

security = HTTPBearer()

async def check_ip_whitelist(request: Request):
    settings = request.app.state.settings
    client_ip = request.client.host
    
    # Allow if no whitelist configured
    if not settings.IP_WHITELIST:
        return True
    
    # Check each rule
    for rule in settings.IP_WHITELIST:
        try:
            if '/' in rule:  # CIDR range
                if ip_address(client_ip) in ip_network(rule, strict=False):
                    return True
            elif client_ip == rule:  # Exact match
                return True
        except ValueError:
            continue
    
    raise HTTPException(
        status_code=403,
        detail=f"IP {client_ip} not allowed"
    )

# Combined auth (Bearer + optional whitelist)
async def authenticate(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # First check Bearer token
    if credentials.scheme != "Bearer" or credentials.credentials != request.app.state.settings.API_KEY:
        raise HTTPException(401, "Invalid API key")
    
    # Then check optional IP whitelist
    await check_ip_whitelist(request)
    return True

