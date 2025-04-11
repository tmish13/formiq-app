export interface MetricValue {
  value: number;
  timestamp: number;
}

export interface Metric {
  name: string;
  values: MetricValue[];
  unit?: string;
  tags?: string[];
}

export interface Alert {
  type: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  details?: Record<string, any>;
  timestamp: number;
}

export interface LogEntry {
  level: string;
  message: string;
  context?: Record<string, any>;
  timestamp: number;
}

export class MonitoringService {
  private static instance: MonitoringService;
  private metrics: Map<string, Metric> = new Map();
  private alerts: Alert[] = [];
  private logs: LogEntry[] = [];
  private readonly MAX_METRIC_VALUES = 1000;
  private readonly MAX_ALERTS = 100;
  private readonly MAX_LOGS = 1000;
  private alertHandlers: ((alert: Alert) => void)[] = [];

  private constructor() {
    // Initialize performance monitoring
    if (typeof window !== 'undefined') {
      this.initializePerformanceMonitoring();
    }
  }

  public static getInstance(): MonitoringService {
    if (!MonitoringService.instance) {
      MonitoringService.instance = new MonitoringService();
    }
    return MonitoringService.instance;
  }

  private initializePerformanceMonitoring(): void {
    // Track page load performance
    window.addEventListener('load', () => {
      const performance = window.performance;
      if (performance) {
        // Navigation Timing
        const navigationTiming = performance.getEntriesByType('navigation')[0];
        if (navigationTiming) {
          this.trackMetric('page_load_time', navigationTiming.duration, 'ms');
        }

        // Resource Timing
        const resources = performance.getEntriesByType('resource');
        resources.forEach(resource => {
          const resourceTiming = resource as PerformanceResourceTiming;
          this.trackMetric(
            `resource_load_time_${resourceTiming.initiatorType}`,
            resourceTiming.duration,
            'ms',
            ['resource', resourceTiming.initiatorType]
          );
        });
      }
    });

    // Track memory usage if available
    if (performance && (performance as any).memory) {
      setInterval(() => {
        const memory = (performance as any).memory;
        this.trackMetric('heap_size', memory.usedJSHeapSize, 'bytes', ['memory']);
      }, 30000);
    }
  }

  public trackMetric(name: string, value: number, unit?: string, tags?: string[]): void {
    const metric = this.metrics.get(name) || { name, values: [], unit, tags };
    
    metric.values.push({
      value,
      timestamp: Date.now()
    });

    // Trim old values if exceeding max
    if (metric.values.length > this.MAX_METRIC_VALUES) {
      metric.values = metric.values.slice(-this.MAX_METRIC_VALUES);
    }

    this.metrics.set(name, metric);
  }

  public trackMetrics(metrics: Record<string, number>, unit?: string, tags?: string[]): void {
    Object.entries(metrics).forEach(([name, value]) => {
      this.trackMetric(name, value, unit, tags);
    });
  }

  public trackError(error: Error | string, context?: Record<string, any>): void {
    const message = error instanceof Error ? error.message : error;
    const errorContext = error instanceof Error ? 
      { ...context, stack: error.stack } : context;

    this.sendAlert({
      type: 'error',
      message,
      severity: 'error',
      details: errorContext
    });

    this.trackMetric('error_count', 1, undefined, ['error']);
  }

  public trackLog(entry: LogEntry): void {
    this.logs.push(entry);
    if (this.logs.length > this.MAX_LOGS) {
      this.logs.shift();
    }

    // Track log counts by level
    this.trackMetric(`log_count_${entry.level}`, 1, undefined, ['log', entry.level]);
  }

  public sendAlert(alert: Omit<Alert, 'timestamp'>): void {
    const fullAlert: Alert = {
      ...alert,
      timestamp: Date.now()
    };

    this.alerts.push(fullAlert);
    if (this.alerts.length > this.MAX_ALERTS) {
      this.alerts.shift();
    }

    // Notify alert handlers
    this.alertHandlers.forEach(handler => {
      try {
        handler(fullAlert);
      } catch (error) {
        console.error('Error in alert handler:', error);
      }
    });
  }

  public onAlert(handler: (alert: Alert) => void): () => void {
    this.alertHandlers.push(handler);
    return () => {
      this.alertHandlers = this.alertHandlers.filter(h => h !== handler);
    };
  }

  public getMetric(name: string): Metric | undefined {
    return this.metrics.get(name);
  }

  public getMetricValue(name: string): number | undefined {
    const metric = this.metrics.get(name);
    return metric?.values[metric.values.length - 1]?.value;
  }

  public getMetricsByTag(tag: string): Metric[] {
    return Array.from(this.metrics.values())
      .filter(metric => metric.tags?.includes(tag));
  }

  public getAllMetrics(): Metric[] {
    return Array.from(this.metrics.values());
  }

  public getAlerts(options: {
    type?: string;
    severity?: Alert['severity'];
    startTime?: number;
    endTime?: number;
  } = {}): Alert[] {
    return this.alerts.filter(alert => {
      if (options.type && alert.type !== options.type) return false;
      if (options.severity && alert.severity !== options.severity) return false;
      if (options.startTime && alert.timestamp < options.startTime) return false;
      if (options.endTime && alert.timestamp > options.endTime) return false;
      return true;
    });
  }

  public getLogs(options: {
    level?: string;
    startTime?: number;
    endTime?: number;
  } = {}): LogEntry[] {
    return this.logs.filter(log => {
      if (options.level && log.level !== options.level) return false;
      if (options.startTime && log.timestamp < options.startTime) return false;
      if (options.endTime && log.timestamp > options.endTime) return false;
      return true;
    });
  }

  public clearMetrics(): void {
    this.metrics.clear();
  }

  public clearAlerts(): void {
    this.alerts = [];
  }

  public clearLogs(): void {
    this.logs = [];
  }

  public getStats(): Record<string, number> {
    return {
      totalMetrics: this.metrics.size,
      totalAlerts: this.alerts.length,
      totalLogs: this.logs.length,
      errorCount: this.getMetricValue('error_count') || 0,
      averageHeapSize: this.calculateAverageMetric('heap_size') || 0,
      averagePageLoadTime: this.calculateAverageMetric('page_load_time') || 0
    };
  }

  private calculateAverageMetric(name: string): number | undefined {
    const metric = this.metrics.get(name);
    if (!metric || metric.values.length === 0) return undefined;
    
    const sum = metric.values.reduce((acc, val) => acc + val.value, 0);
    return sum / metric.values.length;
  }
}

export const monitoringService = MonitoringService.getInstance(); 