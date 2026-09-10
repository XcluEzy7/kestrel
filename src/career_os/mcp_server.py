"""Authenticated Streamable HTTP MCP endpoint for Kestrel.

Token secrets are accepted only in Authorization headers. Database stores hashes;
tool context carries server-resolved account/profile IDs and scopes.
"""

from __future__ import annotations

import hashlib
import csv
import io
import json
from datetime import UTC, datetime

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session

from career_os.config import settings
from career_os.database import SessionLocal
from career_os.models.auth import Account, MCPToken, ProviderConnection
from career_os.models.contacts import Contact
from career_os.models.discovery import DiscoveredJob
from career_os.models.models import ActivityLog, Application, FollowUp, Profile
from career_os.schemas.applications import is_valid_transition
from career_os.models.skills import LearningResource, Skill
from career_os.schemas.contacts import ContactCreate, ContactUpdate
from career_os.schemas.follow_ups import FollowUpCreate
from career_os.services.contacts import (
    archive_contact as archive_contact_record,
    create_contact as create_contact_record,
    update_contact as update_contact_record,
)
from career_os.services.follow_ups import (
    complete_follow_up as complete_follow_up_record,
    create_follow_up as create_follow_up_record,
)
from career_os.services.discovery import run_discovery as run_discovery_service
from career_os.services.learning import (
    create_learning_resource as create_learning_resource_record,
    update_learning_status as update_learning_status_record,
)
from career_os.services.skills import (
    create_skill as create_skill_record,
    update_skill as update_skill_record,
)
from career_os.services.provider_connections import (
    create_connection as create_provider_connection_record,
    get_connection as get_provider_connection,
    update_connection as update_provider_connection_record,
)
from career_os.services.scoring import score_job as score_job_service
from career_os.schemas.provider_connections import ProviderConnectionUpdate
from career_os.migration.csv_import import _process_csv_row

READ = "mcp:read"
WRITE = "mcp:write"

def _resource_url() -> str:
    configured = settings.mcp_resource_url.strip().rstrip("/")
    if configured:
        return configured
    frontend = settings.frontend_url.strip().rstrip("/")
    if frontend and frontend != "*":
        return f"{frontend}/mcp"
    return f"http://localhost:{settings.port}/mcp"


def _token() -> AccessToken:
    token = get_access_token()
    if token is None:
        raise PermissionError("Authentication required")
    return token


def _profile() -> int:
    token = _token()
    profile_id = (token.claims or {}).get("profile_id")
    if not isinstance(profile_id, int):
        raise PermissionError("Token has no profile")
    return profile_id

def _account() -> int:
    account_id = (_token().claims or {}).get("account_id")
    if not isinstance(account_id, int):
        raise PermissionError("Token has no account")
    return account_id


def _require(scope: str) -> None:
    if scope not in _token().scopes:
        raise PermissionError(f"Required scope: {scope}")


def _db() -> Session:
    return SessionLocal()


class MCPTokenVerifier:
    """Resolve opaque MCP token against database, never trust caller ownership."""

    async def verify_token(self, token: str) -> AccessToken | None:
        digest = hashlib.sha256(token.encode()).hexdigest()
        with _db() as db:
            row = db.query(MCPToken).filter(MCPToken.token_hash == digest).first()
            if row is None or row.revoked_at is not None:
                return None
            profile = db.query(Profile).filter(Profile.id == row.profile_id).first()
            if profile is None or profile.account_id != row.account_id:
                return None
            if row.expires_at is not None:
                expires = (
                    row.expires_at.replace(tzinfo=UTC)
                    if row.expires_at.tzinfo is None
                    else row.expires_at
                )
                if expires <= datetime.now(UTC):
                    return None
            return AccessToken(
                token=token,
                client_id=f"mcp-token-{row.id}",
                scopes=row.scopes.split(),
                expires_at=int(row.expires_at.timestamp()) if row.expires_at else None,
                subject=str(row.account_id),
                claims={"account_id": row.account_id, "profile_id": row.profile_id},
                resource=_resource_url(),
            )


mcp = FastMCP(
    "kestrel",
    instructions=(
        "Kestrel account-scoped career data. Reads require mcp:read; writes require mcp:write."
    ),
    token_verifier=MCPTokenVerifier(),
    auth=AuthSettings(
        issuer_url="https://shoo.dev",
        resource_server_url=_resource_url(),
        required_scopes=[],
        validate_token_resource=False,
    ),
    streamable_http_path="/",
    stateless_http=True,
    max_request_body_size=4 * 1024 * 1024,
)


def _safe(value: object) -> object:
    """Remove common credential fields before returning tool data."""
    if isinstance(value, dict):
        secret_words = (
            "token",
            "secret",
            "password",
            "api_key",
            "authorization",
            "credential",
            "private_key",
        )
        return {
            k: _safe(v) for k, v in value.items() if not any(w in k.lower() for w in secret_words)
        }
    if isinstance(value, list):
        return [_safe(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_safe(v) for v in value)
    return value

def _bounded(value: str, name: str, limit: int) -> str:
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f"{name} exceeds size limit")
    return value


def _bounded_items(value: str, name: str, limit: int = 20) -> list[str]:
    """Parse bounded comma-separated MCP input."""
    _bounded(value, name, 2_000)
    items = [item.strip() for item in value.split(",") if item.strip()]
    if len(items) > limit or any(len(item) > 255 for item in items):
        raise ValueError(f"{name} contains too many or oversized items")
    return items


def _job_payload(job: DiscoveredJob) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "remote": job.remote,
        "fit_score": job.fit_score,
    }


@mcp.tool()
def profile_summary() -> str:
    """Read account-owned profile and high-level counts."""
    _require(READ)
    with _db() as db:
        profile = db.query(Profile).filter(Profile.id == _profile()).first()
        if profile is None:
            raise PermissionError("Profile not found")
        return json.dumps(
            _safe(
                {
                    "id": profile.id,
                    "name": profile.name,
                    "email": profile.email,
                    "job_family": profile.job_family,
                }
            )
        )


@mcp.tool()
def list_pipeline(status: str = "", search: str = "") -> str:
    """Read account-owned application pipeline."""
    _require(READ)
    status = _bounded(status, "status", 50)
    search = _bounded(search, "search", 255)
    with _db() as db:
        query = db.query(Application).filter(
            Application.profile_id == _profile(), Application.archived_at.is_(None)
        )
        if status:
            query = query.filter(Application.status == status)
        if search:
            query = query.filter(
                Application.company.ilike(f"%{search}%") | Application.role.ilike(f"%{search}%")
            )
        rows = [
            {
                "id": x.id,
                "company": x.company,
                "role": x.role,
                "status": x.status,
                "fit_score": x.fit_score,
            }
            for x in query.order_by(Application.created_at.desc()).all()
        ]
        return json.dumps(_safe(rows))


@mcp.tool()
def list_contacts(search: str = "") -> str:
    """Read account-owned networking contacts."""
    _require(READ)
    search = _bounded(search, "search", 255)
    with _db() as db:
        query = db.query(Contact).filter(
            Contact.profile_id == _profile(), Contact.archived_at.is_(None)
        )
        if search:
            query = query.filter(
                Contact.name.ilike(f"%{search}%") | Contact.company.ilike(f"%{search}%")
            )
        rows = [
            {
                "id": x.id,
                "name": x.name,
                "company": x.company,
                "role": x.role,
                "relationship_type": x.relationship_type,
            }
            for x in query.all()
        ]
        return json.dumps(_safe(rows))


@mcp.tool()
def list_follow_ups() -> str:
    """Read account-owned follow-up reminders."""
    _require(READ)
    with _db() as db:
        rows = [
            {
                "id": x.id,
                "application_id": x.application_id,
                "due_date": x.due_date.isoformat(),
                "type": x.follow_up_type,
                "notes": x.notes,
            }
            for x in db.query(FollowUp).filter(FollowUp.profile_id == _profile()).all()
        ]
        return json.dumps(_safe(rows))

@mcp.tool()
def create_contact(
    name: str,
    company: str = "",
    role: str = "",
    email: str = "",
    linkedin_url: str = "",
    phone: str = "",
    relationship_type: str = "other",
    warmth: str = "cold",
    notes: str = "",
    tags: str = "",
    source: str = "",
) -> str:
    """Write one account-owned networking contact."""
    _require(WRITE)
    _bounded(name, "name", 255)
    for value, field, limit in (
        (company, "company", 255),
        (role, "role", 255),
        (email, "email", 255),
        (linkedin_url, "linkedin_url", 500),
        (phone, "phone", 50),
        (notes, "notes", 20_000),
        (source, "source", 100),
    ):
        _bounded(value, field, limit)
    tag_values = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else None
    if tag_values and len(tag_values) > 100:
        raise ValueError("tags exceeds size limit")
    payload = ContactCreate(
        profile_id=_profile(),
        name=name,
        company=company or None,
        role=role or None,
        email=email or None,
        linkedin_url=linkedin_url or None,
        phone=phone or None,
        relationship_type=relationship_type,
        warmth=warmth,
        notes=notes or None,
        tags=tag_values,
        source=source or None,
    )
    with _db() as db:
        row = create_contact_record(db, payload)
        return json.dumps(_safe({"id": row.id, "name": row.name, "company": row.company}))

@mcp.tool()
def update_contact(
    contact_id: int,
    name: str = "",
    company: str = "",
    role: str = "",
    email: str = "",
    notes: str = "",
    warmth: str = "",
    relationship_type: str = "",
) -> str:
    """Update account-owned contact fields supplied by caller."""
    _require(WRITE)
    for value, field, limit in (
        (name, "name", 255),
        (company, "company", 255),
        (role, "role", 255),
        (email, "email", 255),
        (notes, "notes", 20_000),
        (warmth, "warmth", 20),
        (relationship_type, "relationship_type", 50),
    ):
        _bounded(value, field, limit)
    changes = {
        key: value
        for key, value in {
            "name": name,
            "company": company,
            "role": role,
            "email": email,
            "notes": notes,
            "warmth": warmth,
            "relationship_type": relationship_type,
        }.items()
        if value
    }
    if not changes:
        raise ValueError("At least one contact field is required")
    with _db() as db:
        row = update_contact_record(db, contact_id, ContactUpdate(**changes), profile_id=_profile())
        return json.dumps(_safe({"id": row.id, "name": row.name, "company": row.company}))

@mcp.tool()
def archive_contact(contact_id: int, confirm: bool = False) -> str:
    """Safely archive contact; explicit confirmation required."""
    _require(WRITE)
    if not confirm:
        return "Refused: pass confirm=true to archive contact"
    with _db() as db:
        row = archive_contact_record(db, contact_id, profile_id=_profile())
        return json.dumps({"id": row.id, "archived": True})

@mcp.tool()
def create_follow_up(
    application_id: int,
    due_date: str,
    follow_up_type: str,
    notes: str = "",
) -> str:
    """Write one follow-up for an account-owned application."""
    _require(WRITE)
    _bounded(due_date, "due_date", 64)
    _bounded(follow_up_type, "follow_up_type", 50)
    _bounded(notes, "notes", 20_000)
    try:
        parsed_due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("due_date must be ISO-8601") from exc
    payload = FollowUpCreate(
        application_id=application_id,
        profile_id=_profile(),
        due_date=parsed_due_date,
        follow_up_type=follow_up_type,
        notes=notes or None,
    )
    with _db() as db:
        row = create_follow_up_record(db, payload)
        return json.dumps(_safe({"id": row.id, "application_id": row.application_id, "due_date": row.due_date.isoformat()}))

@mcp.tool()
def complete_follow_up(follow_up_id: int) -> str:
    """Mark account-owned follow-up complete."""
    _require(WRITE)
    with _db() as db:
        row = complete_follow_up_record(db, follow_up_id, profile_id=_profile())
        return json.dumps(_safe({"id": row.id, "completed_at": row.completed_at.isoformat() if row.completed_at else None}))

@mcp.tool()
def import_applications_csv(csv_content: str, confirm: bool = False) -> str:
    """Import bounded CSV application rows using existing migration parser."""
    _require(WRITE)
    if not confirm:
        return "Refused: pass confirm=true to import applications"
    _bounded(csv_content, "csv_content", 500_000)
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
    except csv.Error as exc:
        raise ValueError("Invalid CSV") from exc
    warnings: list[str] = []
    rows = list(reader)
    if len(rows) > 1_000:
        raise ValueError("CSV contains too many rows (maximum 1000)")
    with _db() as db:
        profile_id = _profile()
        imported = 0
        skipped = 0
        for row_num, source_row in enumerate(rows, start=2):
            application = _process_csv_row(source_row, row_num, profile_id, warnings)
            if application is None:
                skipped += 1
                continue
            db.add(application)
            db.flush()
            db.add(ActivityLog(
                profile_id=profile_id,
                application_id=application.id,
                entity_type="application",
                entity_id=application.id,
                action="mcp_application_imported",
                source="mcp",
            ))
            imported += 1
        db.commit()
    return json.dumps(_safe({"imported": imported, "skipped": skipped, "warnings": warnings}))


@mcp.tool()
def account_analytics() -> str:
    """Read safe personal pipeline analytics."""
    _require(READ)
    with _db() as db:
        rows = (
            db.query(Application.status)
            .filter(Application.profile_id == _profile(), Application.archived_at.is_(None))
            .all()
        )
        counts: dict[str, int] = {}
        for (status,) in rows:
            counts[status] = counts.get(status, 0) + 1
        return json.dumps({"applications": len(rows), "by_status": counts})


@mcp.tool()
async def run_discovery(
    keywords: str = "",
    locations: str = "",
    remote_only: bool = False,
    sources: str = "",
    limit_per_source: int = 25,
    search_profile_id: int | None = None,
) -> str:
    """Run account-owned job discovery using token-derived profile."""
    _require(WRITE)
    if not isinstance(limit_per_source, int) or not 1 <= limit_per_source <= 100:
        raise ValueError("limit_per_source must be between 1 and 100")
    keyword_values = _bounded_items(keywords, "keywords")
    location_values = _bounded_items(locations, "locations")
    source_values = _bounded_items(sources, "sources")
    with _db() as db:
        result = await run_discovery_service(
            db,
            _profile(),
            keywords=keyword_values,
            locations=location_values,
            remote_only=remote_only,
            sources=source_values,
            limit_per_source=limit_per_source,
            search_profile_id=search_profile_id,
            trigger="mcp",
        )
        return json.dumps(
            _safe(
                {
                    "run_id": result["run_id"],
                    "total_found": result["total_found"],
                    "new_jobs": result["new_jobs"],
                    "duplicates": result["duplicates"],
                    "jobs": [_job_payload(job) for job in result.get("jobs", [])],
                    "warnings": result.get("warnings", []),
                    "sources_queried": result.get("sources_queried", []),
                }
            )
        )


@mcp.tool(name="discover_jobs")
async def discover_jobs(
    keywords: str = "",
    locations: str = "",
    remote_only: bool = False,
    sources: str = "",
    limit_per_source: int = 25,
    search_profile_id: int | None = None,
) -> str:
    """Compatibility name for account-owned discovery execution."""
    return await run_discovery(
        keywords=keywords,
        locations=locations,
        remote_only=remote_only,
        sources=sources,
        limit_per_source=limit_per_source,
        search_profile_id=search_profile_id,
    )


@mcp.tool()
async def score_job(
    job_description: str,
    job_title: str = "",
    job_company: str = "",
    job_url: str = "",
) -> str:
    """Score job against token-derived profile without accepting ownership input."""
    _require(WRITE)
    _bounded(job_description, "job_description", 100_000)
    _bounded(job_title, "job_title", 500)
    _bounded(job_company, "job_company", 500)
    _bounded(job_url, "job_url", 2_048)
    with _db() as db:
        scored = await score_job_service(
            db,
            _profile(),
            job_description,
            job_title=job_title or None,
            job_company=job_company or None,
            job_url=job_url or None,
        )
        return json.dumps(
            _safe(
                {
                    "id": scored.id,
                    "fit_score": scored.fit_score,
                    "readiness_score": scored.readiness_score,
                    "career_alignment": scored.career_alignment,
                    "effort_flag": scored.effort_flag,
                    "prep_level": scored.prep_level,
                    "reasoning": scored.reasoning,
                }
            )
        )

@mcp.tool()
def list_discoveries(search: str = "") -> str:
    """Read account-owned discovered jobs."""
    _require(READ)
    search = _bounded(search, "search", 255)
    with _db() as db:
        query = db.query(DiscoveredJob).filter(DiscoveredJob.profile_id == _profile())
        if search:
            query = query.filter(
                DiscoveredJob.title.ilike(f"%{search}%")
                | DiscoveredJob.company.ilike(f"%{search}%")
            )
        rows = [
            {
                "id": x.id,
                "title": x.title,
                "company": x.company,
                "location": x.location,
                "url": x.url,
                "remote": x.remote,
                "fit_score": x.fit_score,
                "posted_at": x.posted_at.isoformat() if x.posted_at else None,
            }
            for x in query.order_by(DiscoveredJob.created_at.desc()).all()
        ]
        return json.dumps(_safe(rows))

@mcp.tool()
def list_skills(search: str = "") -> str:
    """Read account-owned skills and proficiency."""
    _require(READ)
    search = _bounded(search, "search", 255)
    with _db() as db:
        query = db.query(Skill).filter(Skill.profile_id == _profile())
        if search:
            query = query.filter(Skill.name.ilike(f"%{search}%"))
        rows = [
            {
                "id": x.id,
                "name": x.name,
                "category": x.category,
                "proficiency": x.proficiency,
                "evidence_source": x.evidence_source,
            }
            for x in query.order_by(Skill.name.asc()).all()
        ]
        return json.dumps(_safe(rows))


@mcp.tool()
def create_skill(
    name: str,
    category: str,
    proficiency: str = "beginner",
    evidence_detail: str = "",
) -> str:
    """Create one manual skill owned by token-derived profile."""
    _require(WRITE)
    _bounded(name, "name", 255)
    _bounded(category, "category", 50)
    _bounded(proficiency, "proficiency", 50)
    _bounded(evidence_detail, "evidence_detail", 20_000)
    if category not in {"technical", "domain", "soft", "tools"}:
        raise ValueError("Invalid skill category")
    if proficiency not in {"beginner", "intermediate", "advanced", "expert"}:
        raise ValueError("Invalid skill proficiency")
    with _db() as db:
        skill = create_skill_record(
            db,
            _profile(),
            {
                "name": name,
                "category": category,
                "proficiency": proficiency,
                "evidence_source": "manual",
                "evidence_detail": evidence_detail or None,
            },
        )
        return json.dumps(_safe({"id": skill.id, "name": skill.name, "proficiency": skill.proficiency}))


@mcp.tool()
def update_skill(
    skill_id: int,
    name: str = "",
    category: str = "",
    proficiency: str = "",
    evidence_detail: str = "",
    reason: str = "",
) -> str:
    """Update account-owned skill and record proficiency history."""
    _require(WRITE)
    for value, field, limit in (
        (name, "name", 255),
        (category, "category", 50),
        (proficiency, "proficiency", 50),
        (evidence_detail, "evidence_detail", 20_000),
        (reason, "reason", 1_000),
    ):
        _bounded(value, field, limit)
    if category and category not in {"technical", "domain", "soft", "tools"}:
        raise ValueError("Invalid skill category")
    if proficiency and proficiency not in {"beginner", "intermediate", "advanced", "expert"}:
        raise ValueError("Invalid skill proficiency")
    changes = {
        key: value
        for key, value in {
            "name": name,
            "category": category,
            "proficiency": proficiency,
            "evidence_detail": evidence_detail,
            "reason": reason,
        }.items()
        if value
    }
    if not changes:
        raise ValueError("At least one skill field is required")
    with _db() as db:
        skill = update_skill_record(db, skill_id, _profile(), changes)
        return json.dumps(_safe({"id": skill.id, "name": skill.name, "proficiency": skill.proficiency}))

@mcp.tool()
def list_learning_resources(status: str = "") -> str:
    """Read account-owned learning resources."""
    _require(READ)
    status = _bounded(status, "status", 50)
    with _db() as db:
        query = db.query(LearningResource).filter(LearningResource.profile_id == _profile())
        if status:
            query = query.filter(LearningResource.status == status)
        rows = [
            {
                "id": x.id,
                "skill_id": x.skill_id,
                "title": x.title,
                "url": x.url,
                "provider": x.provider,
                "resource_type": x.resource_type,
                "estimated_hours": x.estimated_hours,
                "difficulty": x.difficulty,
                "status": x.status,
            }
            for x in query.order_by(LearningResource.created_at.desc()).all()
        ]
        return json.dumps(_safe(rows))


@mcp.tool()
def create_learning_resource(
    gap_id: int,
    title: str,
    url: str = "",
    provider: str = "",
    resource_type: str = "free_course",
    estimated_hours: float | None = None,
    difficulty: str = "",
) -> str:
    """Add account-owned learning resource for a profile gap."""
    _require(WRITE)
    _bounded(title, "title", 500)
    _bounded(url, "url", 2_048)
    _bounded(provider, "provider", 255)
    _bounded(resource_type, "resource_type", 50)
    _bounded(difficulty, "difficulty", 50)
    if url and not url.startswith(("http://", "https://")):
        raise ValueError("url must use http or https")
    if resource_type not in {"free_course", "paid_course", "hands_on_project"}:
        raise ValueError("Invalid resource type")
    if difficulty and difficulty not in {"beginner", "intermediate", "advanced", "expert"}:
        raise ValueError("Invalid difficulty")
    if estimated_hours is not None and (estimated_hours < 0 or estimated_hours > 10_000):
        raise ValueError("estimated_hours must be between 0 and 10000")
    with _db() as db:
        resource = create_learning_resource_record(
            db,
            gap_id,
            _profile(),
            {
                "title": title,
                "url": url or None,
                "provider": provider or None,
                "resource_type": resource_type,
                "estimated_hours": estimated_hours,
                "difficulty": difficulty or None,
            },
        )
        return json.dumps(_safe({"id": resource.id, "title": resource.title, "status": resource.status}))


@mcp.tool()
def update_learning_resource(resource_id: int, status: str) -> str:
    """Advance account-owned learning resource through valid status transitions."""
    _require(WRITE)
    _bounded(status, "status", 50)
    if status not in {"not_started", "in_progress", "completed"}:
        raise ValueError("Invalid learning status")
    with _db() as db:
        resource = update_learning_status_record(db, resource_id, _profile(), status)
        return json.dumps(_safe({"id": resource.id, "status": resource.status}))

@mcp.tool()
def settings_summary() -> str:
    """Read safe server settings without credentials or secret values."""
    _require(READ)
    return json.dumps(
        _safe(
            {
                "app_name": settings.app_name,
                "ai_provider": settings.ai_provider,
                "openrouter_model": settings.openrouter_model,
                "anthropic_model": settings.anthropic_model,
                "ollama_model": settings.ollama_model,
                "auth_enabled": settings.auth_enabled,
                "shoo_auth_enabled": settings.shoo_auth_enabled,
            }
        )
    )

@mcp.tool()
def list_provider_connections() -> str:
    """Read account-owned provider connection metadata, never credentials."""
    _require(READ)
    with _db() as db:
        rows = [
            {
                "id": x.id,
                "display_name": x.display_name,
                "provider_type": x.provider_type,
                "base_url": x.base_url,
                "model": x.model,
                "enabled": x.enabled,
            }
            for x in db.query(ProviderConnection)
            .filter(ProviderConnection.account_id == _account())
            .order_by(ProviderConnection.display_name.asc())
            .all()
        ]
        return json.dumps(_safe(rows))


@mcp.tool()
def update_provider_connection(
    connection_id: int,
    display_name: str = "",
    base_url: str = "",
    model: str = "",
    api_key: str = "",
    enabled: bool | None = None,
) -> str:
    """Update account-owned provider metadata or encrypted credential."""
    _require(WRITE)
    for value, field, limit in (
        (display_name, "display_name", 255),
        (base_url, "base_url", 2_048),
        (model, "model", 255),
        (api_key, "api_key", 4_096),
    ):
        _bounded(value, field, limit)
    if base_url and not base_url.startswith(("http://", "https://")):
        raise ValueError("base_url must use http or https")
    changes = {
        key: value
        for key, value in {
            "display_name": display_name,
            "base_url": base_url,
            "model": model,
            "api_key": api_key,
            "enabled": enabled,
        }.items()
        if value not in ("", None)
    }
    if not changes:
        raise ValueError("At least one provider field is required")
    with _db() as db:
        account = db.query(Account).filter(Account.id == _account()).first()
        if account is None:
            raise PermissionError("Account not found")
        try:
            row = get_provider_connection(db, account, connection_id)
        except LookupError as exc:
            raise ValueError("Provider connection not found") from exc
        result = update_provider_connection_record(db, row, ProviderConnectionUpdate(**changes))
        db.add(ActivityLog(
            profile_id=_profile(),
            entity_type="provider_connection",
            entity_id=connection_id,
            action="mcp_provider_connection_updated",
            source="mcp",
        ))
        db.commit()
        return json.dumps(_safe(result.model_dump(mode="json")))


@mcp.tool()
def select_provider(connection_id: int) -> str:
    """Select one enabled provider for this account; never accepts account ID."""
    _require(WRITE)
    with _db() as db:
        account_id = _account()
        account = db.query(Account).filter(Account.id == account_id).first()
        if account is None:
            raise PermissionError("Account not found")
        try:
            selected = get_provider_connection(db, account, connection_id)
        except LookupError as exc:
            raise ValueError("Provider connection not found") from exc
        for row in db.query(ProviderConnection).filter(ProviderConnection.account_id == account_id).all():
            row.enabled = row.id == selected.id
        db.add(ActivityLog(
            profile_id=_profile(),
            entity_type="provider_connection",
            entity_id=selected.id,
            action="mcp_provider_selected",
            source="mcp",
        ))
        db.commit()
        return json.dumps({"id": selected.id, "selected": True})


@mcp.tool()
def create_application(company: str, role: str, url: str = "", notes: str = "") -> str:
    """Write one pipeline application; profile ownership comes from token."""
    _require(WRITE)
    _bounded(company, "company", 255)
    _bounded(role, "role", 500)
    _bounded(url, "url", 2048)
    _bounded(notes, "notes", 20_000)
    if url and not url.startswith(("http://", "https://")):
        raise ValueError("url must use http or https")
    if len(company) > 255 or len(role) > 500 or len(notes) > 20_000:
        raise ValueError("Input exceeds size limit")
    with _db() as db:
        row = Application(
            profile_id=_profile(),
            company=company,
            role=role,
            url=url or None,
            notes=notes or None,
            status="discovered",
        )
        db.add(row)
        db.flush()
        db.add(
            ActivityLog(
                profile_id=row.profile_id,
                application_id=row.id,
                entity_type="application",
                entity_id=row.id,
                action="mcp_application_created",
                source="mcp",
            )
        )
        db.commit()
        return json.dumps({"id": row.id, "status": row.status})


@mcp.tool()
def update_application(application_id: int, status: str = "", notes: str = "") -> str:
    """Write account-owned application fields."""
    _require(WRITE)
    _bounded(status, "status", 50)
    _bounded(notes, "notes", 20_000)
    if len(notes) > 20_000:
        raise ValueError("Input exceeds size limit")
    with _db() as db:
        row = (
            db.query(Application)
            .filter(
                Application.id == application_id,
                Application.profile_id == _profile(),
                Application.archived_at.is_(None),
            )
            .first()
        )
        if row is None:
            raise ValueError("Application not found")
        if status:
            status = status.strip().lower()
            if not is_valid_transition(row.status, status):
                raise ValueError(f"Invalid status transition from '{row.status}' to '{status}'")
            row.status = status
        if notes:
            row.notes = notes
        db.add(
            ActivityLog(
                profile_id=row.profile_id,
                application_id=row.id,
                entity_type="application",
                entity_id=row.id,
                action="mcp_application_updated",
                source="mcp",
            )
        )
        db.commit()
        return json.dumps({"id": row.id, "status": row.status})


@mcp.tool()
def archive_application(application_id: int, confirm: bool = False) -> str:
    """Safely archive application; explicit confirmation required."""
    _require(WRITE)
    if not confirm:
        return "Refused: pass confirm=true to archive application"
    with _db() as db:
        row = (
            db.query(Application)
            .filter(
                Application.id == application_id,
                Application.profile_id == _profile(),
                Application.archived_at.is_(None),
            )
            .first()
        )
        if row is None:
            raise ValueError("Application not found")
        row.archived_at = datetime.now(UTC)
        db.add(
            ActivityLog(
                profile_id=row.profile_id,
                application_id=row.id,
                entity_type="application",
                entity_id=row.id,
                action="mcp_application_archived",
                source="mcp",
            )
        )
        db.commit()
        return json.dumps({"id": row.id, "archived": True})


def app():
    """Return mounted Streamable HTTP ASGI app."""
    return mcp.streamable_http_app()
