"""
RAG Performance Monitoring and Analytics System
"""
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
import numpy as np

from django.db import models, transaction
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Monitoring features will be limited.")

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus client not available. Metrics will be limited.")


@dataclass
class QueryMetrics:
    """Metrics for a single query"""
    query_id: str
    query_text: str
    user_id: Optional[str]
    timestamp: datetime
    
    # Performance metrics
    total_duration: float
    retrieval_duration: float
    reranking_duration: float
    generation_duration: float
    
    # Quality metrics
    retrieval_count: int
    rerank_count: int
    confidence_score: float
    fallback_used: bool
    
    # Cache metrics
    cache_hit: bool
    cache_type: Optional[str]  # exact, similar, miss
    
    # Response metrics
    response_length: int
    tokens_used: int
    
    # User feedback
    user_rating: Optional[int] = None
    user_feedback: Optional[str] = None


class RAGMetrics(models.Model):
    """Database model for storing RAG metrics"""
    query_id = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rag_metrics'
    )
    query_text = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Performance fields
    total_duration = models.FloatField()
    retrieval_duration = models.FloatField()
    reranking_duration = models.FloatField(default=0)
    generation_duration = models.FloatField()
    
    # Quality fields
    retrieval_count = models.IntegerField()
    rerank_count = models.IntegerField(default=0)
    confidence_score = models.FloatField()
    fallback_used = models.BooleanField(default=False)
    
    # Cache fields
    cache_hit = models.BooleanField(default=False)
    cache_type = models.CharField(max_length=20, null=True, blank=True)
    
    # Response fields
    response_length = models.IntegerField()
    tokens_used = models.IntegerField(default=0)
    
    # Feedback fields
    user_rating = models.IntegerField(null=True, blank=True)
    user_feedback = models.TextField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['confidence_score']),
        ]
        ordering = ['-timestamp']


class RAGMonitor:
    """
    Comprehensive monitoring for RAG system with:
    - Real-time performance tracking
    - Quality metrics
    - User satisfaction tracking
    - Alerting for degradation
    - Analytics dashboard data
    """
    
    def __init__(self):
        # Get Redis settings from Django cache configuration
        redis_settings = settings.CACHES.get('default', {}).get('LOCATION', 'redis://localhost:6379/1')
        # Parse redis URL
        from urllib.parse import urlparse
        parsed = urlparse(redis_settings)

        self.redis_client = redis.Redis(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 6379,
            db=int(parsed.path.strip('/')) if parsed.path else 0,
            decode_responses=True
        ) if REDIS_AVAILABLE else None
        
        # Initialize Prometheus metrics
        self._init_prometheus_metrics()
        
        # Alert thresholds
        self.thresholds = {
            'response_time': 5.0,  # seconds
            'confidence': 0.5,
            'cache_hit_rate': 0.3,
            'error_rate': 0.1
        }
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        if PROMETHEUS_AVAILABLE:
            # Counters
            self.query_counter = Counter(
                'rag_queries_total',
                'Total number of RAG queries',
                ['cache_status', 'fallback_used']
            )

            self.error_counter = Counter(
                'rag_errors_total',
                'Total number of RAG errors',
                ['error_type']
            )

            # Histograms
            self.duration_histogram = Histogram(
                'rag_query_duration_seconds',
                'RAG query duration distribution',
                ['stage'],
                buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
            )

            self.confidence_histogram = Histogram(
                'rag_confidence_score',
                'Confidence score distribution',
                buckets=(0.1, 0.3, 0.5, 0.7, 0.9)
            )

            # Gauges
            self.cache_hit_rate_gauge = Gauge(
                'rag_cache_hit_rate',
                'Current cache hit rate'
            )

            self.avg_confidence_gauge = Gauge(
                'rag_average_confidence',
                'Average confidence score'
            )
        else:
            # Create mock objects
            self.query_counter = None
            self.error_counter = None
            self.duration_histogram = None
            self.confidence_histogram = None
            self.cache_hit_rate_gauge = None
            self.avg_confidence_gauge = None
    
    def record_query(self, metrics: QueryMetrics):
        """Record query metrics"""
        # Update Prometheus metrics if available
        if PROMETHEUS_AVAILABLE and self.query_counter:
            self.query_counter.labels(
                cache_status=metrics.cache_type or 'miss',
                fallback_used=str(metrics.fallback_used)
            ).inc()

            self.duration_histogram.labels(stage='total').observe(metrics.total_duration)
            self.duration_histogram.labels(stage='retrieval').observe(metrics.retrieval_duration)
            self.duration_histogram.labels(stage='reranking').observe(metrics.reranking_duration)
            self.duration_histogram.labels(stage='generation').observe(metrics.generation_duration)

            self.confidence_histogram.observe(metrics.confidence_score)
        
        # Store in database
        with transaction.atomic():
            RAGMetrics.objects.create(
                query_id=metrics.query_id,
                user_id=metrics.user_id,
                query_text=metrics.query_text[:500],  # Truncate for storage
                timestamp=metrics.timestamp,
                total_duration=metrics.total_duration,
                retrieval_duration=metrics.retrieval_duration,
                reranking_duration=metrics.reranking_duration,
                generation_duration=metrics.generation_duration,
                retrieval_count=metrics.retrieval_count,
                rerank_count=metrics.rerank_count,
                confidence_score=metrics.confidence_score,
                fallback_used=metrics.fallback_used,
                cache_hit=metrics.cache_hit,
                cache_type=metrics.cache_type,
                response_length=metrics.response_length,
                tokens_used=metrics.tokens_used
            )
        
        # Update real-time metrics
        self._update_realtime_metrics(metrics)
        
        # Check for alerts
        self._check_alerts(metrics)
    
    def _update_realtime_metrics(self, metrics: QueryMetrics):
        """Update real-time metrics in Redis"""
        if not self.redis_client:
            return

        key = f"rag:realtime:{datetime.now().strftime('%Y-%m-%d:%H')}"

        # Increment counters
        self.redis_client.hincrby(key, "total_queries", 1)
        if metrics.cache_hit:
            self.redis_client.hincrby(key, "cache_hits", 1)
        if metrics.fallback_used:
            self.redis_client.hincrby(key, "fallback_count", 1)

        # Add to running averages
        self.redis_client.hincrbyfloat(key, "total_duration", metrics.total_duration)
        self.redis_client.hincrbyfloat(key, "total_confidence", metrics.confidence_score)

        # Set expiry
        self.redis_client.expire(key, 86400)  # 24 hours

        # Update gauges
        self._update_gauges()
    
    def _update_gauges(self):
        """Update Prometheus gauges"""
        if not self.redis_client or not PROMETHEUS_AVAILABLE:
            return

        # Get last hour metrics
        current_hour = datetime.now().strftime('%Y-%m-%d:%H')
        key = f"rag:realtime:{current_hour}"

        metrics = self.redis_client.hgetall(key)
        if metrics:
            total = int(metrics.get('total_queries', 0))
            cache_hits = int(metrics.get('cache_hits', 0))
            total_confidence = float(metrics.get('total_confidence', 0))

            if total > 0:
                hit_rate = cache_hits / total
                avg_confidence = total_confidence / total

                if self.cache_hit_rate_gauge:
                    self.cache_hit_rate_gauge.set(hit_rate)
                if self.avg_confidence_gauge:
                    self.avg_confidence_gauge.set(avg_confidence)
    
    def _check_alerts(self, metrics: QueryMetrics):
        """Check if metrics trigger any alerts"""
        alerts = []
        
        # Response time alert
        if metrics.total_duration > self.thresholds['response_time']:
            alerts.append({
                'type': 'slow_response',
                'message': f"Slow response: {metrics.total_duration:.2f}s",
                'severity': 'warning'
            })
        
        # Low confidence alert
        if metrics.confidence_score < self.thresholds['confidence']:
            alerts.append({
                'type': 'low_confidence',
                'message': f"Low confidence: {metrics.confidence_score:.2f}",
                'severity': 'warning'
            })
        
        # Process alerts
        for alert in alerts:
            self._send_alert(alert, metrics)
    
    def _send_alert(self, alert: Dict, metrics: QueryMetrics):
        """Send alert to monitoring system"""
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'alert': alert,
            'metrics': asdict(metrics)
        }
        
        # Store alert
        alert_key = f"rag:alerts:{datetime.now().strftime('%Y-%m-%d')}"
        self.redis_client.rpush(alert_key, json.dumps(alert_data))
        self.redis_client.expire(alert_key, 86400 * 7)  # 7 days
        
        logger.warning(f"RAG Alert: {alert['message']}")
    
    def record_user_feedback(self, query_id: str, rating: int, feedback: Optional[str] = None):
        """Record user feedback for a query"""
        try:
            metric = RAGMetrics.objects.get(query_id=query_id)
            metric.user_rating = rating
            metric.user_feedback = feedback
            metric.save()
            
            # Update satisfaction metrics
            self._update_satisfaction_metrics(rating)
            
        except RAGMetrics.DoesNotExist:
            logger.error(f"Metrics not found for query_id: {query_id}")
    
    def _update_satisfaction_metrics(self, rating: int):
        """Update user satisfaction metrics"""
        key = f"rag:satisfaction:{datetime.now().strftime('%Y-%m-%d')}"
        
        self.redis_client.hincrby(key, f"rating_{rating}", 1)
        self.redis_client.hincrby(key, "total_ratings", 1)
        self.redis_client.expire(key, 86400 * 30)  # 30 days
    
    def get_analytics_data(self, time_range: str = '24h') -> Dict:
        """Get analytics data for dashboard"""
        # Parse time range
        if time_range == '24h':
            start_time = timezone.now() - timedelta(hours=24)
        elif time_range == '7d':
            start_time = timezone.now() - timedelta(days=7)
        elif time_range == '30d':
            start_time = timezone.now() - timedelta(days=30)
        else:
            start_time = timezone.now() - timedelta(hours=24)
        
        # Query metrics
        metrics = RAGMetrics.objects.filter(timestamp__gte=start_time)
        
        # Calculate aggregates
        total_queries = metrics.count()
        avg_duration = metrics.aggregate(
            avg=models.Avg('total_duration')
        )['avg'] or 0
        
        avg_confidence = metrics.aggregate(
            avg=models.Avg('confidence_score')
        )['avg'] or 0
        
        cache_hit_rate = metrics.filter(cache_hit=True).count() / total_queries if total_queries > 0 else 0
        fallback_rate = metrics.filter(fallback_used=True).count() / total_queries if total_queries > 0 else 0
        
        # Get satisfaction metrics
        satisfaction_data = self._get_satisfaction_data()
        
        # Get query distribution
        query_distribution = metrics.values('timestamp__hour').annotate(
            count=models.Count('id')
        ).order_by('timestamp__hour')
        
        return {
            'summary': {
                'total_queries': total_queries,
                'avg_response_time': avg_duration,
                'avg_confidence': avg_confidence,
                'cache_hit_rate': cache_hit_rate,
                'fallback_rate': fallback_rate,
                'user_satisfaction': satisfaction_data
            },
            'time_series': {
                'query_volume': list(query_distribution),
                'performance': self._get_performance_time_series(metrics),
                'confidence': self._get_confidence_time_series(metrics)
            },
            'top_queries': self._get_top_queries(metrics),
            'recent_alerts': self._get_recent_alerts()
        }
    
    def _get_satisfaction_data(self) -> Dict:
        """Get user satisfaction data"""
        today = datetime.now().strftime('%Y-%m-%d')
        key = f"rag:satisfaction:{today}"
        
        data = self.redis_client.hgetall(key)
        if not data:
            return {'average': 0, 'distribution': {}}
        
        total = int(data.get('total_ratings', 0))
        if total == 0:
            return {'average': 0, 'distribution': {}}
        
        distribution = {}
        total_score = 0
        
        for i in range(1, 6):
            count = int(data.get(f'rating_{i}', 0))
            distribution[str(i)] = count
            total_score += i * count
        
        return {
            'average': total_score / total,
            'distribution': distribution
        }
    
    def _get_performance_time_series(self, metrics) -> List[Dict]:
        """Get performance metrics time series"""
        return list(metrics.values('timestamp__hour').annotate(
            avg_duration=models.Avg('total_duration'),
            p95_duration=models.aggregates.Percentile('total_duration', 0.95)
        ).order_by('timestamp__hour'))
    
    def _get_confidence_time_series(self, metrics) -> List[Dict]:
        """Get confidence metrics time series"""
        return list(metrics.values('timestamp__hour').annotate(
            avg_confidence=models.Avg('confidence_score'),
            min_confidence=models.Min('confidence_score')
        ).order_by('timestamp__hour'))
    
    def _get_top_queries(self, metrics) -> List[Dict]:
        """Get most frequent queries"""
        return list(metrics.values('query_text').annotate(
            count=models.Count('id'),
            avg_confidence=models.Avg('confidence_score')
        ).order_by('-count')[:10])
    
    def _get_recent_alerts(self) -> List[Dict]:
        """Get recent alerts"""
        key = f"rag:alerts:{datetime.now().strftime('%Y-%m-%d')}"
        alerts = self.redis_client.lrange(key, -10, -1)
        
        return [json.loads(alert) for alert in alerts]


# Create singleton instance
rag_monitor = RAGMonitor()