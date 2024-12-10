from prometheus_client import Counter, Histogram, start_http_server

class WhiteboardMetrics:
    def __init__(self, port=8000):
        # Counters
        self.connection_counter = Counter(
            'whiteboard_connections_total',
            'Total number of client connections'
        )
        self.draw_actions_counter = Counter(
            'whiteboard_draw_actions_total',
            'Total number of drawing actions'
        )
        self.clear_actions_counter = Counter(
            'whiteboard_clear_actions_total',
            'Total number of canvas clears'
        )
        
        # Histograms
        self.action_processing_time = Histogram(
            'whiteboard_action_processing_seconds',
            'Time spent processing drawing actions',
            buckets=(0.1, 0.5, 1, 2, 5)
        )
        self.redis_operation_time = Histogram(
            'whiteboard_redis_operation_seconds',
            'Time spent on Redis operations',
            buckets=(0.01, 0.05, 0.1, 0.5, 1)
        )
        
        # Start metrics server
        start_http_server(port)

