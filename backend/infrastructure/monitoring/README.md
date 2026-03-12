# FormIQ Monitoring Infrastructure

This directory contains the monitoring and alerting configuration for the FormIQ backend system.

## Overview

The monitoring system is built around **Prometheus** for metrics collection and **AlertManager** for alert routing and notification. The system provides comprehensive observability across all critical components of the FormIQ platform.

## Components

### Prometheus Configuration

- **`prometheus.yml`** - Main Prometheus configuration with scrape targets and global settings
- **`alert_rules.yml`** - Alert rules for all system components with appropriate thresholds
- **`recording_rules.yml`** - Pre-computed queries for performance optimization

### Monitored Components

1. **API Layer**
   - HTTP request metrics (latency, success rate, throughput)
   - Endpoint-specific performance tracking
   - Authentication and authorization metrics

2. **AI/ML Pipeline**
   - Frame processing performance (sub-300ms target)
   - Model inference duration and confidence scores
   - Video processing success rates

3. **Database**
   - Query performance and connection pool utilization
   - Index effectiveness and slow query detection

4. **External Services**
   - Circuit breaker state monitoring
   - S3 and OpenAI API integration health

5. **System Resources**
   - CPU, memory, and disk utilization
   - System-level performance tracking

## Alert Severity Levels

### Critical (Immediate Response Required)
- Service unavailable
- Critical API error rates (>10%)
- Circuit breakers open
- System resource exhaustion

### Warning (Investigation Required)
- High error rates (5-10%)
- Performance degradation
- High resource usage (80%+)
- Business metric anomalies

### Info (Monitoring Only)
- Low user activity
- Non-critical system events

## SLA Monitoring

The system monitors compliance with the following SLAs:

| Component | Metric | Target | Alert Threshold |
|-----------|--------|---------|-----------------|
| API | Success Rate | ≥ 99.9% | < 95% (warning), < 90% (critical) |
| API | P95 Latency | ≤ 300ms | > 1s (warning), > 3s (critical) |
| Frame Processing | P95 Duration | ≤ 300ms | > 300ms (warning) |
| Frame Processing | Success Rate | ≥ 99% | < 95% (warning) |
| Database | P95 Query Time | ≤ 2s | > 2s (warning) |

## Setup Instructions

### 1. Install Prometheus

```bash
# Download and install Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xvfz prometheus-2.40.0.linux-amd64.tar.gz
cd prometheus-2.40.0.linux-amd64
```

### 2. Configure Prometheus

```bash
# Copy configuration files
cp prometheus/prometheus.yml /etc/prometheus/
cp prometheus/alert_rules.yml /etc/prometheus/
cp prometheus/recording_rules.yml /etc/prometheus/

# Set proper permissions
chown -R prometheus:prometheus /etc/prometheus/
```

### 3. Start Prometheus

```bash
# Start Prometheus with configuration
./prometheus --config.file=/etc/prometheus/prometheus.yml \
             --storage.tsdb.path=/var/lib/prometheus/ \
             --web.console.templates=/etc/prometheus/consoles \
             --web.console.libraries=/etc/prometheus/console_libraries \
             --web.listen-address=:9090 \
             --web.enable-lifecycle
```

### 4. Verify Configuration

```bash
# Check configuration validity
./promtool check config /etc/prometheus/prometheus.yml
./promtool check rules /etc/prometheus/alert_rules.yml
./promtool check rules /etc/prometheus/recording_rules.yml
```

## Usage

### Accessing Prometheus UI

Navigate to `http://localhost:9090` to access the Prometheus web interface.

### Key Queries for Monitoring

```promql
# API success rate over last 5 minutes
formiq:api:success_rate_5m

# Frame processing P95 latency
formiq:frame_processing:p95_duration_5m

# Active circuit breakers
circuit_breaker_state > 1

# Database connection utilization
formiq:db:connection_utilization

# Overall SLA compliance score
formiq:sla:overall_score_5m
```

### Grafana Dashboards

Import the provided dashboard configurations to visualize:

- API performance and error rates
- AI pipeline processing times
- System resource utilization
- Business metrics and user activity
- SLA compliance tracking

## Alert Configuration

### AlertManager Integration

Configure AlertManager to route alerts to appropriate channels:

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  receiver: 'formiq-alerts'

receivers:
  - name: 'formiq-alerts'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        title: 'FormIQ Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### Notification Channels

Configure notifications for different severity levels:

- **Critical**: Immediate PagerDuty + Slack
- **Warning**: Slack notifications during business hours
- **Info**: Dashboard visibility only

## Maintenance

### Rule Updates

To update alert or recording rules:

```bash
# Validate changes
./promtool check rules /etc/prometheus/alert_rules.yml

# Reload Prometheus configuration
curl -X POST http://localhost:9090/-/reload
```

### Performance Tuning

Monitor Prometheus performance:

```bash
# Check Prometheus metrics
curl http://localhost:9090/metrics | grep prometheus_

# Monitor storage usage
du -sh /var/lib/prometheus/
```

### Retention Management

Current retention settings:
- **Time-based**: 30 days
- **Size-based**: 10GB maximum

Adjust in `prometheus.yml` under the `storage` section.

## Troubleshooting

### Common Issues

1. **High cardinality metrics**
   - Monitor series count: `prometheus_tsdb_symbol_table_size_bytes`
   - Review label usage in custom metrics

2. **Slow queries**
   - Use recording rules for complex calculations
   - Monitor query performance in Prometheus UI

3. **Missing metrics**
   - Verify service discovery configuration
   - Check scrape target health in Prometheus UI

### Debug Commands

```bash
# Check target health
curl http://localhost:9090/api/v1/targets

# Validate rules
./promtool query instant 'formiq:api:success_rate_5m'

# Check alert evaluation
curl http://localhost:9090/api/v1/alerts
```

## Integration with FormIQ Backend

The FormIQ backend exposes metrics at `/metrics` endpoint. Key integration points:

### Custom Metrics

The application tracks:
- Request/response metrics via middleware
- Business logic metrics in services
- AI pipeline performance in processing tasks
- Database metrics in repository layer

### Health Checks

Monitor application health:
- `/health` endpoint for basic availability
- `/metrics` endpoint for detailed performance data
- Circuit breaker states for external dependencies

## Production Deployment

### High Availability

For production, deploy Prometheus in HA mode:

```yaml
# prometheus-ha.yml
global:
  external_labels:
    replica: 'prometheus-1'  # Unique per instance

# Use shared storage for rules
rule_files:
  - /shared/rules/*.yml
```

### Resource Requirements

**Minimum Production Requirements:**
- CPU: 4 cores
- Memory: 8GB RAM
- Storage: 100GB SSD with high IOPS
- Network: Low latency to monitored services

### Backup Strategy

Implement regular backups of:
- Prometheus data directory
- Configuration files
- Alert/recording rules

```bash
# Automated backup script
tar czf prometheus-backup-$(date +%Y%m%d).tar.gz \
    /var/lib/prometheus/ \
    /etc/prometheus/
```

---

**Last Updated**: December 6, 2024  
**Maintainer**: FormIQ DevOps Team  
**Documentation Version**: 1.0