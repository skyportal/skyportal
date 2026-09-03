import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field

from baselayer.app.access import auth_or_token
from baselayer.app.env import load_env

from ...models import Comment, Group, Obj, SourceInterest, Token
from ..base import BaseHandler

env, cfg = load_env()

INTERESTED_CHANNEL = "Interested"


class SourceInterestPostBody(BaseModel):
    """Request body for registering an interest in a source."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Title of the planned work")
    description: str | None = Field(
        default=None, description="Description of the planned work"
    )
    link: str | None = Field(
        default=None, description="Link to a related page or document"
    )


class SourceInterestHandler(BaseHandler):
    @auth_or_token
    async def get(self, obj_id: str):
        """
        ---
        summary: Retrieve the interests registered on a source
        description: Retrieve the users interested in working on a source.
        tags:
          - sources
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        async with self.AsyncSession() as session:
            interests = await session.scalars(
                SourceInterest.for_obj(session.user_or_token, obj_id)
            )
            return self.success(data=[interest.to_dict() for interest in interests])

    @auth_or_token
    async def post(self, obj_id: str, *, body: SourceInterestPostBody = None):
        """
        ---
        summary: Register an interest in a source
        description: >
            Register an interest in a source. A user may register several,
            one per planned publication.
        tags:
          - sources
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        body = self.parse_body(SourceInterestPostBody)

        async with self.AsyncSession() as session:
            obj = await session.scalar(
                Obj.select(session.user_or_token).where(Obj.id == obj_id)
            )
            if obj is None:
                return self.error("Invalid objId")

            interest = SourceInterest(
                obj_id=obj_id,
                user_id=self.associated_user_object.id,
                **body.model_dump(),
            )
            session.add(interest)
            public_group = await session.scalar(
                sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
            )
            session.add(
                Comment(
                    obj_id=obj_id,
                    author_id=self.associated_user_object.id,
                    channel=INTERESTED_CHANNEL,
                    text=(
                        f"**{self.associated_user_object.username}** registered "
                        f"an interest: **{body.title}**"
                    ),
                    groups=[public_group] if public_group else [],
                    system=True,
                    bot=isinstance(self.current_user, Token),
                )
            )
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE_INTERESTS", payload={"obj_id": obj_id}
            )
            return self.success(data={"id": interest.id})

    @auth_or_token
    async def delete(self, obj_id: str, interest_id: int):
        """
        ---
        summary: Withdraw an interest in a source
        description: Delete one of the requesting user's interests.
        tags:
          - sources
        parameters:
          - in: path
            name: obj_id
            required: true
            schema:
              type: string
          - in: path
            name: interest_id
            required: true
            schema:
              type: integer
        responses:
          200:
            content:
              application/json:
                schema: Success
        """
        async with self.AsyncSession() as session:
            interest = await session.scalar(
                SourceInterest.select(session.user_or_token, mode="delete")
                .where(SourceInterest.id == interest_id)
                .where(SourceInterest.obj_id == obj_id)
            )
            if interest is None:
                return self.error("Invalid interest ID")

            title = interest.title
            await session.delete(interest)
            public_group = await session.scalar(
                sa.select(Group).where(Group.name == cfg["misc.public_group_name"])
            )
            session.add(
                Comment(
                    obj_id=obj_id,
                    author_id=self.associated_user_object.id,
                    channel=INTERESTED_CHANNEL,
                    text=(
                        f"**{self.associated_user_object.username}** withdrew "
                        f"an interest: **{title}**"
                    ),
                    groups=[public_group] if public_group else [],
                    system=True,
                    bot=isinstance(self.current_user, Token),
                )
            )
            await session.commit()

            self.push_all(
                action="skyportal/REFRESH_SOURCE_INTERESTS", payload={"obj_id": obj_id}
            )
            return self.success()
