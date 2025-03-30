# recruiterbook-api

Local: run with uvicorn main:app --reload. Docs will be available at http://127.0.0.1:8000/docs.

Deployed at https://recruiterbook-api-production.up.railway.app/docs. 

## API Authentication

The API supports two methods of authentication:

### Cookie Authentication (for Web Browser)

When a user signs in with Google through the web UI, a JWT token is stored in a cookie. This authentication method is automatically used when accessing the API from the browser.

### Bearer Token Authentication (for API clients)

For API clients or external applications, use the JWT token directly with Bearer authentication:

1. After logging in through Google OAuth, get a JWT token from the `/auth/token` endpoint
2. Include the token in the `Authorization` header of your requests:

```
Authorization: Bearer your-jwt-token
```

This is useful for mobile apps, scripts, or any third-party integration that needs to access the API. 
