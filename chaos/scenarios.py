#!/usr/bin/env python3
"""
Predefined chaos engineering scenarios
"""
import time
import subprocess
from fault_injector import FaultInjector

class ChaosScenario:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.injector = FaultInjector()
    
    def execute(self):
        raise NotImplementedError

class LatencySpike(ChaosScenario):
    """Simulate network latency spike"""
    def __init__(self, delay_ms=200):
        super().__init__(
            'Latency Spike',
            f'Inject {delay_ms}ms network latency'
        )
        self.delay_ms = delay_ms
    
    def execute(self):
        print(f"\n🔥 CHAOS: {self.name}")
        print(f"   {self.description}")
        result = self.injector.inject_latency(self.delay_ms, jitter_ms=50)
        print(f"   Result: {result['message']}")
        return result

class DatabaseFailure(ChaosScenario):
    """Simulate database connection failure"""
    def __init__(self):
        super().__init__(
            'Database Connection Drop',
            'Block all connections to PostgreSQL'
        )
    
    def execute(self):
        print(f"\n🔥 CHAOS: {self.name}")
        print(f"   {self.description}")
        result = self.injector.inject_connection_drops(port=5432)
        print(f"   Result: {result['message']}")
        return result

class RedisFailure(ChaosScenario):
    """Simulate Redis connection failure"""
    def __init__(self):
        super().__init__(
            'Redis Connection Drop',
            'Block all connections to Redis'
        )
    
    def execute(self):
        print(f"\n🔥 CHAOS: {self.name}")
        print(f"   {self.description}")
        result = self.injector.inject_connection_drops(port=6379)
        print(f"   Result: {result['message']}")
        return result

class PacketLoss(ChaosScenario):
    """Simulate packet loss"""
    def __init__(self, loss_percent=10):
        super().__init__(
            'Packet Loss',
            f'Inject {loss_percent}% packet loss'
        )
        self.loss_percent = loss_percent
    
    def execute(self):
        print(f"\n🔥 CHAOS: {self.name}")
        print(f"   {self.description}")
        result = self.injector.inject_packet_loss(self.loss_percent)
        print(f"   Result: {result['message']}")
        return result

class CascadingFailure(ChaosScenario):
    """Multi-layer failure simulation"""
    def __init__(self):
        super().__init__(
            'Cascading Failure',
            'Latency → Packet Loss → Database Drop'
        )
    
    def execute(self):
        print(f"\n🔥 CHAOS: {self.name}")
        print(f"   {self.description}")
        
        print("\n   Step 1: Inject latency...")
        self.injector.inject_latency(100, 20)
        time.sleep(5)
        
        print("   Step 2: Add packet loss...")
        self.injector.inject_packet_loss(5)
        time.sleep(5)
        
        print("   Step 3: Drop database connections...")
        result = self.injector.inject_connection_drops(5432)
        
        return result

# Scenario registry
SCENARIOS = {
    'latency': LatencySpike(200),
    'db_fail': DatabaseFailure(),
    'redis_fail': RedisFailure(),
    'packet_loss': PacketLoss(10),
    'cascading': CascadingFailure()
}

def run_scenario(scenario_name, duration_seconds=30):
    """Run a chaos scenario for specified duration"""
    if scenario_name not in SCENARIOS:
        print(f"❌ Unknown scenario: {scenario_name}")
        print(f"Available: {list(SCENARIOS.keys())}")
        return
    
    scenario = SCENARIOS[scenario_name]
    
    print(f"\n{'='*60}")
    print(f"Starting chaos scenario: {scenario.name}")
    print(f"Duration: {duration_seconds}s")
    print(f"{'='*60}")
    
    scenario.execute()
    
    print(f"\n⏳ Chaos active for {duration_seconds} seconds...")
    print("   (Monitor Jaeger at http://localhost:16686)")
    
    time.sleep(duration_seconds)
    
    print("\n🧹 Cleaning up...")
    injector = FaultInjector()
    result = injector.clear_all_faults()
    print(f"   {result['message']}")
    
    print("\n✅ Scenario complete!")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python scenarios.py [scenario_name] [duration_seconds]")
        print(f"\nAvailable scenarios: {list(SCENARIOS.keys())}")
        sys.exit(1)
    
    scenario_name = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    run_scenario(scenario_name, duration)
