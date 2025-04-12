import { Request, Response, NextFunction } from 'express';
import crypto from 'crypto';
import { getJWTSecret } from './jwt_config';

// Extend Express Request type to include user
interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    [key: string]: any;
  };
}

interface CSRFOptions {
  cookie: {
    key: string;
    path: string;
    maxAge: number;
    secure: boolean;
    sameSite: boolean | 'lax' | 'strict' | 'none';
  };
  ignoreMethods: string[];
  headerKey: string;
}

const defaultOptions: CSRFOptions = {
  cookie: {
    key: 'XSRF-TOKEN',
    path: '/',
    maxAge: 7200000, // 2 hours
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict'
  },
  ignoreMethods: ['GET', 'HEAD', 'OPTIONS'],
  headerKey: 'X-XSRF-TOKEN'
};

class CSRFTokenManager {
  private static instance: CSRFTokenManager;
  private tokenCache: Map<string, { token: string; expires: number }>;
  
  private constructor() {
    this.tokenCache = new Map();
  }
  
  public static getInstance(): CSRFTokenManager {
    if (!CSRFTokenManager.instance) {
      CSRFTokenManager.instance = new CSRFTokenManager();
    }
    return CSRFTokenManager.instance;
  }
  
  private generateToken(): string {
    return crypto.randomBytes(32).toString('hex');
  }
  
  public createToken(userId: string): string {
    const token = this.generateToken();
    const expires = Date.now() + defaultOptions.cookie.maxAge;
    
    this.tokenCache.set(userId, { token, expires });
    return token;
  }
  
  public validateToken(userId: string, token: string): boolean {
    const cached = this.tokenCache.get(userId);
    
    if (!cached) {
      return false;
    }
    
    if (Date.now() > cached.expires) {
      this.tokenCache.delete(userId);
      return false;
    }
    
    return crypto.timingSafeEqual(
      Buffer.from(token),
      Buffer.from(cached.token)
    );
  }
  
  public cleanupExpiredTokens(): void {
    const now = Date.now();
    for (const [userId, data] of this.tokenCache.entries()) {
      if (now > data.expires) {
        this.tokenCache.delete(userId);
      }
    }
  }
}

// Middleware to set CSRF token
export const setCSRFToken = (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void => {
  if (!req.user?.id) {
    next();
    return;
  }
  
  const manager = CSRFTokenManager.getInstance();
  const token = manager.createToken(req.user.id);
  
  res.cookie(defaultOptions.cookie.key, token, {
    ...defaultOptions.cookie,
    httpOnly: true
  });
  
  next();
};

// Middleware to validate CSRF token
export const validateCSRFToken = (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void => {
  // Clean up expired tokens periodically
  CSRFTokenManager.getInstance().cleanupExpiredTokens();
  
  // Skip validation for ignored methods
  if (defaultOptions.ignoreMethods.includes(req.method)) {
    next();
    return;
  }
  
  if (!req.user?.id) {
    res.status(403).json({ error: 'Unauthorized' });
    return;
  }
  
  const token = req.headers[defaultOptions.headerKey.toLowerCase()];
  
  if (!token || typeof token !== 'string') {
    res.status(403).json({ error: 'CSRF token missing' });
    return;
  }
  
  const manager = CSRFTokenManager.getInstance();
  
  if (!manager.validateToken(req.user.id, token)) {
    res.status(403).json({ error: 'Invalid CSRF token' });
    return;
  }
  
  next();
};

// Helper to verify if request is same-origin
export const isSameOrigin = (req: Request): boolean => {
  const origin = req.get('origin');
  if (!origin) {
    return true; // Same-origin requests don't set the origin header
  }
  
  try {
    const requestOrigin = new URL(origin);
    const appOrigin = new URL(process.env.APP_URL || 'http://localhost:3000');
    return requestOrigin.origin === appOrigin.origin;
  } catch {
    return false;
  }
};

export default {
  setCSRFToken,
  validateCSRFToken,
  isSameOrigin
}; 