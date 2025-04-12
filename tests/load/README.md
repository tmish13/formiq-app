# FormIQ Load Testing Suite

This directory contains the load testing infrastructure for the FormIQ application. The suite is designed to simulate various user scenarios and measure application performance under different load conditions.

## Directory Structure

```
tests/load/
├── README.md               # This file
├── config.yaml            # Test configuration and scenarios
├── locustfile.py          # Locust test definitions
├── run_load_tests.py      # Test runner script
├── generate_sample_video.py # Script to generate test video
└── sample_video.mp4       # Sample video for form analysis tests
```

## Prerequisites

1. Python 3.8 or higher
2. Required packages:
   ```bash
   pip install locust pyyaml opencv-python numpy
   ```

## Setup

1. Generate the sample video for form analysis tests:
   ```bash
   python generate_sample_video.py
   ```
   This will create a 5-second sample video with a moving rectangle.

2. Make the test runner executable:
   ```bash
   chmod +x run_load_tests.py
   ```

## Configuration

The `config.yaml` file contains all test scenarios and parameters:

- **Normal Load**: 50 users, 5 users/sec spawn rate, 30 minutes duration
- **Peak Load**: 200 users, 20 users/sec spawn rate, 15 minutes duration
- **Stress Test**: 500 users, 50 users/sec spawn rate, 10 minutes duration
- **Endurance Test**: 100 users, 10 users/sec spawn rate, 2 hours duration

Additional configurations include:
- Performance thresholds
- Monitoring settings
- Reporting options

## Running Tests

1. Run a specific scenario:
   ```bash
   ./run_load_tests.py --scenario normal_load
   ```

2. Run all scenarios:
   ```bash
   ./run_load_tests.py --scenario all
   ```

## Test Scenarios

### FormIQUser
Simulates regular users performing common actions:
- Viewing form check history
- Submitting new form checks
- Browsing exercise library
- Updating user profile
- Searching exercises
- Filtering exercises

### AdminUser
Simulates administrative tasks:
- Viewing application metrics
- Managing user accounts

### WebsocketUser
Tests real-time features:
- Streaming form analysis data

## Reports

Test reports are generated in the configured output directory with the following structure:
```
reports/
└── scenario_name_YYYYMMDD_HHMMSS/
    ├── report.html          # HTML report
    ├── stats.csv           # Overall statistics
    ├── stats_history.csv   # Historical data
    └── failure.csv         # Failure details
```

## Performance Thresholds

The tests monitor the following metrics:
- 95th percentile response time: < 2000ms
- Error rate: < 1%

## Monitoring

The test suite integrates with:
- StatsD for metrics collection
- Graphite for visualization

## Troubleshooting

1. **Authentication Issues**
   - Ensure the test users have proper permissions
   - Check if the admin credentials are correct

2. **Video Upload Failures**
   - Verify the sample video file exists
   - Check file permissions
   - Ensure the video format is supported

3. **High Error Rates**
   - Check server logs
   - Verify API endpoints are accessible
   - Monitor server resources

## Contributing

When adding new test scenarios:
1. Update `config.yaml` with new scenario parameters
2. Add corresponding tasks in `locustfile.py`
3. Update this README with new scenario details 