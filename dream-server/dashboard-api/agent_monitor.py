"""
Agent Monitoring Module for Dashboard API
Collects real-time metrics on agent swarms, sessions, and token usage.
"""

import asyncio
import json
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os
import asyncpg

# Token monitor database URL - configurable via environment variable
# Default: postgresql connection to token-spy-db
TOKEN_MONITOR_DB_URL = os.environ.get(
    "TOKEN_MONITOR_DB",
    "postgresql://tokenspy:tokenspy@token-spy-db:5432/tokenspy"
)


class AgentMetrics:
    """Real-time agent monitoring metrics"""

    def __init__(self):
        self.last_update = datetime.now()
        self.session_count = 0
        self.tokens_per_second = 0.0
        self.error_rate_1h = 0.0
        self.queue_depth = 0

    def to_dict(self) -> dict:
        return {
            "session_count": self.session_count,
            "tokens_per_second": round(self.tokens_per_second, 2),
            "error_rate_1h": round(self.error_rate_1h, 2),
            "queue_depth": self.queue_depth,
            "last_update": self.last_update.isoformat()
        }


class ClusterStatus:
    """Cluster health and node status"""

    def __init__(self):
        self.nodes: List[dict] = []
        self.failover_ready = False
        self.total_gpus = 0
        self.active_gpus = 0

    async def refresh(self):
        """Query cluster status from smart proxy"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "curl", "-s", "http://localhost:9199/status",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)

            if proc.returncode == 0:
                data = json.loads(stdout.decode())
                self.nodes = data.get("nodes", [])
                self.total_gpus = len(self.nodes)
                self.active_gpus = sum(1 for n in self.nodes if n.get("healthy", False))
                self.failover_ready = self.active_gpus > 1
        except Exception:
            pass

    def to_dict(self) -> dict:
        return {
            "nodes": self.nodes,
            "total_gpus": self.total_gpus,
            "active_gpus": self.active_gpus,
            "failover_ready": self.failover_ready
        }


class TokenUsageMetrics:
    """Token usage statistics from Token Spy TimescaleDB"""

    def __init__(self):
        self.total_tokens_24h = 0
        self.total_cost_24h = 0.0
        self.requests_24h = 0
        self.top_models: List[dict] = []

    async def refresh(self):
        """Query Token Spy database for usage stats"""
        conn = None
        try:
            conn = await asyncpg.connect(TOKEN_MONITOR_DB_URL)

            # Last 24 hours
            since = datetime.now() - timedelta(hours=24)

            # Get aggregate stats
            row = await conn.fetchrow("""
                SELECT
                    SUM(prompt_tokens + completion_tokens) as total_tokens,
                    SUM(total_cost) as total_cost,
                    COUNT(*) as request_count
                FROM api_requests
                WHERE timestamp > $1
            """, since)

            if row:
                self.total_tokens_24h = row['total_tokens'] or 0
                self.total_cost_24h = float(row['total_cost'] or 0.0)
                self.requests_24h = row['request_count'] or 0

            # Get top models
            rows = await conn.fetch("""
                SELECT
                    model,
                    SUM(prompt_tokens + completion_tokens) as tokens,
                    COUNT(*) as requests
                FROM api_requests
                WHERE timestamp > $1
                GROUP BY model
                ORDER BY tokens DESC
                LIMIT 5
            """, since)

            self.top_models = [
                {"model": row['model'], "tokens": row['tokens'], "requests": row['requests']}
                for row in rows
            ]

            await conn.close()
        except Exception:
            # Silently fail if database is unavailable
            if conn:
                await conn.close()

    def to_dict(self) -> dict:
        return {
            "total_tokens_24h": self.total_tokens_24h,
            "total_cost_24h": round(self.total_cost_24h, 4),
            "requests_24h": self.requests_24h,
            "top_models": self.top_models
        }


class ThroughputMetrics:
    """Real-time throughput tracking"""

    def __init__(self, history_minutes: int = 15):
        self.history_minutes = history_minutes
        self.data_points: List[dict] = []

    def add_sample(self, tokens_per_sec: float):
        """Add a new throughput sample"""
        self.data_points.append({
            "timestamp": datetime.now().isoformat(),
            "tokens_per_sec": tokens_per_sec
        })

        # Prune old data
        cutoff = datetime.now() - timedelta(minutes=self.history_minutes)
        self.data_points = [
            p for p in self.data_points
            if datetime.fromisoformat(p["timestamp"]) > cutoff
        ]

    def get_stats(self) -> dict:
        """Get throughput statistics"""
        if not self.data_points:
            return {"current": 0, "average": 0, "peak": 0, "history": []}

        values = [p["tokens_per_sec"] for p in self.data_points]
        return {
            "current": values[-1] if values else 0,
            "average": sum(values) / len(values),
            "peak": max(values) if values else 0,
            "history": self.data_points[-30:]  # Last 30 points
        }


# Global metrics instances
agent_metrics = AgentMetrics()
cluster_status = ClusterStatus()
token_usage = TokenUsageMetrics()
throughput = ThroughputMetrics()


async def collect_metrics():
    """Background task to collect metrics periodically"""
    while True:
        try:
            # Update cluster status
            await cluster_status.refresh()

            # Update token usage
            await token_usage.refresh()

            # Estimate throughput from token usage rate
            if token_usage.requests_24h > 0:
                avg_tokens_per_request = token_usage.total_tokens_24h / token_usage.requests_24h
                # Rough estimate: divide by time window
                throughput.add_sample(avg_tokens_per_request / 60)  # per minute

            agent_metrics.last_update = datetime.now()

        except Exception:
            pass

        await asyncio.sleep(5)  # Update every 5 seconds


def get_full_agent_metrics() -> dict:
    """Get all agent monitoring metrics as a dict"""
    return {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_metrics.to_dict(),
        "cluster": cluster_status.to_dict(),
        "tokens": token_usage.to_dict(),
        "throughput": throughput.get_stats()
    }
