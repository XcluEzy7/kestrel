"""Authenticated API for user-configured OpenAI-compatible inference."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from career_os.database import get_db
from career_os.dependencies import current_account
from career_os.models.auth import Account
from career_os.schemas.provider_connections import (
    ProviderCompletionRequest,
    ProviderCompletionResponse,
    ProviderConnectionCreate,
    ProviderConnectionListResponse,
    ProviderConnectionResponse,
    ProviderConnectionUpdate,
    ProviderDiscoveryRequest,
    ProviderModelsResponse,
    ProviderTestResponse,
)
from career_os.services.provider_connections import (
    complete,
    create_connection,
    discover_models,
    discover_draft_models,
    get_connection,
    list_connections,
    test_connection,
    update_connection,
)

router = APIRouter(prefix="/api/provider-connections", tags=["provider-connections"])
AccountDep = Annotated[Account, Depends(current_account)]


def _require_account(account: Account | None) -> Account:
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return account


@router.get("", response_model=ProviderConnectionListResponse)
def list_provider_connections(
    account: AccountDep, db: Annotated[Session, Depends(get_db)]
) -> ProviderConnectionListResponse:
    return ProviderConnectionListResponse(
        connections=list_connections(db, _require_account(account))
    )


@router.post("", response_model=ProviderConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_provider_connection(
    payload: ProviderConnectionCreate,
    account: AccountDep,
    db: Annotated[Session, Depends(get_db)],
) -> ProviderConnectionResponse:
    try:
        owner = _require_account(account)
        response = create_connection(db, owner, payload)
        if response.model is None:
            row = get_connection(db, owner, response.id)
            try:
                discovered = await discover_models(row)
                row.model = next((item.strip() for item in discovered.models if item.strip()), "") or None
                if row.model is None:
                    raise ValueError("Provider did not report a usable model")
                db.commit()
                db.refresh(row)
                response.model = row.model
                return response
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                db.delete(row)
                db.commit()
                raise HTTPException(status_code=502, detail="Model discovery failed") from exc
        return response
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{connection_id}", response_model=ProviderConnectionResponse)
def update_provider_connection(
    connection_id: int,
    payload: ProviderConnectionUpdate,
    account: AccountDep,
    db: Annotated[Session, Depends(get_db)],
) -> ProviderConnectionResponse:
    try:
        row = get_connection(db, _require_account(account), connection_id)
        return update_connection(db, row, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider_connection(
    connection_id: int,
    account: AccountDep,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    try:
        row = get_connection(db, _require_account(account), connection_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.delete(row)
    db.commit()


@router.post("/{connection_id}/test", response_model=ProviderTestResponse)
async def test_provider_connection(
    connection_id: int,
    account: AccountDep,
    db: Annotated[Session, Depends(get_db)],
) -> ProviderTestResponse:
    try:
        row = get_connection(db, _require_account(account), connection_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await test_connection(row)


@router.post("/models/discover", response_model=ProviderModelsResponse)
async def discover_draft_provider_models(
    payload: ProviderDiscoveryRequest, account: AccountDep
) -> ProviderModelsResponse:
    _require_account(account)
    try:
        return await discover_draft_models(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Model discovery failed") from exc


@router.get("/{connection_id}/models", response_model=ProviderModelsResponse)
async def discover_provider_models(
    connection_id: int,
    account: AccountDep,
    db: Annotated[Session, Depends(get_db)],
) -> ProviderModelsResponse:
    try:
        row = get_connection(db, _require_account(account), connection_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        return await discover_models(row)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Model discovery failed") from exc


@router.post("/{connection_id}/complete", response_model=ProviderCompletionResponse)
async def complete_provider_connection(
    connection_id: int,
    payload: ProviderCompletionRequest,
    account: AccountDep,
    db: Annotated[Session, Depends(get_db)],
) -> ProviderCompletionResponse:
    try:
        row = get_connection(db, _require_account(account), connection_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        return await complete(row, payload.prompt, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Provider completion failed") from exc
