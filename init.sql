CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at DESC);

-- Insert sample data
INSERT INTO orders (order_id, customer_id, amount, status) VALUES
    ('ORD-001', 'CUST-A', 99.99, 'completed'),
    ('ORD-002', 'CUST-B', 149.50, 'completed'),
    ('ORD-003', 'CUST-C', 79.99, 'pending');
