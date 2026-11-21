#!/usr/bin/env python3
"""
Linux kernel-based fault injection using tc (traffic control) and iptables
"""
import subprocess
import sys

class FaultInjector:
    def __init__(self, interface='eth0'):
        self.interface = interface
    
    def inject_latency(self, delay_ms=100, jitter_ms=10):
        """Add network latency using tc (traffic control)"""
        try:
            # Clear existing rules
            subprocess.run(['tc', 'qdisc', 'del', 'dev', self.interface, 'root'], 
                          stderr=subprocess.DEVNULL)
            
            # Add latency with jitter
            cmd = [
                'tc', 'qdisc', 'add', 'dev', self.interface, 'root', 'netem',
                'delay', f'{delay_ms}ms', f'{jitter_ms}ms'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'Injected {delay_ms}ms latency (±{jitter_ms}ms jitter) on {self.interface}'
                }
            else:
                return {'success': False, 'error': result.stderr}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def inject_packet_loss(self, loss_percent=5):
        """Simulate packet loss using tc"""
        try:
            subprocess.run(['tc', 'qdisc', 'del', 'dev', self.interface, 'root'],
                          stderr=subprocess.DEVNULL)
            
            cmd = [
                'tc', 'qdisc', 'add', 'dev', self.interface, 'root', 'netem',
                'loss', f'{loss_percent}%'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'Injected {loss_percent}% packet loss on {self.interface}'
                }
            else:
                return {'success': False, 'error': result.stderr}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def inject_connection_drops(self, port=5432):
        """Drop connections to specific port using iptables"""
        try:
            cmd = [
                'iptables', '-A', 'OUTPUT', '-p', 'tcp',
                '--dport', str(port), '-j', 'DROP'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'Dropping connections to port {port}',
                    'port': port
                }
            else:
                return {'success': False, 'error': result.stderr}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def clear_all_faults(self):
        """Remove all fault injection rules"""
        results = []
        
        # Clear tc rules
        try:
            subprocess.run(['tc', 'qdisc', 'del', 'dev', self.interface, 'root'],
                          stderr=subprocess.DEVNULL)
            results.append('Cleared tc rules')
        except:
            pass
        
        # Clear iptables rules
        try:
            subprocess.run(['iptables', '-F', 'OUTPUT'], stderr=subprocess.DEVNULL)
            results.append('Cleared iptables rules')
        except:
            pass
        
        return {
            'success': True,
            'message': 'Cleared all fault injection rules',
            'details': results
        }

def main():
    if len(sys.argv) < 2:
        print("Usage: python fault_injector.py [latency|packet_loss|connection_drop|clear]")
        sys.exit(1)
    
    injector = FaultInjector()
    command = sys.argv[1]
    
    if command == 'latency':
        delay = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        result = injector.inject_latency(delay)
    
    elif command == 'packet_loss':
        loss = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        result = injector.inject_packet_loss(loss)
    
    elif command == 'connection_drop':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5432
        result = injector.inject_connection_drops(port)
    
    elif command == 'clear':
        result = injector.clear_all_faults()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    print(result)

if __name__ == '__main__':
    main()
