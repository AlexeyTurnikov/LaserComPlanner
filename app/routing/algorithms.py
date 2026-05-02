"""Routing algorithms for the terrestrial fiber graph."""

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import inf


@dataclass(frozen=True)
class RouteEdge:
    """Weighted fiber graph edge."""

    source_id: int
    target_id: int
    distance_km: float
    latency_ms: float
    capacity_gbps: float


@dataclass(frozen=True)
class RoutePath:
    """Calculated route through the fiber graph."""

    route: list[int]
    total_cost: float
    total_distance_km: float
    total_latency_ms: float
    min_capacity_gbps: float


@dataclass(frozen=True)
class SearchState:
    """Current Dijkstra queue state."""

    node_id: int
    route: list[int]
    distance_km: float
    latency_ms: float
    min_capacity_gbps: float


def calculate_edge_cost(edge: RouteEdge) -> float:
    """Calculate edge cost using distance, latency, and 100 km spacing penalty."""

    distance_penalty = abs(edge.distance_km - 100) / 100
    return edge.distance_km * 0.5 + edge.latency_ms * 0.3 + distance_penalty * 0.2


def _build_adjacency(
    nodes: list[int],
    edges: list[RouteEdge],
) -> dict[int, list[tuple[int, RouteEdge]]]:
    """Build undirected adjacency list for valid graph edges."""

    node_set = set(nodes)
    adjacency: dict[int, list[tuple[int, RouteEdge]]] = {node_id: [] for node_id in nodes}
    for edge in edges:
        if edge.source_id not in node_set or edge.target_id not in node_set:
            continue
        adjacency[edge.source_id].append((edge.target_id, edge))
        adjacency[edge.target_id].append((edge.source_id, edge))
    return adjacency


def _route_path_from_state(state: SearchState, total_cost: float) -> RoutePath:
    """Convert a queue state into the public route result."""

    return RoutePath(
        route=state.route,
        total_cost=round(total_cost, 6),
        total_distance_km=round(state.distance_km, 3),
        total_latency_ms=round(state.latency_ms, 6),
        min_capacity_gbps=round(state.min_capacity_gbps, 6),
    )


def find_shortest_path(
    nodes: list[int],
    edges: list[RouteEdge],
    start_id: int,
    target_id: int,
) -> RoutePath | None:
    """Find the lowest-cost route between two graph nodes using Dijkstra."""

    node_set = set(nodes)
    if start_id not in node_set or target_id not in node_set:
        return None
    if start_id == target_id:
        return RoutePath(
            route=[start_id],
            total_cost=0.0,
            total_distance_km=0.0,
            total_latency_ms=0.0,
            min_capacity_gbps=0.0,
        )

    adjacency = _build_adjacency(nodes, edges)
    best_costs: dict[int, float] = {start_id: 0.0}
    sequence = count()
    queue: list[tuple[float, int, SearchState]] = []
    heappush(
        queue,
        (
            0.0,
            next(sequence),
            SearchState(start_id, [start_id], 0.0, 0.0, inf),
        ),
    )

    while queue:
        current_cost, _, state = heappop(queue)
        if current_cost > best_costs.get(state.node_id, inf):
            continue
        if state.node_id == target_id:
            return _route_path_from_state(state, current_cost)

        for next_node_id, edge in adjacency[state.node_id]:
            next_cost = current_cost + calculate_edge_cost(edge)
            if next_cost >= best_costs.get(next_node_id, inf):
                continue
            best_costs[next_node_id] = next_cost
            next_state = SearchState(
                next_node_id,
                [*state.route, next_node_id],
                state.distance_km + edge.distance_km,
                state.latency_ms + edge.latency_ms,
                min(state.min_capacity_gbps, edge.capacity_gbps),
            )
            heappush(
                queue,
                (next_cost, next(sequence), next_state),
            )

    return None
