"""Central aggregation service for dashboard data.

Pulls from all observability singletons (metrics, alerts, audit, safety)
and transforms the data into dashboard-ready structures.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog

from src.observability.alerts import AlertEvaluator
from src.observability.audit import AuditTrail
from src.observability.log_buffer import LogBuffer, LogRecord, get_log_buffer
from src.observability.metrics import MetricsCollector, get_metrics_collector
from src.observability.safety_evaluator import SafetyEvaluator
from src.observability.vector_projection import compute_2d_projection
from src.utils.config import settings
from src.utils.session import SessionStore

logger = structlog.get_logger(__name__)


@dataclass
class DashboardState:
    """References to all singletons needed by the dashboard."""

    start_time: float = field(default_factory=time.monotonic)
    session_store: SessionStore | None = None
    alert_evaluator: AlertEvaluator | None = None
    audit_trail: AuditTrail | None = None
    safety_evaluator: SafetyEvaluator | None = None
    vector_index: Any = None  # VectorIndex — optional import


class DashboardAggregator:
    """Aggregates data from all observability components for the dashboard."""

    def __init__(self, state: DashboardState) -> None:
        self._state = state

    def _collector(self) -> MetricsCollector:
        return get_metrics_collector()

    def _log_buffer(self) -> LogBuffer:
        return get_log_buffer()

    # ---- Endpoint methods ----

    def get_health_overview(self) -> dict[str, Any]:
        """Status, env, uptime, active sessions, SCIN records, counters."""
        collector = self._collector()
        uptime_s = time.monotonic() - self._state.start_time
        index = self._state.vector_index
        sessions = self._state.session_store

        return {
            "status": "ok",
            "env": settings.app_env,
            "version": "0.1.0",
            "model_backend": settings.model_backend,
            "uptime_seconds": round(uptime_s, 1),
            "active_sessions": sessions.active_count if sessions else 0,
            "scin_records": index.size if index else 0,
            "predictions_total": int(collector.get_counter("predictions_total")),
            "escalations_total": int(collector.get_counter("escalations_total")),
            "retrievals_total": int(collector.get_counter("retrievals_total")),
            "log_buffer_size": self._log_buffer().size,
        }

    def get_performance_metrics(self) -> dict[str, Any]:
        """Latency percentiles, confidence distribution, ICD code counts."""
        collector = self._collector()
        pred_latency = collector.get_histogram("prediction_latency")
        retr_latency = collector.get_histogram("retrieval_latency")

        # Confidence distribution from recorded metric points
        all_metrics = collector.get_all_metrics()
        confidence_values = [m.value for m in all_metrics if m.name == "prediction_confidence"]

        # ICD code counts
        icd_codes: dict[str, int] = {}
        for key, val in collector._counters.items():
            if key.startswith("icd_code_"):
                icd_codes[key.replace("icd_code_", "")] = int(val)

        return {
            "prediction_latency": pred_latency,
            "retrieval_latency": retr_latency,
            "confidence_values": confidence_values,
            "confidence_stats": _compute_stats(confidence_values),
            "icd_code_counts": icd_codes,
        }

    def get_vector_space(self, max_points: int = 500) -> dict[str, Any]:
        """2D PCA projection of vector index embeddings."""
        index = self._state.vector_index
        if index is None or index.size == 0:
            return {"points": [], "total_embeddings": 0, "sampled": 0}

        # Extract embeddings and metadata from index
        try:
            embeddings = np.array(index._embeddings, dtype=np.float32)
            metadata = list(index._metadata)
            result = compute_2d_projection(embeddings, metadata, max_points)
            return {
                "points": result.points,
                "total_embeddings": result.total_embeddings,
                "sampled": result.sampled,
            }
        except (AttributeError, ValueError) as exc:
            logger.debug("vector_projection_failed", error=str(exc))
            return {"points": [], "total_embeddings": 0, "sampled": 0, "error": str(exc)}

    def get_safety_metrics(self) -> dict[str, Any]:
        """Safety pass rate, violations, escalation rate."""
        evaluator = self._state.safety_evaluator
        collector = self._collector()

        if evaluator:
            report = evaluator.generate_report()
            safety_data = {
                "total_checked": report.total_checked,
                "total_passed": report.total_passed,
                "pass_rate": round(report.pass_rate, 4),
                "violations_by_type": report.violations_by_type,
            }
        else:
            safety_data = {
                "total_checked": 0,
                "total_passed": 0,
                "pass_rate": 1.0,
                "violations_by_type": {},
            }

        # Escalation rate
        preds = collector.get_counter("predictions_total")
        escs = collector.get_counter("escalations_total")
        safety_data["escalation_rate"] = round(escs / preds, 4) if preds > 0 else 0.0
        safety_data["escalations_total"] = int(escs)
        safety_data["predictions_total"] = int(preds)

        return safety_data

    def get_bias_metrics(self) -> dict[str, Any]:
        """Metrics grouped by Fitzpatrick type and language."""
        all_metrics = self._collector().get_all_metrics()

        # Group confidence by fitzpatrick_type and language
        by_fitz: dict[str, list[float]] = defaultdict(list)
        by_lang: dict[str, list[float]] = defaultdict(list)
        fitz_counts: dict[str, int] = defaultdict(int)
        lang_counts: dict[str, int] = defaultdict(int)

        for m in all_metrics:
            if m.name != "prediction_confidence":
                continue
            ftype = m.labels.get("fitzpatrick_type", "")
            lang = m.labels.get("language", "")
            if ftype:
                by_fitz[ftype].append(m.value)
                fitz_counts[ftype] += 1
            if lang:
                by_lang[lang].append(m.value)
                lang_counts[lang] += 1

        return {
            "by_fitzpatrick": {
                k: {
                    "count": fitz_counts[k],
                    "mean_confidence": round(sum(v) / len(v), 4) if v else 0.0,
                    "min_confidence": round(min(v), 4) if v else 0.0,
                    "max_confidence": round(max(v), 4) if v else 0.0,
                }
                for k, v in sorted(by_fitz.items())
            },
            "by_language": {
                k: {
                    "count": lang_counts[k],
                    "mean_confidence": round(sum(v) / len(v), 4) if v else 0.0,
                    "min_confidence": round(min(v), 4) if v else 0.0,
                    "max_confidence": round(max(v), 4) if v else 0.0,
                }
                for k, v in sorted(by_lang.items())
            },
        }

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Triggered alerts with severity and runbook URLs."""
        evaluator = self._state.alert_evaluator
        if evaluator is None:
            return []

        alerts = evaluator.evaluate_all()
        return [
            {
                "name": a.rule.name,
                "category": a.rule.category,
                "severity": a.rule.severity,
                "description": a.rule.description,
                "runbook_url": a.rule.runbook_url,
                "actual_value": round(a.actual_value, 2),
                "threshold": a.rule.threshold,
                "message": a.message,
            }
            for a in alerts
        ]

    def get_audit_records(self, limit: int = 50) -> list[dict[str, Any]]:
        """Recent audit records (session_id included for traceability)."""
        trail = self._state.audit_trail
        if trail is None:
            return []

        all_records = trail.export_all()
        # Return most recent first, up to limit
        return all_records[-limit:][::-1]

    def get_logs(
        self,
        *,
        level: str = "",
        event: str = "",
        search: str = "",
        session_id: str = "",
        since: str = "",
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Filtered log records from the in-memory buffer."""
        records = self._log_buffer().query(
            level=level,
            event=event,
            search=search,
            session_id=session_id,
            since=since,
            limit=limit,
        )
        return [_log_record_to_dict(r) for r in records]

    def get_time_series(
        self,
        metric_name: str,
        bucket_seconds: int = 60,
    ) -> dict[str, Any]:
        """Time-bucketed metric values for line charts."""
        all_metrics = self._collector().get_all_metrics()
        matching = [m for m in all_metrics if m.name == metric_name]

        if not matching:
            return {"metric": metric_name, "bucket_seconds": bucket_seconds, "buckets": []}

        # Group by time bucket
        buckets: dict[int, list[float]] = defaultdict(list)
        for m in matching:
            bucket_key = int(m.timestamp // bucket_seconds) * bucket_seconds
            buckets[bucket_key] = buckets.get(bucket_key, [])
            buckets[bucket_key].append(m.value)

        result_buckets = []
        for ts in sorted(buckets.keys()):
            vals = buckets[ts]
            result_buckets.append(
                {
                    "timestamp": ts,
                    "count": len(vals),
                    "mean": round(sum(vals) / len(vals), 4) if vals else 0,
                    "min": round(min(vals), 4) if vals else 0,
                    "max": round(max(vals), 4) if vals else 0,
                }
            )

        return {
            "metric": metric_name,
            "bucket_seconds": bucket_seconds,
            "buckets": result_buckets,
        }

    def get_request_stats(self) -> dict[str, Any]:
        """API call counts, error rates, latency by endpoint."""
        all_metrics = self._collector().get_all_metrics()

        # Group request metrics by path
        by_path: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "errors": 0, "latencies": []},
        )

        for m in all_metrics:
            path = m.labels.get("path", "")
            if not path:
                continue
            if m.name == "request_count_ms":
                # This was recorded via observe_latency, which also records the metric
                pass
            elif m.name == "request_latency_ms":
                by_path[path]["latencies"].append(m.value)
                by_path[path]["count"] += 1
                status = m.labels.get("status", "200")
                if status.startswith(("4", "5")):
                    by_path[path]["errors"] += 1

        # Also check counters
        collector = self._collector()
        total_requests = int(collector.get_counter("request_count"))
        total_errors = int(collector.get_counter("request_errors"))

        endpoints = {}
        for path, data in sorted(by_path.items()):
            lats = data["latencies"]
            endpoints[path] = {
                "count": data["count"],
                "errors": data["errors"],
                "latency_stats": _compute_stats(lats),
            }

        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round(total_errors / total_requests, 4) if total_requests > 0 else 0.0,
            "endpoints": endpoints,
        }


def _log_record_to_dict(record: LogRecord) -> dict[str, Any]:
    """Convert a LogRecord to a serializable dict."""
    return {
        "timestamp": record.timestamp,
        "level": record.level,
        "event": record.event,
        "logger_name": record.logger_name,
        "fields": record.fields,
    }


def _compute_stats(values: list[float]) -> dict[str, float]:
    """Compute p50, p95, p99, mean for a list of values."""
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "count": 0}
    sv = sorted(values)
    n = len(sv)
    return {
        "p50": round(sv[int(n * 0.50)], 4),
        "p95": round(sv[min(int(n * 0.95), n - 1)], 4),
        "p99": round(sv[min(int(n * 0.99), n - 1)], 4),
        "mean": round(sum(sv) / n, 4),
        "count": n,
    }
