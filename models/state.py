import structlog
import time
import json
from redis.cluster import RedisCluster, ClusterNode
from redis.exceptions import RedisClusterException
from monitoring.metrics import WhiteboardMetrics
from typing import Dict, List

logger = structlog.get_logger()

class RedisClusterStateManager:
    def __init__(self, startup_nodes, password=None):
        self.metrics = WhiteboardMetrics()
        try:
            # Connect to just the primary node first
            primary_node = startup_nodes[0]
            self.redis_cluster = RedisCluster(
                host=primary_node['host'],
                port=primary_node['port'],
                decode_responses=True,
                skip_full_coverage_check=True,
                retry_on_timeout=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            logger.info("connected_to_redis_cluster", 
                       node_count=len(self.redis_cluster.get_nodes()))
        except RedisClusterException as e:
            logger.error("redis_cluster_connection_failed", error=str(e))
            raise
    # def __init__(self, startup_nodes, password=None, max_retries=5):
    #     self.metrics = WhiteboardMetrics()
    #     retries = 0
    #
    #     while retries < max_retries:
    #         try:
    #             cluster_nodes = [
    #                 ClusterNode(node['host'], node['port']) 
    #                 for node in startup_nodes
    #             ]
    #
    #             self.redis_cluster = RedisCluster(
    #                 startup_nodes=cluster_nodes,
    #                 decode_responses=True,
    #                 password=password,
    #                 skip_full_coverage_check=True,
    #                 retry_on_timeout=True,
    #                 socket_timeout=5,
    #                 socket_connect_timeout=5
    #             )
    #             logger.info("connected_to_redis_cluster", 
    #                        node_count=len(self.redis_cluster.get_nodes()))
    #             return
    #         except RedisClusterException as e:
    #             retries += 1
    #             if retries >= max_retries:
    #                 logger.error("redis_cluster_connection_failed", error=str(e))
    #                 raise
    #             wait_time = min(2 ** retries, 30)  # exponential backoff with max 30 seconds
    #             logger.warning(f"Failed to connect to Redis cluster (attempt {retries}/{max_retries}). Retrying in {wait_time} seconds...")
    #             time.sleep(wait_time)
    #
    def save_action(self, action: Dict) -> None:
        start_time = time.time()
        try:
            self.redis_cluster.zadd(
                'whiteboard:actions',
                {json.dumps(action): action['timestamp']}
            )
            self.metrics.draw_actions_counter.inc()
        except RedisClusterException as e:
            logger.error("save_action_failed", error=str(e), action_id=action.get('id'))
            raise
        finally:
            self.metrics.redis_operation_time.observe(time.time() - start_time)

    def get_actions_since(self, timestamp: float) -> List[Dict]:
        start_time = time.time()
        try:
            actions = self.redis_cluster.zrangebyscore(
                'whiteboard:actions',
                timestamp,
                float('inf')
            )
            return [json.loads(action) for action in actions]
        except RedisClusterException as e:
            logger.error("get_actions_failed", error=str(e), timestamp=timestamp)
            return []
        finally:
            self.metrics.redis_operation_time.observe(time.time() - start_time)
