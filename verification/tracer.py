#!/usr/bin/env python3
"""
OpenTelemetry trace analysis and bottleneck detection
"""
import requests
import time
from datetime import datetime, timedelta

class TraceAnalyzer:
    def __init__(self, jaeger_url='http://localhost:16686'):
        self.jaeger_url = jaeger_url
        self.api_url = f'{jaeger_url}/api'
    
    def get_services(self):
        """List all instrumented services"""
        try:
            response = requests.get(f'{self.api_url}/services')
            return response.json()['data']
        except Exception as e:
            return {'error': str(e)}
    
    def get_traces(self, service='api-gateway', lookback_minutes=10, limit=20):
        """Fetch recent traces for a service"""
        try:
            lookback_micros = lookback_minutes * 60 * 1000000
            
            params = {
                'service': service,
                'lookback': f'{lookback_micros}us',
                'limit': limit
            }
            
            response = requests.get(f'{self.api_url}/traces', params=params)
            data = response.json()
            
            if 'data' not in data:
                return []
            
            return data['data']
        
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_trace(self, trace):
        """Analyze a single trace for bottlenecks"""
        if 'spans' not in trace:
            return None
        
        spans = trace['spans']
        
        # Calculate total duration
        start_times = [span['startTime'] for span in spans]
        end_times = [span['startTime'] + span['duration'] for span in spans]
        
        total_duration_us = max(end_times) - min(start_times)
        total_duration_ms = total_duration_us / 1000
        
        # Find slowest spans
        span_durations = []
        for span in spans:
            span_durations.append({
                'operation': span['operationName'],
                'service': span['process']['serviceName'],
                'duration_ms': span['duration'] / 1000,
                'tags': {tag['key']: tag['value'] for tag in span.get('tags', [])}
            })
        
        span_durations.sort(key=lambda x: x['duration_ms'], reverse=True)
        
        # Check for errors
        errors = []
        for span in spans:
            tags = {tag['key']: tag['value'] for tag in span.get('tags', [])}
            if tags.get('error') == 'true' or tags.get('otel.status_code') == 'ERROR':
                errors.append({
                    'operation': span['operationName'],
                    'service': span['process']['serviceName'],
                    'error_message': tags.get('error.message', 'Unknown error')
                })
        
        return {
            'trace_id': trace['traceID'],
            'total_duration_ms': total_duration_ms,
            'span_count': len(spans),
            'slowest_spans': span_durations[:5],
            'errors': errors,
            'has_errors': len(errors) > 0
        }
    
    def find_bottlenecks(self, service='api-gateway', lookback_minutes=10):
        """Identify performance bottlenecks in recent traces"""
        print(f"\n🔍 Analyzing traces for {service} (last {lookback_minutes} minutes)...")
        
        traces = self.get_traces(service, lookback_minutes)
        
        if isinstance(traces, dict) and 'error' in traces:
            print(f"❌ Error fetching traces: {traces['error']}")
            return
        
        if not traces:
            print("⚠️  No traces found")
            return
        
        print(f"✓ Found {len(traces)} traces\n")
        
        analyzed = []
        for trace in traces:
            result = self.analyze_trace(trace)
            if result:
                analyzed.append(result)
        
        # Calculate statistics
        durations = [t['total_duration_ms'] for t in analyzed]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        error_count = sum(1 for t in analyzed if t['has_errors'])
        
        print("📊 Summary Statistics:")
        print(f"   Average duration: {avg_duration:.2f}ms")
        print(f"   Max duration: {max_duration:.2f}ms")
        print(f"   Error rate: {error_count}/{len(analyzed)} ({error_count*100/len(analyzed):.1f}%)")
        
        # Find common bottlenecks
        operation_times = {}
        for trace in analyzed:
            for span in trace['slowest_spans']:
                op = span['operation']
                if op not in operation_times:
                    operation_times[op] = []
                operation_times[op].append(span['duration_ms'])
        
        print("\n🐌 Slowest Operations (avg):")
        op_avgs = {op: sum(times)/len(times) for op, times in operation_times.items()}
        for op, avg in sorted(op_avgs.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   {op}: {avg:.2f}ms")
        
        # Show errors
        if error_count > 0:
            print(f"\n❌ Errors detected in {error_count} traces:")
            for trace in analyzed:
                if trace['has_errors']:
                    for error in trace['errors']:
                        print(f"   {error['service']}.{error['operation']}: {error['error_message']}")
        
        return analyzed

if __name__ == '__main__':
    import sys
    
    analyzer = TraceAnalyzer()
    
    if len(sys.argv) > 1:
        service = sys.argv[1]
    else:
        service = 'api-gateway'
    
    lookback = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    analyzer.find_bottlenecks(service, lookback)
