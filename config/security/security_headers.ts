import { Request, Response, NextFunction } from 'express';
import helmet from 'helmet';

interface SecurityHeadersConfig {
  contentSecurityPolicy: {
    directives: {
      [key: string]: string[] | null;  // Allow null for conditional directives
    };
  };
  referrerPolicy: string;
  hsts: {
    maxAge: number;
    includeSubDomains: boolean;
    preload: boolean;
  };
  frameguard: {
    action: 'deny' | 'sameorigin';
  };
  permittedCrossDomainPolicies: string;
}

const defaultConfig: SecurityHeadersConfig = {
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", 'data:', 'blob:'],
      connectSrc: ["'self'", process.env.API_URL || 'http://localhost:3000'],
      fontSrc: ["'self'"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      frameSrc: ["'none'"],
      sandbox: ['allow-forms', 'allow-scripts', 'allow-same-origin'],
      childSrc: ["'none'"],
      workerSrc: ["'self'", 'blob:'],
      frameAncestors: ["'none'"],
      formAction: ["'self'"],
      upgradeInsecureRequests: process.env.NODE_ENV === 'production' ? [] : null,
      blockAllMixedContent: process.env.NODE_ENV === 'production' ? [] : null
    }
  },
  referrerPolicy: 'strict-origin-when-cross-origin',
  hsts: {
    maxAge: 31536000, // 1 year
    includeSubDomains: true,
    preload: true
  },
  frameguard: {
    action: 'deny'
  },
  permittedCrossDomainPolicies: 'none'
};

// Configure security headers middleware
export const configureSecurityHeaders = (config: Partial<SecurityHeadersConfig> = {}) => {
  const mergedConfig = {
    ...defaultConfig,
    ...config,
    contentSecurityPolicy: {
      directives: {
        ...defaultConfig.contentSecurityPolicy.directives,
        ...(config.contentSecurityPolicy?.directives || {})
      }
    }
  };

  // Filter out null directives for production
  const cspDirectives = Object.entries(mergedConfig.contentSecurityPolicy.directives)
    .reduce((acc, [key, value]) => {
      if (value !== null) {
        acc[key] = value;
      }
      return acc;
    }, {} as Record<string, string[]>);

  return [
    // Use Helmet for common security headers
    helmet({
      contentSecurityPolicy: {
        useDefaults: false,
        directives: cspDirectives
      },
      referrerPolicy: {
        policy: mergedConfig.referrerPolicy
      },
      hsts: mergedConfig.hsts,
      frameguard: mergedConfig.frameguard,
      permittedCrossDomainPolicies: {
        permittedPolicies: mergedConfig.permittedCrossDomainPolicies
      },
      dnsPrefetchControl: true,
      expectCt: true,
      noSniff: true,
      xssFilter: true
    }),

    // Additional custom headers
    (req: Request, res: Response, next: NextFunction) => {
      // Prevent browsers from detecting the mimetype if not sent correctly
      res.setHeader('X-Content-Type-Options', 'nosniff');
      
      // Disable client-side caching for authenticated routes
      if (req.path.startsWith('/api/') && req.path !== '/api/health') {
        res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
        res.setHeader('Pragma', 'no-cache');
        res.setHeader('Expires', '0');
      }
      
      // Add Feature-Policy header
      res.setHeader('Feature-Policy', [
        "geolocation 'none'",
        "midi 'none'",
        "sync-xhr 'none'",
        "microphone 'none'",
        "camera 'none'",
        "magnetometer 'none'",
        "gyroscope 'none'",
        "fullscreen 'self'",
        "payment 'none'"
      ].join('; '));
      
      next();
    }
  ];
};

// Rate limiting configuration
export const configureRateLimiting = () => {
  const rateLimit = require('express-rate-limit');
  
  return {
    global: rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 100 // limit each IP to 100 requests per windowMs
    }),
    
    auth: rateLimit({
      windowMs: 60 * 60 * 1000, // 1 hour
      max: 5, // limit each IP to 5 login attempts per hour
      message: 'Too many login attempts, please try again later'
    }),
    
    api: rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 50, // limit each IP to 50 requests per 15 minutes
      message: 'Too many API requests, please try again later'
    })
  };
};

export default {
  configureSecurityHeaders,
  configureRateLimiting
}; 