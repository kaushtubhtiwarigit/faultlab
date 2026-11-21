#!/bin/bash
# FaultLab experiment runner

set -e

echo "🧪 FaultLab Chaos Engineering Experiment"
echo "========================================"
echo ""

# Check if docker-compose is running
if ! docker-compose ps | grep -q "Up"; then
    echo "⚠️  Services not running. Starting..."
    docker-compose up -d
    sleep 10
fi

echo "✓ Services are running"
echo ""

# Baseline traffic
echo "📊 Phase 1: Baseline (no faults)"
echo "Generating 10 orders..."
for i in {1..10}; do
    curl -s -X POST http://localhost:3000/orders \
        -H "Content-Type: application/json" \
        -d "{\"customer_id\": \"CUST-$i\", \"amount\": 99.99}" > /dev/null
    echo -n "."
done
echo " Done!"
sleep 2

# Inject chaos
SCENARIO=${1:-latency}
DURATION=${2:-30}

echo ""
echo "🔥 Phase 2: Chaos Injection"
echo "Scenario: $SCENARIO"
echo "Duration: ${DURATION}s"
echo ""

# Run scenario in background
docker exec faultlab-api-gateway-1 python chaos/scenarios.py $SCENARIO $DURATION &
CHAOS_PID=$!

sleep 5

# Traffic under chaos
echo "Generating traffic under chaos..."
for i in {11..20}; do
    curl -s -X POST http://localhost:3000/orders \
        -H "Content-Type: application/json" \
        -d "{\"customer_id\": \"CUST-$i\", \"amount\": 149.99}" > /dev/null
    echo -n "."
    sleep 1
done
echo " Done!"

# Wait for chaos to finish
wait $CHAOS_PID

echo ""
echo "🔍 Phase 3: Analysis"
echo ""

# Run diagnostics
python verification/runbook.py

echo ""
echo "📈 View detailed traces at: http://localhost:16686"
echo ""
echo "✅ Experiment complete!"
