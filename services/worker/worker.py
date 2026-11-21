#!/usr/bin/env python3
import os
import json
import time
import redis
import psycopg2
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

# Initialize OpenTelemetry
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(
    endpoint=f"{os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://jaeger:4318')}/v1/traces"
)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

# Auto-instrument Redis and PostgreSQL
RedisInstrumentor().instrument()
Psycopg2Instrumentor().instrument()

tracer = trace.get_tracer(os.getenv('OTEL_SERVICE_NAME', 'worker'))

def get_redis_client():
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        decode_responses=True
    )

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'orders'),
        user=os.getenv('POSTGRES_USER', 'faultlab'),
        password=os.getenv('POSTGRES_PASSWORD', 'chaos123')
    )

def process_order(order_data):
    """Process order and save to database"""
    with tracer.start_as_current_span('process-order') as span:
        try:
            order = json.loads(order_data)
            span.set_attribute('order.id', order['order_id'])
            span.set_attribute('order.customer_id', order['customer_id'])
            span.set_attribute('order.amount', order['amount'])
            
            # Simulate processing time
            time.sleep(0.1)
            
            # Save to database
            with tracer.start_as_current_span('db-insert'):
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    INSERT INTO orders (order_id, customer_id, amount, status, processed_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (order_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        processed_at = EXCLUDED.processed_at
                    """,
                    (order['order_id'], order['customer_id'], order['amount'], 'completed')
                )
                
                conn.commit()
                cursor.close()
                conn.close()
            
            print(f"✓ Processed order: {order['order_id']}")
            return True
            
        except Exception as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            print(f"✗ Error processing order: {str(e)}")
            return False

def main():
    print("Worker starting...")
    redis_client = get_redis_client()
    
    print("Waiting for orders in queue...")
    
    while True:
        try:
            # Blocking pop from Redis queue
            result = redis_client.brpop('order_queue', timeout=5)
            
            if result:
                queue_name, order_data = result
                print(f"\n← Received order from queue")
                process_order(order_data)
            
        except KeyboardInterrupt:
            print("\nShutting down worker...")
            break
        except Exception as e:
            print(f"Worker error: {str(e)}")
            time.sleep(5)

if __name__ == '__main__':
    main()
