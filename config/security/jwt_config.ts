import { config } from 'dotenv';
import crypto from 'crypto';
import fs from 'fs';
import path from 'path';

// Load environment variables
config();

interface JWTConfig {
  secret: string;
  expiresIn: string;
  algorithm: string;
  issuer: string;
  rotationInterval: number; // in hours
}

class JWTSecretManager {
  private static instance: JWTSecretManager;
  private currentSecret: string;
  private previousSecret: string | null;
  private lastRotation: Date;
  private readonly secretPath: string;
  
  private constructor() {
    this.secretPath = path.join(process.cwd(), 'config', 'security', 'jwt_secrets.json');
    this.loadOrGenerateSecrets();
    this.lastRotation = new Date();
  }

  public static getInstance(): JWTSecretManager {
    if (!JWTSecretManager.instance) {
      JWTSecretManager.instance = new JWTSecretManager();
    }
    return JWTSecretManager.instance;
  }

  private generateSecret(): string {
    return crypto.randomBytes(64).toString('hex');
  }

  private loadOrGenerateSecrets(): void {
    try {
      if (fs.existsSync(this.secretPath)) {
        const secrets = JSON.parse(fs.readFileSync(this.secretPath, 'utf8'));
        this.currentSecret = secrets.current;
        this.previousSecret = secrets.previous;
      } else {
        this.currentSecret = this.generateSecret();
        this.previousSecret = null;
        this.saveSecrets();
      }
    } catch (error) {
      console.error('Error loading JWT secrets:', error);
      throw new Error('Failed to initialize JWT secrets');
    }
  }

  private saveSecrets(): void {
    const secrets = {
      current: this.currentSecret,
      previous: this.previousSecret,
      lastRotation: this.lastRotation.toISOString()
    };
    
    try {
      fs.writeFileSync(this.secretPath, JSON.stringify(secrets, null, 2));
    } catch (error) {
      console.error('Error saving JWT secrets:', error);
      throw new Error('Failed to save JWT secrets');
    }
  }

  public getCurrentSecret(): string {
    return this.currentSecret;
  }

  public getPreviousSecret(): string | null {
    return this.previousSecret;
  }

  public rotateSecrets(): void {
    this.previousSecret = this.currentSecret;
    this.currentSecret = this.generateSecret();
    this.lastRotation = new Date();
    this.saveSecrets();
  }

  public shouldRotate(rotationInterval: number): boolean {
    const hours = (new Date().getTime() - this.lastRotation.getTime()) / (1000 * 60 * 60);
    return hours >= rotationInterval;
  }
}

const jwtConfig: JWTConfig = {
  secret: process.env.JWT_SECRET || JWTSecretManager.getInstance().getCurrentSecret(),
  expiresIn: process.env.JWT_EXPIRES_IN || '24h',
  algorithm: 'HS512',
  issuer: 'formiq-api',
  rotationInterval: parseInt(process.env.JWT_ROTATION_INTERVAL || '168', 10) // Default 7 days
};

export const getJWTSecret = (): string => {
  const manager = JWTSecretManager.getInstance();
  
  // Check if rotation is needed
  if (manager.shouldRotate(jwtConfig.rotationInterval)) {
    manager.rotateSecrets();
  }
  
  return manager.getCurrentSecret();
};

export const validateJWTSecret = (): boolean => {
  const secret = getJWTSecret();
  
  if (!secret || secret.length < 64) {
    throw new Error('JWT secret is not strong enough');
  }
  
  if (secret === 'SECRET_KEY' || secret === 'your-secret-key') {
    throw new Error('JWT secret is using a default value');
  }
  
  return true;
};

export default jwtConfig; 