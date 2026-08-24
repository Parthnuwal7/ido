"""
Taste worlds, learned from which channels are watched in the same sitting.

Sessions are baskets and channels are items. Build a channel x channel co-occurrence
matrix, convert to PPMI, factorize with SVD, and cluster the rows. SVD of a PPMI matrix
is the matrix-factorization equivalent of word2vec, and this is the same family of
technique as YouTube's own 2016 candidate-generation embeddings -- learned from watch
sequences rather than from any metadata.

numpy only, deliberately: the matrix is at most a few hundred square, so numpy.linalg
is exact and instant, and sklearn+scipy would add ~100 MB to a free-tier deployment.

Cluster ids are arbitrary and must never be shown. Cards render labels or names.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from typing import Dict, List, Optional, Tuple

import numpy as np

# Cluster count is chosen per user rather than fixed. Forcing one K splits real
# groups: at K=6 a viewer with three genuine music worlds got "Pop Music and
# Electronic", "Pop Music and Film" and "Pop Music and Asia" as separate worlds.
MIN_K = 3
MAX_K = 8                  # more than this stops reading as "worlds" on a card
MIN_VOCAB = 12             # below this, do not cluster at all
MIN_SESSIONS = 8           # sessions a channel must appear in to be embeddable
SESSION_GAP_MINUTES = 30
MAX_SESSION_CHANNELS = 50  # a longer sitting is autoplay drift, not deliberate pairing
SVD_DIMS = 32
SEED = 0
N_INIT = 10               # k-means++ restarts; a single init strands whole groups
PERMUTATIONS = 200
SEASONAL_P = 0.05


@dataclass
class InterestResult:
    clusters: List[Dict] = field(default_factory=list)
    cluster_of: Dict[str, int] = field(default_factory=dict)
    coverage: float = 0.0
    vocab_size: int = 0


def _sessions(watch_events: List[Dict]) -> List[List[str]]:
    timed: List[Tuple[datetime, str]] = []
    for event in watch_events:
        stamp = event.get("timestamp_local") or event.get("timestamp_utc")
        channel = event.get("channel_clean")
        if not stamp or not channel:
            continue
        try:
            timed.append((datetime.fromisoformat(stamp.replace("Z", "+00:00")), channel))
        except (ValueError, AttributeError):
            continue

    if not timed:
        return []

    timed.sort(key=lambda pair: pair[0])
    sessions, current = [], [timed[0][1]]
    for index in range(1, len(timed)):
        gap = (timed[index][0] - timed[index - 1][0]).total_seconds() / 60
        if gap > SESSION_GAP_MINUTES:
            sessions.append(current)
            current = []
        current.append(timed[index][1])
    sessions.append(current)
    return sessions


def _kmeans_once(points: np.ndarray, k: int, rng, iterations: int = 60):
    """One k-means++ run. Returns (labels, inertia)."""
    n = len(points)
    centres = [points[rng.integers(n)]]
    for _ in range(k - 1):
        distances = np.min(
            ((points[:, None, :] - np.array(centres)[None, :, :]) ** 2).sum(-1), axis=1
        )
        total = distances.sum()
        probabilities = distances / total if total > 0 else np.full(n, 1 / n)
        centres.append(points[rng.choice(n, p=probabilities)])

    centroids = np.array(centres)
    labels = np.zeros(n, dtype=int)
    for _ in range(iterations):
        labels = np.argmin(
            ((points[:, None, :] - centroids[None, :, :]) ** 2).sum(-1), axis=1
        )
        moved = np.array([
            points[labels == j].mean(0) if (labels == j).any() else centroids[j]
            for j in range(k)
        ])
        if np.allclose(moved, centroids):
            break
        centroids = moved

    inertia = float(((points - centroids[labels]) ** 2).sum())
    return labels, inertia


def _kmeans(points: np.ndarray, k: int, seed: int = SEED, iterations: int = 60):
    """Best of N_INIT k-means++ runs, by inertia. Deterministic for a given input.

    The restarts are not optional. A single k-means++ init frequently strands whole
    groups: on six perfectly disjoint channel groups it produced one cluster containing
    three of them while splitting another into singletons. Co-occurrence embeddings are
    near-degenerate within a group -- rows in the same block are almost identical -- so
    one unlucky seeding is easy to hit and impossible to recover from by iterating.
    """
    rng = np.random.default_rng(seed)
    best_labels, best_inertia = None, None
    for _ in range(N_INIT):
        labels, inertia = _kmeans_once(points, k, rng, iterations)
        if best_inertia is None or inertia < best_inertia:
            best_labels, best_inertia = labels, inertia
    return best_labels


def _silhouette(points: np.ndarray, labels: np.ndarray) -> float:
    """Mean silhouette score: how well each point sits in its own cluster.

    For each point, a = mean distance to its own cluster, b = mean distance to the
    nearest other cluster; the score is (b - a) / max(a, b). Near 1 means tight and
    well separated, near 0 means the split is arbitrary. This is what lets the code
    prefer three real worlds over six invented ones.
    """
    unique = np.unique(labels)
    if len(unique) < 2 or len(unique) >= len(points):
        return -1.0

    distances = np.sqrt(
        np.maximum(((points[:, None, :] - points[None, :, :]) ** 2).sum(-1), 0)
    )
    scores = []
    for i in range(len(points)):
        own = labels[i]
        same = labels == own
        same[i] = False
        if not same.any():
            continue                      # a lone point has no cohesion to measure
        a = distances[i, same].mean()
        b = min(
            distances[i, labels == other].mean()
            for other in unique if other != own and (labels == other).any()
        )
        denominator = max(a, b)
        if denominator > 0:
            scores.append((b - a) / denominator)
    return float(np.mean(scores)) if scores else -1.0


def _best_labels(points: np.ndarray) -> np.ndarray:
    """Cluster at every K in range and keep the best-separated result."""
    upper = min(MAX_K, len(points) - 1)
    best_labels, best_score = None, None
    for k in range(MIN_K, max(upper, MIN_K) + 1):
        labels = _kmeans(points, k)
        score = _silhouette(points, labels)
        if best_score is None or score > best_score:
            best_labels, best_score = labels, score
    return best_labels if best_labels is not None else _kmeans(points, MIN_K)


def analyse(watch_events: List[Dict]) -> Optional[InterestResult]:
    """Cluster channels into taste worlds, or None when the data cannot support it."""
    sessions = _sessions(watch_events)
    if not sessions:
        return None

    appearances = Counter(channel for s in sessions for channel in set(s))
    vocab = [c for c, n in appearances.most_common() if n >= MIN_SESSIONS]
    if len(vocab) < MIN_VOCAB:
        return None

    index = {channel: i for i, channel in enumerate(vocab)}
    size = len(vocab)
    matrix = np.zeros((size, size))
    for s in sessions:
        unique = [c for c in set(s) if c in index]
        if len(unique) > MAX_SESSION_CHANNELS:
            continue
        for a, b in combinations(unique, 2):
            matrix[index[a], index[b]] += 1
            matrix[index[b], index[a]] += 1

    total = matrix.sum()
    if total == 0:
        return None

    row_sums = matrix.sum(1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        pmi = np.log((matrix * total) / (row_sums * row_sums.T))
    ppmi = np.nan_to_num(np.maximum(pmi, 0), nan=0.0, posinf=0.0, neginf=0.0)

    left, singular, _ = np.linalg.svd(ppmi, full_matrices=False)
    dims = min(SVD_DIMS, size - 1)
    embedding = left[:, :dims] * singular[:dims]
    norms = np.linalg.norm(embedding, axis=1, keepdims=True)
    embedding = embedding / (norms + 1e-9)

    labels = _best_labels(embedding)
    cluster_of = {channel: int(labels[index[channel]]) for channel in vocab}

    watch_counts = Counter(
        e.get("channel_clean") for e in watch_events if e.get("channel_clean")
    )
    members = defaultdict(list)
    for channel, cluster in cluster_of.items():
        members[cluster].append(channel)

    clustered_watches = sum(watch_counts[c] for c in vocab)
    clusters = []
    for cluster, channels in members.items():
        channels = sorted(channels, key=lambda c: -watch_counts[c])
        watches = sum(watch_counts[c] for c in channels)
        clusters.append({
            "index": cluster,
            "channels": channels,
            "watches": watches,
            "share": round(watches / clustered_watches, 4) if clustered_watches else 0.0,
        })
    clusters.sort(key=lambda c: -c["watches"])

    all_watches = sum(watch_counts.values())
    return InterestResult(
        clusters=clusters,
        cluster_of=cluster_of,
        coverage=round(clustered_watches / all_watches, 4) if all_watches else 0.0,
        vocab_size=size,
    )


def by_month(result: Optional[InterestResult], watch_events: List[Dict]) -> Dict:
    """Share of each month's clustered viewing per world, with a seasonality test."""
    if result is None:
        return {"months": [], "worlds": [], "seasonal": False, "p_value": 1.0}

    counts: Dict[str, Counter] = defaultdict(Counter)
    for event in watch_events:
        channel = event.get("channel_clean")
        cluster = result.cluster_of.get(channel)
        if cluster is None:
            continue
        stamp = event.get("timestamp_local") or event.get("timestamp_utc")
        if not stamp:
            continue
        try:
            month = datetime.fromisoformat(stamp.replace("Z", "+00:00")).strftime("%Y-%m")
        except (ValueError, AttributeError):
            continue
        counts[month][cluster] += 1

    months = sorted(counts)
    order = [c["index"] for c in result.clusters]
    if not months:
        return {"months": [], "worlds": [], "seasonal": False, "p_value": 1.0}

    grid = np.array([[counts[m][c] for m in months] for c in order], dtype=float)
    column_totals = np.maximum(grid.sum(0, keepdims=True), 1)
    shares = grid / column_totals

    # Is the month-to-month movement more than re-sampling the same totals produces?
    observed = float(shares.std(axis=1).mean())
    row_totals = grid.sum(1)
    rng = np.random.default_rng(SEED)
    simulated = []
    if row_totals.sum() > 0:
        weights = row_totals / row_totals.sum()
        for _ in range(PERMUTATIONS):
            draw = np.zeros_like(grid)
            for j, column_total in enumerate(grid.sum(0)):
                draw[:, j] = rng.multinomial(int(column_total), weights)
            draw_shares = draw / np.maximum(draw.sum(0, keepdims=True), 1)
            simulated.append(draw_shares.std(axis=1).mean())
    p_value = float(np.mean(np.array(simulated) >= observed)) if simulated else 1.0

    worlds = [
        {"index": cluster, "shares": [round(float(v), 4) for v in shares[i]]}
        for i, cluster in enumerate(order)
    ]
    return {
        "months": months,
        "worlds": worlds,
        "seasonal": bool(p_value < SEASONAL_P and len(months) >= 3),
        "p_value": round(p_value, 4),
    }
