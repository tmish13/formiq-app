import { MonitoringService } from './monitoringService';

interface PerformanceMetrics {
  timeToFirstByte: number;
  timeToFirstPaint: number;
  timeToFirstContentfulPaint: number;
  timeToInteractive: number;
  largestContentfulPaint: number;
  firstInputDelay: number;
  cumulativeLayoutShift: number;
  memoryUsage: MemoryInfo;
  resourceTimings: ResourceTiming[];
}

interface MemoryInfo {
  jsHeapSizeLimit: number;
  totalJSHeapSize: number;
  usedJSHeapSize: number;
  peakUsage: number;
}

interface ResourceTiming {
  name: string;
  initiatorType: string;
  duration: number;
  transferSize: number;
  encodedBodySize: number;
  decodedBodySize: number;
}

export class PerformanceService {
  private static instance: PerformanceService;
  private monitoring: MonitoringService;
  private metricsBuffer: PerformanceMetrics[] = [];
  private readonly BUFFER_SIZE = 100;
  private isMonitoring = false;

  private constructor() {
    this.monitoring = MonitoringService.getInstance();
    this.initializePerformanceObservers();
  }

  public static getInstance(): PerformanceService {
    if (!PerformanceService.instance) {
      PerformanceService.instance = new PerformanceService();
    }
    return PerformanceService.instance;
  }

  private initializePerformanceObservers(): void {
    // Observe paint timing
    if ('PerformanceObserver' in window) {
      // First Paint & First Contentful Paint
      const paintObserver = new PerformanceObserver((entries) => {
        entries.getEntries().forEach((entry) => {
          this.monitoring.trackMetric(`paint_${entry.name}`, entry.startTime);
        });
      });
      paintObserver.observe({ entryTypes: ['paint'] });

      // Largest Contentful Paint
      const lcpObserver = new PerformanceObserver((entries) => {
        const lastEntry = entries.getEntries().pop();
        if (lastEntry) {
          this.monitoring.trackMetric('largest_contentful_paint', lastEntry.startTime);
        }
      });
      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });

      // First Input Delay
      const fidObserver = new PerformanceObserver((entries) => {
        entries.getEntries().forEach((entry) => {
          const eventEntry = entry as PerformanceEventTiming;
          this.monitoring.trackMetric('first_input_delay', eventEntry.processingStart - entry.startTime);
        });
      });
      fidObserver.observe({ entryTypes: ['first-input'] });

      // Cumulative Layout Shift
      const clsObserver = new PerformanceObserver((entries) => {
        let cumulativeLayoutShift = 0;
        entries.getEntries().forEach((entry: any) => {
          if (!entry.hadRecentInput) {
            cumulativeLayoutShift += entry.value;
          }
        });
        this.monitoring.trackMetric('cumulative_layout_shift', cumulativeLayoutShift);
      });
      clsObserver.observe({ entryTypes: ['layout-shift'] });

      // Resource Timing
      const resourceObserver = new PerformanceObserver((entries) => {
        entries.getEntries().forEach((entry) => {
          this.trackResourceTiming(entry as PerformanceResourceTiming);
        });
      });
      resourceObserver.observe({ entryTypes: ['resource'] });
    }
  }

  public startMonitoring(): void {
    if (this.isMonitoring) return;
    this.isMonitoring = true;

    // Start periodic performance checks
    setInterval(() => {
      this.collectMetrics();
    }, 60000); // Every minute

    // Track initial page load metrics
    window.addEventListener('load', () => {
      this.collectMetrics();
    });
  }

  private async collectMetrics(): Promise<void> {
    const metrics: PerformanceMetrics = {
      timeToFirstByte: this.getTimeToFirstByte(),
      timeToFirstPaint: this.getTimeToFirstPaint(),
      timeToFirstContentfulPaint: this.getTimeToFirstContentfulPaint(),
      timeToInteractive: await this.getTimeToInteractive(),
      largestContentfulPaint: this.getLargestContentfulPaint(),
      firstInputDelay: this.getFirstInputDelay(),
      cumulativeLayoutShift: this.getCumulativeLayoutShift(),
      memoryUsage: this.getMemoryUsage(),
      resourceTimings: this.getResourceTimings()
    };

    this.metricsBuffer.push(metrics);
    if (this.metricsBuffer.length > this.BUFFER_SIZE) {
      this.metricsBuffer.shift();
    }

    // Pass only the numeric scalar fields to trackMetrics (excludes memoryUsage / resourceTimings objects)
    this.monitoring.trackMetrics({
      timeToFirstByte: metrics.timeToFirstByte,
      timeToFirstPaint: metrics.timeToFirstPaint,
      timeToFirstContentfulPaint: metrics.timeToFirstContentfulPaint,
      timeToInteractive: metrics.timeToInteractive,
      largestContentfulPaint: metrics.largestContentfulPaint,
      firstInputDelay: metrics.firstInputDelay,
      cumulativeLayoutShift: metrics.cumulativeLayoutShift,
    });
    this.analyzePerformance(metrics);
  }

  private getTimeToFirstByte(): number {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    return navigation ? navigation.responseStart - navigation.requestStart : 0;
  }

  private getTimeToFirstPaint(): number {
    const paint = performance.getEntriesByName('first-paint')[0];
    return paint ? paint.startTime : 0;
  }

  private getTimeToFirstContentfulPaint(): number {
    const paint = performance.getEntriesByName('first-contentful-paint')[0];
    return paint ? paint.startTime : 0;
  }

  private async getTimeToInteractive(): Promise<number> {
    return new Promise((resolve) => {
      if ('requestIdleCallback' in window) {
        (window as any).requestIdleCallback(() => {
          const navigationEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
          resolve(navigationEntry ? navigationEntry.domInteractive : 0);
        });
      } else {
        setTimeout(() => {
          const navigationEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined;
          resolve(navigationEntry ? navigationEntry.domInteractive : 0);
        }, 0);
      }
    });
  }

  private getLargestContentfulPaint(): number {
    const lcp = performance.getEntriesByType('largest-contentful-paint').pop();
    return lcp ? lcp.startTime : 0;
  }

  private getFirstInputDelay(): number {
    const fid = performance.getEntriesByType('first-input')[0] as PerformanceEventTiming | undefined;
    return fid ? fid.processingStart - fid.startTime : 0;
  }

  private getCumulativeLayoutShift(): number {
    return (window as any).cumulativeLayoutShiftScore || 0;
  }

  private getMemoryUsage(): MemoryInfo {
    const memory = (performance as any).memory || {};
    return {
      jsHeapSizeLimit: memory.jsHeapSizeLimit || 0,
      totalJSHeapSize: memory.totalJSHeapSize || 0,
      usedJSHeapSize: memory.usedJSHeapSize || 0,
      peakUsage: memory.peakUsage || 0
    };
  }

  private getResourceTimings(): ResourceTiming[] {
    return performance.getEntriesByType('resource').map(entry => {
      const r = entry as PerformanceResourceTiming;
      return {
        name: r.name,
        initiatorType: r.initiatorType,
        duration: r.duration,
        transferSize: r.transferSize,
        encodedBodySize: r.encodedBodySize,
        decodedBodySize: r.decodedBodySize
      };
    });
  }

  private trackResourceTiming(entry: PerformanceResourceTiming): void {
    const timing: ResourceTiming = {
      name: entry.name,
      initiatorType: entry.initiatorType,
      duration: entry.duration,
      transferSize: entry.transferSize,
      encodedBodySize: entry.encodedBodySize,
      decodedBodySize: entry.decodedBodySize
    };

    this.monitoring.trackMetric(`resource_${entry.initiatorType}`, timing.duration);
  }

  private analyzePerformance(metrics: PerformanceMetrics): void {
    // Check for performance issues
    if (metrics.timeToFirstContentfulPaint > 3000) {
      this.monitoring.sendAlert({
        type: 'performance_warning',
        severity: 'warning' as const,
        message: 'High First Contentful Paint time detected',
        details: {
          metric: 'FCP',
          value: metrics.timeToFirstContentfulPaint,
          threshold: 3000
        }
      });
    }

    if (metrics.largestContentfulPaint > 4000) {
      this.monitoring.sendAlert({
        type: 'performance_warning',
        severity: 'warning' as const,
        message: 'High Largest Contentful Paint time detected',
        details: {
          metric: 'LCP',
          value: metrics.largestContentfulPaint,
          threshold: 4000
        }
      });
    }

    if (metrics.cumulativeLayoutShift > 0.1) {
      this.monitoring.sendAlert({
        type: 'performance_warning',
        severity: 'warning' as const,
        message: 'High Cumulative Layout Shift detected',
        details: {
          metric: 'CLS',
          value: metrics.cumulativeLayoutShift,
          threshold: 0.1
        }
      });
    }

    // Check memory usage
    const memoryUsagePercent = (metrics.memoryUsage.usedJSHeapSize / metrics.memoryUsage.jsHeapSizeLimit) * 100;
    if (memoryUsagePercent > 80) {
      this.monitoring.sendAlert({
        type: 'performance_warning',
        severity: 'warning' as const,
        message: 'High memory usage detected',
        details: {
          metric: 'Memory',
          value: memoryUsagePercent,
          threshold: 80
        }
      });
    }
  }

  public getMetricsHistory(): PerformanceMetrics[] {
    return [...this.metricsBuffer];
  }

  public clearMetricsHistory(): void {
    this.metricsBuffer = [];
    performance.clearResourceTimings();
  }
}

export const performanceService = PerformanceService.getInstance(); 