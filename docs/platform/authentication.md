# Authentication

The staging API uses short-lived HS256 JWT access tokens and rotating, hashed refresh tokens. Roles are `admin`, `manager`, `agent`, and `viewer`. `/health`, `/login`, and `/refresh` are public by necessity; all operational routes require bearer authentication. Configure a unique 32+ character `PLATFORM_JWT_SECRET` outside source control. No default user or password is created.
