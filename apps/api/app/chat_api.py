from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import Field

from app.auth import identity
from app.db import session as db_session
from app.schemas import Creative, InputAssets
from app.services import chat
from app.video_recipe import StrictModel
from app.responses import PromptResponse
from app.creative_direction import PlannedAnswer

router = APIRouter(prefix="/api/chat/sessions")


def chat_identity(user=Depends(identity), db=Depends(db_session)):
    # Release existing auth-initialization locks before a long model turn so a
    # concurrent authenticated request can cancel that turn.
    db.commit()
    return user


class ChatContext(StrictModel):
    templateId: str = Field(max_length=100)
    productUrl: str | None = Field(default=None, max_length=2048)
    brief: str = Field(default="", max_length=4000)
    inputAssets: InputAssets
    duration: Literal[15, 20, 30]
    aspectRatio: Literal["9:16", "1:1", "16:9"]
    language: str | None = Field(default=None, pattern=r"^[a-z]{2,3}$")
    # Recreate: the mechanism of a past video the user wants applied to a new offer.
    preferredMechanism: str | None = Field(
        default=None, max_length=80, pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
    )


class SendMessage(StrictModel):
    text: str = Field(min_length=1, max_length=4000, pattern=r"\S")
    context: ChatContext
    intent: Literal["message", "change_concept"] = "message"


class ApplyRecipe(StrictModel):
    revision: int = Field(ge=1)
    creative: Creative


class VisibleMessage(StrictModel):
    id: str
    role: Literal["user", "assistant"]
    text: str
    createdAt: str


class SessionView(StrictModel):
    id: str
    messages: list[VisibleMessage]
    answer: PlannedAnswer | None
    revision: int
    status: Literal["idle", "responding"]
    simulated: bool
    createdAt: str
    updatedAt: str


class ApplyResponse(StrictModel):
    creative: Creative
    prompt: PromptResponse


class DeleteResponse(StrictModel):
    deleted: bool


@router.post("", response_model=SessionView, status_code=201)
async def create(user=Depends(chat_identity)):
    return await chat.create(user)


@router.get("/{id}", response_model=SessionView)
def get(id: str, user=Depends(chat_identity)):
    return chat.get(user, id)


@router.get("/{id}/messages", response_model=list[VisibleMessage])
def messages(id: str, user=Depends(chat_identity)):
    return chat.get(user, id)["messages"]


@router.post("/{id}/messages", response_model=SessionView)
async def send(id: str, body: SendMessage, user=Depends(chat_identity)):
    return await chat.send(user, id, body)


@router.delete("/{id}", response_model=DeleteResponse)
async def delete(id: str, user=Depends(chat_identity)):
    return await chat.delete(user, id)


@router.post("/{id}/apply", response_model=ApplyResponse)
async def apply(id: str, body: ApplyRecipe, user=Depends(chat_identity)):
    return await chat.apply_with_references(user, id, body)
