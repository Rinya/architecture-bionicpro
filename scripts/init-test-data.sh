#!/bin/bash
# BionicPRO Test Data Initialization - Linux/macOS version
# This script initializes test data in ClickHouse for demonstration

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Find script directory and navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/../docker-compose.yaml" ]; then
    cd "$SCRIPT_DIR/.."
elif [ -f "$SCRIPT_DIR/docker-compose.yaml" ]; then
    cd "$SCRIPT_DIR"
else
    echo -e "${RED}[ERROR] Cannot find docker-compose.yaml file!${NC}"
    echo "Please run from project root or scripts folder."
    exit 1
fi

echo "========================================"
echo "   BionicPRO Test Data Initialization"
echo "========================================"
echo ""

# Function to test ClickHouse connection
test_clickhouse() {
    echo -n "Testing ClickHouse connection... "
    if curl -s --max-time 10 "http://localhost:8123/ping" >/dev/null 2>&1; then
        echo -e "${GREEN}[✓] Connected${NC}"
        return 0
    else
        echo -e "${RED}[✗] Failed${NC}"
        return 1
    fi
}

# Function to execute ClickHouse query
execute_clickhouse() {
    local query="$1"
    local description="$2"

    echo -n "$description... "

    if curl -s --max-time 30 -X POST \
        "http://localhost:8123/" \
        --data-binary "$query" >/dev/null 2>&1; then
        echo -e "${GREEN}[✓] Success${NC}"
        return 0
    else
        echo -e "${RED}[✗] Failed${NC}"
        echo "Query: $query"
        return 1
    fi
}

# Wait for ClickHouse to be ready
echo -e "${BLUE}[INFO]${NC} Waiting for ClickHouse to be ready..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if test_clickhouse; then
        break
    fi

    if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}[ERROR] ClickHouse is not responding after $max_attempts attempts${NC}"
        echo "Please ensure ClickHouse container is running:"
        echo "  docker-compose ps clickhouse"
        echo "  docker-compose logs clickhouse"
        exit 1
    fi

    echo "Attempt $attempt/$max_attempts failed, retrying in 2 seconds..."
    sleep 2
    ((attempt++))
done

echo ""
echo -e "${BLUE}[INFO]${NC} ClickHouse is ready, initializing database..."

# Create database if not exists
execute_clickhouse "CREATE DATABASE IF NOT EXISTS bionicpro" "Creating database 'bionicpro'"

# Create users table
USER_TABLE_SQL="CREATE TABLE IF NOT EXISTS bionicpro.users (
    user_id String,
    username String,
    email String,
    created_at DateTime DEFAULT now(),
    is_active UInt8 DEFAULT 1
) ENGINE = MergeTree()
ORDER BY user_id"

execute_clickhouse "$USER_TABLE_SQL" "Creating users table"

# Create devices table
DEVICE_TABLE_SQL="CREATE TABLE IF NOT EXISTS bionicpro.devices (
    device_id String,
    user_id String,
    device_type String,
    model String,
    serial_number String,
    installation_date Date,
    is_active UInt8 DEFAULT 1
) ENGINE = MergeTree()
ORDER BY (user_id, device_id)"

execute_clickhouse "$DEVICE_TABLE_SQL" "Creating devices table"

# Create daily reports table (main data table)
REPORTS_TABLE_SQL="CREATE TABLE IF NOT EXISTS bionicpro.daily_reports (
    report_date Date,
    user_id String,
    device_id String,
    daily_usage_hours Float32,
    movement_efficiency Float32,
    maintenance_score Float32,
    battery_health Float32,
    anomaly_count UInt32,
    total_sessions UInt32,
    avg_session_duration Float32,
    max_pressure_reached Float32,
    last_sync DateTime
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (user_id, device_id, report_date)"

execute_clickhouse "$REPORTS_TABLE_SQL" "Creating daily_reports table"

# Create telemetry table for raw sensor data
TELEMETRY_TABLE_SQL="CREATE TABLE IF NOT EXISTS bionicpro.telemetry_raw (
    timestamp DateTime,
    device_id String,
    user_id String,
    sensor_type String,
    sensor_value Float32,
    unit String,
    quality_score Float32
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (device_id, sensor_type, timestamp)"

execute_clickhouse "$TELEMETRY_TABLE_SQL" "Creating telemetry_raw table"

echo ""
echo -e "${BLUE}[INFO]${NC} Inserting test data..."

# Insert test users
USERS_DATA="INSERT INTO bionicpro.users (user_id, username, email, created_at) VALUES
('user1', 'john_doe', 'john.doe@bionicpro.com', '2024-01-01 10:00:00'),
('user2', 'jane_smith', 'jane.smith@bionicpro.com', '2024-01-02 11:00:00'),
('user3', 'mike_wilson', 'mike.wilson@bionicpro.com', '2024-01-03 12:00:00'),
('admin', 'admin_user', 'admin@bionicpro.com', '2024-01-01 09:00:00')"

execute_clickhouse "$USERS_DATA" "Inserting test users"

# Insert test devices
DEVICES_DATA="INSERT INTO bionicpro.devices (device_id, user_id, device_type, model, serial_number, installation_date) VALUES
('esp32-001', 'user1', 'arm_prosthetic', 'BionicArm Pro v2.1', 'BA-2024-001', '2024-01-15'),
('esp32-002', 'user1', 'leg_prosthetic', 'BionicLeg Elite v1.8', 'BL-2024-001', '2024-01-20'),
('esp32-003', 'user2', 'arm_prosthetic', 'BionicArm Pro v2.1', 'BA-2024-002', '2024-01-25'),
('esp32-004', 'user3', 'leg_prosthetic', 'BionicLeg Elite v1.8', 'BL-2024-002', '2024-01-30')"

execute_clickhouse "$DEVICES_DATA" "Inserting test devices"

# Generate and insert test daily reports data
echo -n "Generating daily reports data for last 30 days... "

REPORTS_DATA="INSERT INTO bionicpro.daily_reports (
    report_date, user_id, device_id, daily_usage_hours, movement_efficiency,
    maintenance_score, battery_health, anomaly_count, total_sessions,
    avg_session_duration, max_pressure_reached, last_sync
) VALUES"

# Generate data for the last 30 days
for i in {0..29}; do
    date=$(date -d "$i days ago" +"%Y-%m-%d" 2>/dev/null || date -v -${i}d +"%Y-%m-%d" 2>/dev/null || echo "2024-01-31")

    # Data for user1, device esp32-001
    usage=$(( (RANDOM % 4) + 6 ))  # 6-10 hours
    efficiency=$(( 80 + (RANDOM % 20) ))  # 80-100%
    maintenance=$(( 85 + (RANDOM % 15) ))  # 85-100%
    battery=$(( 90 + (RANDOM % 10) ))  # 90-100%
    anomalies=$(( RANDOM % 3 ))  # 0-2 anomalies
    sessions=$(( 10 + (RANDOM % 10) ))  # 10-20 sessions
    session_duration=$(( 25 + (RANDOM % 20) ))  # 25-45 minutes
    max_pressure=$(( 400 + (RANDOM % 100) ))  # 400-500

    REPORTS_DATA="$REPORTS_DATA
('$date', 'user1', 'esp32-001', $usage, $efficiency, $maintenance, $battery, $anomalies, $sessions, $session_duration, $max_pressure, '$date 18:00:00'),"

    # Data for user1, device esp32-002
    usage=$(( (RANDOM % 3) + 7 ))
    efficiency=$(( 82 + (RANDOM % 18) ))
    maintenance=$(( 87 + (RANDOM % 13) ))
    battery=$(( 88 + (RANDOM % 12) ))
    anomalies=$(( RANDOM % 2 ))
    sessions=$(( 8 + (RANDOM % 8) ))
    session_duration=$(( 30 + (RANDOM % 15) ))
    max_pressure=$(( 350 + (RANDOM % 80) ))

    REPORTS_DATA="$REPORTS_DATA
('$date', 'user1', 'esp32-002', $usage, $efficiency, $maintenance, $battery, $anomalies, $sessions, $session_duration, $max_pressure, '$date 19:00:00'),"

    # Data for user2, device esp32-003
    if [ $i -le 20 ]; then  # Only 20 days of data for user2
        usage=$(( (RANDOM % 5) + 5 ))
        efficiency=$(( 78 + (RANDOM % 22) ))
        maintenance=$(( 83 + (RANDOM % 17) ))
        battery=$(( 86 + (RANDOM % 14) ))
        anomalies=$(( RANDOM % 4 ))
        sessions=$(( 12 + (RANDOM % 12) ))
        session_duration=$(( 28 + (RANDOM % 18) ))
        max_pressure=$(( 420 + (RANDOM % 90) ))

        REPORTS_DATA="$REPORTS_DATA
('$date', 'user2', 'esp32-003', $usage, $efficiency, $maintenance, $battery, $anomalies, $sessions, $session_duration, $max_pressure, '$date 17:30:00'),"
    fi

    # Data for user3, device esp32-004
    if [ $i -le 15 ]; then  # Only 15 days of data for user3
        usage=$(( (RANDOM % 6) + 4 ))
        efficiency=$(( 75 + (RANDOM % 25) ))
        maintenance=$(( 80 + (RANDOM % 20) ))
        battery=$(( 84 + (RANDOM % 16) ))
        anomalies=$(( RANDOM % 5 ))
        sessions=$(( 15 + (RANDOM % 15) ))
        session_duration=$(( 22 + (RANDOM % 25) ))
        max_pressure=$(( 380 + (RANDOM % 120) ))

        REPORTS_DATA="$REPORTS_DATA
('$date', 'user3', 'esp32-004', $usage, $efficiency, $maintenance, $battery, $anomalies, $sessions, $session_duration, $max_pressure, '$date 20:15:00'),"
    fi
done

# Remove the last comma and execute
REPORTS_DATA=$(echo "$REPORTS_DATA" | sed 's/,$//')
execute_clickhouse "$REPORTS_DATA" "Inserting daily reports data"

# Generate some raw telemetry data (sample)
echo -n "Generating raw telemetry data... "

TELEMETRY_DATA="INSERT INTO bionicpro.telemetry_raw (
    timestamp, device_id, user_id, sensor_type, sensor_value, unit, quality_score
) VALUES"

# Generate telemetry for today
today=$(date +"%Y-%m-%d")
for hour in {8..18}; do
    for minute in {0..59..15}; do  # Every 15 minutes
        timestamp="$today $(printf "%02d:%02d:00" $hour $minute)"

        # Pressure sensor data for esp32-001
        pressure=$(( 300 + (RANDOM % 200) ))
        quality=$(( 90 + (RANDOM % 10) ))
        TELEMETRY_DATA="$TELEMETRY_DATA
('$timestamp', 'esp32-001', 'user1', 'pressure', $pressure, 'kPa', 0.$quality),"

        # Temperature sensor data
        temp=$(( 35 + (RANDOM % 5) ))
        quality=$(( 88 + (RANDOM % 12) ))
        TELEMETRY_DATA="$TELEMETRY_DATA
('$timestamp', 'esp32-001', 'user1', 'temperature', $temp, 'celsius', 0.$quality),"

        # Battery voltage
        voltage=$(( 370 + (RANDOM % 30) ))
        quality=$(( 95 + (RANDOM % 5) ))
        TELEMETRY_DATA="$TELEMETRY_DATA
('$timestamp', 'esp32-001', 'user1', 'battery_voltage', $voltage, 'mV', 0.$quality),"
    done
done

# Remove the last comma and execute
TELEMETRY_DATA=$(echo "$TELEMETRY_DATA" | sed 's/,$//')
execute_clickhouse "$TELEMETRY_DATA" "Inserting raw telemetry data"

echo ""
echo -e "${BLUE}[INFO]${NC} Creating useful views and aggregations..."

# Create a view for user summaries
USER_SUMMARY_VIEW="CREATE VIEW IF NOT EXISTS bionicpro.user_summary AS
SELECT
    user_id,
    count() as total_reports,
    avg(daily_usage_hours) as avg_daily_usage,
    avg(movement_efficiency) as avg_efficiency,
    avg(maintenance_score) as avg_maintenance,
    avg(battery_health) as avg_battery_health,
    sum(anomaly_count) as total_anomalies,
    max(last_sync) as last_activity
FROM bionicpro.daily_reports
GROUP BY user_id"

execute_clickhouse "$USER_SUMMARY_VIEW" "Creating user summary view"

# Verify data was inserted correctly
echo ""
echo -e "${BLUE}[INFO]${NC} Verifying data insertion..."

# Count records
echo -n "Checking users count... "
users_count=$(curl -s "http://localhost:8123/" --data-binary "SELECT count() FROM bionicpro.users")
echo -e "${GREEN}$users_count users${NC}"

echo -n "Checking devices count... "
devices_count=$(curl -s "http://localhost:8123/" --data-binary "SELECT count() FROM bionicpro.devices")
echo -e "${GREEN}$devices_count devices${NC}"

echo -n "Checking daily reports count... "
reports_count=$(curl -s "http://localhost:8123/" --data-binary "SELECT count() FROM bionicpro.daily_reports")
echo -e "${GREEN}$reports_count daily reports${NC}"

echo -n "Checking telemetry records count... "
telemetry_count=$(curl -s "http://localhost:8123/" --data-binary "SELECT count() FROM bionicpro.telemetry_raw")
echo -e "${GREEN}$telemetry_count telemetry records${NC}"

echo ""
echo "========================================"
echo "    Test Data Summary"
echo "========================================"
echo ""

# Show sample data
echo "Sample user data:"
curl -s "http://localhost:8123/?default_format=PrettyCompact" --data-binary "
SELECT user_id, username, email
FROM bionicpro.users
ORDER BY user_id
LIMIT 5"

echo ""
echo "Sample recent reports:"
curl -s "http://localhost:8123/?default_format=PrettyCompact" --data-binary "
SELECT
    report_date,
    user_id,
    device_id,
    round(daily_usage_hours, 1) as usage_hrs,
    round(movement_efficiency, 1) as efficiency,
    battery_health
FROM bionicpro.daily_reports
WHERE report_date >= today() - 7
ORDER BY report_date DESC, user_id
LIMIT 10"

echo ""
echo "========================================"
echo "        Initialization Complete!"
echo "========================================"
echo ""

echo -e "${GREEN}✅ Test data has been successfully initialized!${NC}"
echo ""
echo "📊 Data Summary:"
echo "   Users: $users_count"
echo "   Devices: $devices_count"
echo "   Daily Reports: $reports_count"
echo "   Telemetry Records: $telemetry_count"
echo ""
echo "🔍 You can now:"
echo "   1. Test API endpoints with real data"
echo "   2. View reports in the frontend"
echo "   3. Explore data in ClickHouse directly"
echo ""
echo "💡 Useful queries:"
echo "   # View all users:"
echo "   curl 'http://localhost:8123/' -d 'SELECT * FROM bionicpro.users'"
echo ""
echo "   # Get latest reports for user1:"
echo "   curl 'http://localhost:8123/' -d 'SELECT * FROM bionicpro.daily_reports WHERE user_id=\"user1\" ORDER BY report_date DESC LIMIT 5'"
echo ""
echo "   # Check user summaries:"
echo "   curl 'http://localhost:8123/' -d 'SELECT * FROM bionicpro.user_summary'"
echo ""

echo "🎯 Next step: Run the API tests to verify everything works!"
echo "   ./scripts/step5-functionality-test.sh"