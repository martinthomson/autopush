"""Metrics interface and implementations"""
from twisted.internet import reactor
from txstatsd.client import StatsDClientProtocol, TwistedStatsDClient
from txstatsd.metrics.metrics import Metrics

import datadog
from datadog import ThreadStats
from datadog.util.hostname import get_hostname


class IMetrics(object):
    """Metrics interface

    Each method except :meth:`__init__` and :meth:`start` must be implemented.

    Additional ``kwargs`` may be recorded as additional metric tags for metric
    systems that support it, otherwise they should be ignored.

    """
    def __init__(self, *args, **kwargs):
        """Setup the metrics"""

    def start(self):
        """Start any connection needed for metric transmission"""

    def increment(self, name, count=1, **kwargs):
        """Increment a counter for a metric name"""
        raise NotImplementedError("No increment implemented")

    def gauge(self, name, count, **kwargs):
        """Record a gauge for a metric name"""
        raise NotImplementedError("No gauge implemented")

    def timing(self, name, duration, **kwargs):
        """Record a timing in ms for a metric name"""
        raise NotImplementedError("No timing implemented")


class SinkMetrics(IMetrics):
    """Exists to ignore metrics when metrics are not active"""
    def increment(self, name, count=1, **kwargs):
        pass

    def gauge(self, name, count, **kwargs):
        pass

    def timing(self, name, duration, **kwargs):
        pass


class TwistedMetrics(object):
    """Twisted implementation of statsd output"""
    def __init__(self, statsd_host="localhost", statsd_port=8125):
        self.client = TwistedStatsDClient(statsd_host, statsd_port)
        self._metric = Metrics(connection=self.client, namespace="autopush")

    def start(self):
        protocol = StatsDClientProtocol(self.client)
        reactor.listenUDP(0, protocol)

    def increment(self, name, count=1, **kwargs):
        self._metric.increment(name, count)

    def gauge(self, name, count, **kwargs):
        self._metric.gauge(name, count)

    def timing(self, name, duration, **kwargs):
        self._metric.timing(name, duration)


class DatadogMetrics(object):
    """DataDog Metric backend"""
    def __init__(self, api_key, app_key, flush_interval=10,
                 namespace="autopush"):

        datadog.initialize(api_key=api_key, app_key=app_key)
        self._client = ThreadStats()
        self._flush_interval = flush_interval
        self._host = get_hostname()
        self._namespace = namespace

    def _prefix_name(self, name):
        return "%s.%s" % (self._namespace, name)

    def start(self):
        self._client.start(flush_interval=self._flush_interval,
                           roll_up_interval=self._flush_interval)

    def increment(self, name, count=1, **kwargs):
        self._client.increment(self._prefix_name(name), count, host=self._host,
                               **kwargs)

    def gauge(self, name, count, **kwargs):
        self._client.gauge(self._prefix_name(name), count, host=self._host,
                           **kwargs)

    def timing(self, name, duration, **kwargs):
        self._client.timing(self._prefix_name(name), value=duration,
                            host=self._host, **kwargs)
