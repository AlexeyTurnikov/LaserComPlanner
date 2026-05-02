"""Routing and transmission planning use cases."""

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.availability.models import AvailabilityCheck, AvailabilityStatus
from app.availability.service import get_latest_availability_or_none
from app.fiber_links.models import FiberLink
from app.routing.algorithms import RouteEdge, RoutePath, find_shortest_path
from app.routing.models import RoutingResult
from app.routing.schemas import (
    FindNearestAvailableRequest,
    FindNearestAvailableResponse,
    FindRouteRequest,
    FindRouteResponse,
    TransmissionPlanRequest,
    TransmissionPlanResponse,
)
from app.terminals.models import Terminal, TerminalStatus
from app.terminals.service import get_terminal_or_404
from app.transmission_requests.models import (
    TransmissionPriority,
    TransmissionRequest,
    TransmissionRequestStatus,
)
from app.transmission_requests.service import get_transmission_request_for_user
from app.users.models import User

REQUIRED_CAPACITY_GBPS = {
    TransmissionPriority.low: 1.0,
    TransmissionPriority.normal: 5.0,
    TransmissionPriority.high: 10.0,
}


@dataclass(frozen=True)
class RouteCandidate:
    """Candidate terminal routing option."""

    terminal: Terminal
    availability: AvailabilityCheck
    path: RoutePath
    route_score: float
    capacity_score: float
    final_score: float
    estimated_transfer_time_sec: float


@dataclass(frozen=True)
class RoutingResultData:
    """Data needed to persist a routing decision."""

    selected_terminal_id: int
    route: list[int]
    route_distance_km: float
    estimated_latency_ms: float
    estimated_transfer_time_sec: float
    final_score: float
    decision_reason: list[str]


def _load_terminals(db: Session) -> list[Terminal]:
    """Return all terminals ordered by ID."""

    return list(db.scalars(select(Terminal).order_by(Terminal.id)).all())


def _load_active_fiber_edges(db: Session) -> list[RouteEdge]:
    """Return active fiber links as graph edges."""

    links = db.scalars(
        select(FiberLink).where(FiberLink.is_active.is_(True)).order_by(FiberLink.id),
    ).all()
    return [
        RouteEdge(
            source_id=link.source_terminal_id,
            target_id=link.target_terminal_id,
            distance_km=link.distance_km,
            latency_ms=link.latency_ms,
            capacity_gbps=link.capacity_gbps,
        )
        for link in links
    ]


def _load_latest_availability(
    db: Session,
    terminals: list[Terminal],
) -> dict[int, AvailabilityCheck]:
    """Return latest availability for every terminal or raise a clear 409."""

    availability_by_terminal: dict[int, AvailabilityCheck] = {}
    missing_terminal_names: list[str] = []
    for terminal in terminals:
        availability = get_latest_availability_or_none(db, terminal.id)
        if availability is None:
            missing_terminal_names.append(terminal.name)
            continue
        availability_by_terminal[terminal.id] = availability

    if missing_terminal_names:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Latest availability checks are required for all terminals: "
                + ", ".join(missing_terminal_names)
            ),
        )
    return availability_by_terminal


def _select_available_candidates(
    terminals: list[Terminal],
    availability_by_terminal: dict[int, AvailabilityCheck],
    min_availability_score: float,
) -> list[Terminal]:
    """Return terminals available for satellite transmission."""

    return [
        terminal
        for terminal in terminals
        if terminal.status == TerminalStatus.online
        and availability_by_terminal[terminal.id].status == AvailabilityStatus.available
        and availability_by_terminal[terminal.id].availability_score
        >= min_availability_score
    ]


def _source_unavailable_reason(
    source_terminal: Terminal,
    availability: AvailabilityCheck | None,
) -> str:
    """Return a compact explanation for why the source terminal was not direct."""

    if source_terminal.status != TerminalStatus.online:
        return (
            "Source terminal is unavailable because hardware status is "
            f"{source_terminal.status.value}"
        )
    if availability is None:
        return "Source terminal has no latest availability check"
    first_reason = availability.reason[0] if availability.reason else availability.status.value
    return f"Source terminal is unavailable because {first_reason.lower()}"


def _build_path(
    db: Session,
    start_id: int,
    target_id: int,
) -> RoutePath | None:
    """Build the best active-fiber path between two terminals."""

    terminals = _load_terminals(db)
    nodes = [terminal.id for terminal in terminals]
    edges = _load_active_fiber_edges(db)
    return find_shortest_path(nodes, edges, start_id, target_id)


def _estimate_transfer_time_sec(data_volume_gb: float, capacity_gbps: float) -> float:
    """Estimate transfer time in seconds using data volume and capacity."""

    if capacity_gbps <= 0:
        return 0.0
    return round(data_volume_gb * 8 / capacity_gbps, 3)


def _route_score(route_cost: float) -> float:
    """Normalize route cost into a route score."""

    return 1 / (1 + route_cost / 100)


def _capacity_score(min_capacity_gbps: float, priority: TransmissionPriority) -> float:
    """Return normalized capacity score for request priority."""

    required_capacity = REQUIRED_CAPACITY_GBPS[priority]
    return min(1.0, min_capacity_gbps / required_capacity)


def _final_score(
    availability_score: float,
    route_score: float,
    capacity_score: float,
) -> float:
    """Return final weighted routing score."""

    return round(
        0.50 * availability_score + 0.30 * route_score + 0.20 * capacity_score,
        4,
    )


def _create_transmission_request(
    db: Session,
    payload: TransmissionPlanRequest,
    created_by_user_id: int,
) -> TransmissionRequest:
    """Persist a planned transmission request."""

    request = TransmissionRequest(
        created_by_user_id=created_by_user_id,
        source_terminal_id=payload.source_terminal_id,
        data_volume_gb=payload.data_volume_gb,
        priority=payload.priority,
        min_availability_score=payload.min_availability_score,
        status=TransmissionRequestStatus.planned,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def _create_routing_result(
    db: Session,
    request_id: int,
    data: RoutingResultData,
) -> RoutingResult:
    """Persist a routing result."""

    result = RoutingResult(
        request_id=request_id,
        selected_terminal_id=data.selected_terminal_id,
        route_terminal_ids=data.route,
        route_distance_km=data.route_distance_km,
        estimated_latency_ms=data.estimated_latency_ms,
        estimated_transfer_time_sec=data.estimated_transfer_time_sec,
        final_score=data.final_score,
        decision_reason=data.decision_reason,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def _response_from_result(
    result: RoutingResult,
    *,
    source_terminal_id: int,
    direct_satellite_access: bool,
    availability_score: float,
) -> TransmissionPlanResponse:
    """Convert persisted routing result to API response."""

    return TransmissionPlanResponse(
        request_id=result.request_id,
        routing_result_id=result.id,
        source_terminal_id=source_terminal_id,
        direct_satellite_access=direct_satellite_access,
        recommended_terminal_id=result.selected_terminal_id,
        route=result.route_terminal_ids,
        route_distance_km=result.route_distance_km,
        estimated_latency_ms=result.estimated_latency_ms,
        estimated_transfer_time_sec=result.estimated_transfer_time_sec,
        availability_score=availability_score,
        final_score=result.final_score,
        decision_reason=result.decision_reason,
    )


def find_route_between_terminals(
    db: Session,
    payload: FindRouteRequest,
) -> FindRouteResponse:
    """Find an active-fiber route between two terminals."""

    get_terminal_or_404(db, payload.source_terminal_id)
    get_terminal_or_404(db, payload.target_terminal_id)
    path = _build_path(db, payload.source_terminal_id, payload.target_terminal_id)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No active fiber route between terminals",
        )
    return FindRouteResponse(
        source_terminal_id=payload.source_terminal_id,
        target_terminal_id=payload.target_terminal_id,
        route=path.route,
        total_cost=path.total_cost,
        route_distance_km=path.total_distance_km,
        estimated_latency_ms=path.total_latency_ms,
        min_capacity_gbps=path.min_capacity_gbps,
    )


def find_nearest_available_terminal(
    db: Session,
    payload: FindNearestAvailableRequest,
) -> FindNearestAvailableResponse:
    """Find the nearest available terminal reachable from source."""

    source_terminal = get_terminal_or_404(db, payload.source_terminal_id)
    terminals = _load_terminals(db)
    availability_by_terminal = _load_latest_availability(db, terminals)
    candidates = _select_available_candidates(
        terminals,
        availability_by_terminal,
        payload.min_availability_score,
    )
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No available terminals meet the availability threshold",
        )

    if source_terminal in candidates:
        availability = availability_by_terminal[source_terminal.id]
        return FindNearestAvailableResponse(
            source_terminal_id=source_terminal.id,
            recommended_terminal_id=source_terminal.id,
            direct_satellite_access=True,
            route=[source_terminal.id],
            route_distance_km=0.0,
            estimated_latency_ms=0.0,
            availability_score=availability.availability_score,
            decision_reason=["Source terminal is available for direct satellite access"],
        )

    best_path: RoutePath | None = None
    best_terminal: Terminal | None = None
    for candidate in candidates:
        path = _build_path(db, source_terminal.id, candidate.id)
        if path is None:
            continue
        if best_path is None or path.total_distance_km < best_path.total_distance_km:
            best_path = path
            best_terminal = candidate

    if best_path is None or best_terminal is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No route to any available terminal",
        )

    availability = availability_by_terminal[best_terminal.id]
    return FindNearestAvailableResponse(
        source_terminal_id=source_terminal.id,
        recommended_terminal_id=best_terminal.id,
        direct_satellite_access=False,
        route=best_path.route,
        route_distance_km=best_path.total_distance_km,
        estimated_latency_ms=best_path.total_latency_ms,
        availability_score=availability.availability_score,
        decision_reason=[
            _source_unavailable_reason(
                source_terminal,
                availability_by_terminal.get(source_terminal.id),
            ),
            f"Terminal {best_terminal.id} is available for satellite transmission",
            "Selected available terminal has the shortest active fiber route",
        ],
    )


def _candidate_from_path(
    terminal: Terminal,
    availability: AvailabilityCheck,
    path: RoutePath,
    payload: TransmissionPlanRequest,
) -> RouteCandidate:
    """Build scoring data for a reachable candidate terminal."""

    route_score = _route_score(path.total_cost)
    capacity_score = _capacity_score(path.min_capacity_gbps, payload.priority)
    return RouteCandidate(
        terminal=terminal,
        availability=availability,
        path=path,
        route_score=route_score,
        capacity_score=capacity_score,
        final_score=_final_score(
            availability.availability_score,
            route_score,
            capacity_score,
        ),
        estimated_transfer_time_sec=_estimate_transfer_time_sec(
            payload.data_volume_gb,
            path.min_capacity_gbps,
        ),
    )


def _select_best_routed_candidate(
    db: Session,
    source_terminal: Terminal,
    candidates: list[Terminal],
    availability_by_terminal: dict[int, AvailabilityCheck],
    payload: TransmissionPlanRequest,
) -> RouteCandidate:
    """Return the best reachable candidate by final score."""

    route_candidates: list[RouteCandidate] = []
    for candidate in candidates:
        path = _build_path(db, source_terminal.id, candidate.id)
        if path is None:
            continue
        route_candidates.append(
            _candidate_from_path(
                candidate,
                availability_by_terminal[candidate.id],
                path,
                payload,
            ),
        )

    if not route_candidates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No route to any available terminal",
        )

    return max(
        route_candidates,
        key=lambda candidate: (
            candidate.final_score,
            candidate.availability.availability_score,
            -candidate.path.total_distance_km,
        ),
    )


def create_transmission_plan(
    db: Session,
    payload: TransmissionPlanRequest,
    created_by_user_id: int,
) -> TransmissionPlanResponse:
    """Create a transmission request and the best routing result."""

    source_terminal = get_terminal_or_404(db, payload.source_terminal_id)
    terminals = _load_terminals(db)
    availability_by_terminal = _load_latest_availability(db, terminals)
    candidates = _select_available_candidates(
        terminals,
        availability_by_terminal,
        payload.min_availability_score,
    )
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No available terminals meet the availability threshold",
        )

    if source_terminal in candidates:
        availability = availability_by_terminal[source_terminal.id]
        transfer_time = _estimate_transfer_time_sec(
            payload.data_volume_gb,
            source_terminal.max_data_rate_gbps,
        )
        request = _create_transmission_request(db, payload, created_by_user_id)
        result = _create_routing_result(
            db,
            request_id=request.id,
            data=RoutingResultData(
                selected_terminal_id=source_terminal.id,
                route=[source_terminal.id],
                route_distance_km=0.0,
                estimated_latency_ms=0.0,
                estimated_transfer_time_sec=transfer_time,
                final_score=availability.availability_score,
                decision_reason=[
                    "Source terminal is available for direct satellite access",
                    "No terrestrial fiber route is required",
                ],
            ),
        )
        return _response_from_result(
            result,
            source_terminal_id=source_terminal.id,
            direct_satellite_access=True,
            availability_score=availability.availability_score,
        )

    best_candidate = _select_best_routed_candidate(
        db,
        source_terminal,
        candidates,
        availability_by_terminal,
        payload,
    )
    request = _create_transmission_request(db, payload, created_by_user_id)
    result = _create_routing_result(
        db,
        request_id=request.id,
        data=RoutingResultData(
            selected_terminal_id=best_candidate.terminal.id,
            route=best_candidate.path.route,
            route_distance_km=best_candidate.path.total_distance_km,
            estimated_latency_ms=best_candidate.path.total_latency_ms,
            estimated_transfer_time_sec=best_candidate.estimated_transfer_time_sec,
            final_score=best_candidate.final_score,
            decision_reason=[
                _source_unavailable_reason(
                    source_terminal,
                    availability_by_terminal.get(source_terminal.id),
                ),
                (
                    f"Terminal {best_candidate.terminal.id} is available "
                    "for satellite transmission"
                ),
                (
                    "Selected route has the highest combined availability, "
                    "route, and capacity score"
                ),
                "All fiber links in the route are active",
            ],
        ),
    )
    return _response_from_result(
        result,
        source_terminal_id=source_terminal.id,
        direct_satellite_access=False,
        availability_score=best_candidate.availability.availability_score,
    )


def get_routing_result_for_request(
    db: Session,
    request_id: int,
    user: User,
) -> RoutingResult:
    """Return latest routing result for a visible transmission request."""

    get_transmission_request_for_user(db, request_id, user)
    result = db.scalar(
        select(RoutingResult)
        .where(RoutingResult.request_id == request_id)
        .order_by(RoutingResult.created_at.desc(), RoutingResult.id.desc()),
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Routing result not found",
        )
    return result
