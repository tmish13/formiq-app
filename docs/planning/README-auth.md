# FormIQ Authentication System

This document outlines the authentication system for FormIQ, designed to work with both web and mobile applications.

## Authentication Architecture

We use standard JWT (JSON Web Token) token-based authentication for several key reasons:

1. **Cross-platform Compatibility**: JWT tokens work consistently across web and mobile platforms
2. **Stateless Design**: The server doesn't need to store session data
3. **Mobile Friendly**: Mobile apps can securely store tokens in device keychains/keystores
4. **Simplicity**: Single authentication mechanism across all clients

## How It Works

### Authentication Flow

1. **User Login/Registration**:
   - User provides credentials (email/password)
   - Server validates credentials and creates access and refresh tokens
   - Server returns tokens in the response body (not cookies)
   - Client stores tokens securely (localStorage for web, secure storage for mobile)

2. **Authenticated Requests**:
   - Client includes the access token in the Authorization header
   - `Authorization: Bearer {token}`
   - Server validates the token for each request

3. **Token Refresh**:
   - When the access token expires, client uses refresh token to get a new one
   - If refresh token is expired, user must log in again

### Token Storage

#### Web Applications:
- Access and refresh tokens stored in localStorage
- For higher security applications, consider using:
  - Web Crypto API for additional encryption
  - Service workers to handle token management

#### Mobile Applications:
- iOS: Keychain Services
- Android: EncryptedSharedPreferences or Android Keystore
- React Native: Secure storage libraries like `react-native-keychain`

## Security Considerations

1. **Token Security**:
   - Access tokens have short lifetimes (typically 15-60 minutes)
   - Refresh tokens have longer lifetimes (days/weeks) but can be revoked
   - All tokens are signed with a secure secret

2. **HTTPS Only**:
   - All API requests should use HTTPS to prevent token interception

3. **Token Payload**:
   - Avoid storing sensitive information in token payload
   - Keep payload minimal (user ID, expiration, etc.)

4. **Additional Security Measures**:
   - Rate limiting on authentication endpoints
   - Token blacklisting for compromised tokens
   - IP tracking for suspicious activity

## API Endpoints

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Authenticate and receive tokens
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Invalidate tokens (client also removes stored tokens)
- `GET /users/me` - Get current user profile

## Sample Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "expires_in": 3600,
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "username": "user123",
    "is_active": true,
    "is_verified": true,
    "fitness_goals": ["strength", "endurance"]
  }
}
```

## Mobile App Integration

### iOS (Swift)

```swift
// Store tokens
func saveTokens(accessToken: String, refreshToken: String) {
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrAccount as String: "accessToken",
        kSecValueData as String: accessToken.data(using: .utf8)!,
        kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock
    ]
    SecItemAdd(query as CFDictionary, nil)
    
    // Similar code for refresh token
}

// Add token to request
func addAuthHeader(request: URLRequest) -> URLRequest {
    var request = request
    if let accessToken = getAccessToken() {
        request.addValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
    }
    return request
}
```

### Android (Kotlin)

```kotlin
// Store tokens
fun saveTokens(accessToken: String, refreshToken: String) {
    val sharedPrefs = EncryptedSharedPreferences.create(
        "auth_prefs",
        masterKeyAlias,
        context,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    with (sharedPrefs.edit()) {
        putString("access_token", accessToken)
        putString("refresh_token", refreshToken)
        apply()
    }
}

// Add token to request
fun addAuthHeader(request: Request): Request {
    val accessToken = getAccessToken()
    return accessToken?.let {
        request.newBuilder()
            .header("Authorization", "Bearer $it")
            .build()
    } ?: request
}
```

## Web Integration

```typescript
// Store tokens after login
function storeTokens(tokens) {
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
}

// Add token to API requests
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response.status === 401 && !error.config._retry) {
      error.config._retry = true;
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post('/auth/refresh', { refresh_token: refreshToken });
        
        localStorage.setItem('access_token', response.data.access_token);
        localStorage.setItem('refresh_token', response.data.refresh_token);
        
        error.config.headers['Authorization'] = `Bearer ${response.data.access_token}`;
        return axios(error.config);
      } catch (refreshError) {
        // Logout user if refresh fails
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);
``` 