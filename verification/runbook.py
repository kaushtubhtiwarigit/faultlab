#!/usr/bin/env python3
"""
Automated diagnostic runbook for incident triage
"""
import subprocess
import socket
import time
import requests
from datetime import datetime

class DiagnosticRunbook:
    def __init__(self):
        self.results = []
        self.severity = 'OK'
    
    def log_check(self, name, status, message, details=None):
        """Log a diagnostic check result"""
        self.results.append({
            'check': name,
            'status': status,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
        if status in ['CRITICAL', 'ERROR']:
            self.severity = 'CRITICAL'
        elif status == 'WARNING' and self.severity == 'OK':
            self.severity = 'WARNING'
    
    def check_dns(self, hostname='postgres'):
        """DNS Resolution Check"""
        try:
            ip = socket.gethostbyname(hostname)
            self.log_check(
                'DNS Resolution',
                'OK',
                f'{hostname} resolves to {ip}'
            )
            return True
        except socket.gaierror:
            self.log_check(
                'DNS Resolution',
                'CRITICAL',
                f'Failed to resolve {hostname}'
            )
            return False
    
    def check_tcp_port(self, host, port, service_name):
        """TCP Port Connectivity Check"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                self.log_check(
                    f'TCP Connectivity ({service_name})',
                    'OK',
                    f'{host}:{port} is reachable'
                )
                return True
            else:
                self.log_check(
                    f'TCP Connectivity ({service_name})',
                    'CRITICAL',
                    f'{host}:{port} connection refused'
                )
                return False
        except Exception as e:
            self.log_check(
                f'TCP Connectivity ({service_name})',
                'CRITICAL',
                f'Error connecting to {host}:{port}: {str(e)}'
            )
            return False
    
    def check_http_endpoint(self, url, expected_status=200):
        """HTTP Endpoint Health Check"""
        try:
            start = time.time()
            response = requests.get(url, timeout=5)
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code == expected_status:
                self.log_check(
                    'HTTP Endpoint',
                    'OK',
                    f'{url} returned {response.status_code}',
                    {'latency_ms': latency_ms}
                )
                return True
            else:
                self.log_check(
                    'HTTP Endpoint',
                    'WARNING',
                    f'{url} returned {response.status_code} (expected {expected_status})',
                    {'latency_ms': latency_ms}
                )
                return False
        
        except requests.exceptions.Timeout:
            self.log_check(
                'HTTP Endpoint',
                'CRITICAL',
                f'{url} timed out (>5s)'
            )
            return False
        except Exception as e:
            self.log_check(
                'HTTP Endpoint',
                'CRITICAL',
                f'{url} error: {str(e)}'
            )
            return False
    
    def check_redis_connection(self, host='redis', port=6379):
        """Redis Connection Check"""
        try:
            import redis
            client = redis.Redis(host=host, port=port, socket_timeout=3)
            client.ping()
            
            # Check queue length
            queue_len = client.llen('order_queue')
            
            self.log_check(
                'Redis Connection',
                'OK',
                f'Redis connected, queue length: {queue_len}',
                {'queue_length': queue_len}
            )
            return True
        except Exception as e:
            self.log_check(
                'Redis Connection',
                'CRITICAL',
                f'Redis connection failed: {str(e)}'
            )
            return False
    
    def check_database_connection(self, host='postgres', port=5432):
        """PostgreSQL Connection Check"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=host,
                port=port,
                database='orders',
                user='faultlab',
                password='chaos123',
                connect_timeout=3
            )
            
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM orders')
            order_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            self.log_check(
                'Database Connection',
                'OK',
                f'PostgreSQL connected, {order_count} orders in DB',
                {'order_count': order_count}
            )
            return True
        except Exception as e:
            self.log_check(
                'Database Connection',
                'CRITICAL',
                f'PostgreSQL connection failed: {str(e)}'
            )
            return False
    
    def check_network_latency(self, host='8.8.8.8'):
        """Network Latency Check (ping)"""
        try:
            # Windows-compatible ping
            result = subprocess.run(
                ['ping', '-n', '3', host] if subprocess.os.name == 'nt' else ['ping', '-c', '3', host],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.log_check(
                    'Network Latency',
                    'OK',
                    f'Ping to {host} successful'
                )
                return True
            else:
                self.log_check(
                    'Network Latency',
                    'WARNING',
                    f'Ping to {host} failed or high latency'
                )
                return False
        except Exception as e:
            self.log_check(
                'Network Latency',
                'WARNING',
                f'Latency check error: {str(e)}'
            )
            return False
    
    def run_full_diagnostic(self):
        """Execute complete diagnostic runbook"""
        print("\n" + "="*60)
        print("🔧 FaultLab Diagnostic Runbook")
        print("="*60 + "\n")
        
        print("Running diagnostics...\n")
        
        # Layer 1: DNS
        print("📡 Layer 1: DNS Resolution")
        self.check_dns('postgres')
        self.check_dns('redis')
        
        # Layer 2: TCP Connectivity
        print("\n🔌 Layer 2: TCP Connectivity")
        self.check_tcp_port('postgres', 5432, 'PostgreSQL')
        self.check_tcp_port('redis', 6379, 'Redis')
        
        # Layer 3: Service Health
        print("\n🏥 Layer 3: Service Health")
        self.check_http_endpoint('http://localhost:3000/health')
        self.check_redis_connection()
        self.check_database_connection()
        
        # Layer 4: Network Performance
        print("\n📊 Layer 4: Network Performance")
        self.check_network_latency()
        
        # Summary
        print("\n" + "="*60)
        print(f"Diagnostic Complete - Overall Status: {self.severity}")
        print("="*60 + "\n")
        
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """Print diagnostic summary"""
        status_counts = {'OK': 0, 'WARNING': 0, 'CRITICAL': 0}
        
        for result in self.results:
            status_counts[result['status']] = status_counts.get(result['status'], 0) + 1
        
        print(f"✓ Passed: {status_counts['OK']}")
        print(f"⚠ Warnings: {status_counts['WARNING']}")
        print(f"✗ Critical: {status_counts['CRITICAL']}")
        
        if status_counts['CRITICAL'] > 0:
            print("\n❌ Critical Issues Found:")
            for result in self.results:
                if result['status'] == 'CRITICAL':
                    print(f"   • {result['check']}: {result['message']}")
        
        if status_counts['WARNING'] > 0:
            print("\n⚠️  Warnings:")
            for result in self.results:
                if result['status'] == 'WARNING':
                    print(f"   • {result['check']}: {result['message']}")

if __name__ == '__main__':
    runbook = DiagnosticRunbook()
    runbook.run_full_diagnostic()
