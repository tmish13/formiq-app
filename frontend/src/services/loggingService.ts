import { storageService } from './storageService';
import { monitoringService } from './monitoringService';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogEntry {
  id: string;
  timestamp: number;
  level: LogLevel;
  message: string;
  context?: Record<string, any>;
  stack?: string;
  tags?: string[];
}

export interface LogOptions {
  context?: Record<string, any>;
  tags?: string[];
  persist?: boolean;
}

export class LoggingService {
  private static instance: LoggingService;
  private storage = storageService;
  private monitoring = monitoringService;
  private readonly MAX_LOGS = 1000;
  private logBuffer: LogEntry[] = [];
  private logLevel: LogLevel = 'info';

  private constructor() {
    this.initializeLogLevel();
    this.loadStoredLogs();
  }

  public static getInstance(): LoggingService {
    if (!LoggingService.instance) {
      LoggingService.instance = new LoggingService();
    }
    return LoggingService.instance;
  }

  private async initializeLogLevel(): Promise<void> {
    try {
      const storedLevel = await this.storage.get('log_level');
      if (storedLevel) {
        this.logLevel = JSON.parse(storedLevel) as LogLevel;
      }
    } catch (error) {
      console.error('Failed to initialize log level:', error);
    }
  }

  private async loadStoredLogs(): Promise<void> {
    try {
      const storedLogs = await this.storage.get('logs');
      if (storedLogs) {
        this.logBuffer = JSON.parse(storedLogs);
      }
    } catch (error) {
      console.error('Failed to load stored logs:', error);
    }
  }

  public setLogLevel(level: LogLevel): void {
    this.logLevel = level;
    this.storage.set('log_level', JSON.stringify(level)).catch(error => {
      console.error('Failed to store log level:', error);
    });
  }

  public debug(message: string, options: LogOptions = {}): void {
    if (this.shouldLog('debug')) {
      this.log('debug', message, options);
    }
  }

  public info(message: string, options: LogOptions = {}): void {
    if (this.shouldLog('info')) {
      this.log('info', message, options);
    }
  }

  public warn(message: string, options: LogOptions = {}): void {
    if (this.shouldLog('warn')) {
      this.log('warn', message, options);
    }
  }

  public error(message: string | Error, options: LogOptions = {}): void {
    if (this.shouldLog('error')) {
      const errorMessage = message instanceof Error ? message.message : message;
      const context = {
        ...options.context,
        stack: message instanceof Error ? message.stack : undefined
      };
      this.log('error', errorMessage, { ...options, context });
    }
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: LogLevel[] = ['debug', 'info', 'warn', 'error'];
    const currentLevelIndex = levels.indexOf(this.logLevel);
    const messageLevelIndex = levels.indexOf(level);
    return messageLevelIndex >= currentLevelIndex;
  }

  private log(level: LogLevel, message: string, options: LogOptions): void {
    const entry: LogEntry = {
      id: crypto.randomUUID(),
      timestamp: Date.now(),
      level,
      message,
      context: options.context,
      stack: options.context?.stack,
      tags: options.tags
    };

    // Add to buffer
    this.logBuffer.unshift(entry);
    if (this.logBuffer.length > this.MAX_LOGS) {
      this.logBuffer.pop();
    }

    // Console output in development
    if (process.env.NODE_ENV === 'development') {
      const consoleMethod = level === 'debug' ? 'log' : level;
      console[consoleMethod](
        `[${new Date(entry.timestamp).toISOString()}] ${level.toUpperCase()}: ${message}`,
        entry.context || ''
      );
    }

    // Track in monitoring service
    this.monitoring.trackLog(entry);

    // Persist if requested
    if (options.persist) {
      this.persistLogs().catch(error => {
        console.error('Failed to persist logs:', error);
      });
    }
  }

  private async persistLogs(): Promise<void> {
    try {
      await this.storage.set('logs', JSON.stringify(this.logBuffer));
    } catch (error) {
      console.error('Failed to persist logs:', error);
    }
  }

  public async clearLogs(): Promise<void> {
    this.logBuffer = [];
    try {
      await this.storage.remove('logs');
    } catch (error) {
      console.error('Failed to clear logs:', error);
    }
  }

  public getLogs(
    options: {
      level?: LogLevel;
      tags?: string[];
      startTime?: number;
      endTime?: number;
      limit?: number;
    } = {}
  ): LogEntry[] {
    let filteredLogs = [...this.logBuffer];

    // Apply filters
    if (options.level) {
      filteredLogs = filteredLogs.filter(log => log.level === options.level);
    }

    if (options.tags) {
      filteredLogs = filteredLogs.filter(log =>
        log.tags?.some(tag => options.tags?.includes(tag))
      );
    }

    if (options.startTime) {
      filteredLogs = filteredLogs.filter(log => log.timestamp >= (options.startTime || 0));
    }

    if (options.endTime) {
      filteredLogs = filteredLogs.filter(log => log.timestamp <= (options.endTime || Date.now()));
    }

    // Apply limit
    if (options.limit) {
      filteredLogs = filteredLogs.slice(0, options.limit);
    }

    return filteredLogs;
  }

  public async exportLogs(format: 'json' | 'csv' = 'json'): Promise<string> {
    if (format === 'csv') {
      return this.exportLogsAsCsv();
    }
    return JSON.stringify(this.logBuffer, null, 2);
  }

  private exportLogsAsCsv(): string {
    const headers = ['Timestamp', 'Level', 'Message', 'Tags', 'Context'];
    const rows = this.logBuffer.map(log => [
      new Date(log.timestamp).toISOString(),
      log.level,
      log.message,
      log.tags?.join(', ') || '',
      JSON.stringify(log.context || '')
    ]);

    return [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
  }
}

export const loggingService = LoggingService.getInstance(); 