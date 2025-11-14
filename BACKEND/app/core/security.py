from fastapi.security import OAuth2PasswordBearer
# This is the token endpoint (your login route)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
