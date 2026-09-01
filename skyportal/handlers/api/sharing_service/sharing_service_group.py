from typing import Annotated

import sqlalchemy as sa
from pydantic import Field
from skyportal_py_models.sharing_services import (
    SharingServiceGroupPutBody,
    SharingServiceGroupPutResponse,
)
from sqlalchemy.orm import selectinload

from baselayer.app.access import permissions
from baselayer.log import make_log

from ....models import (
    GroupUser,
    SharingService,
    SharingServiceGroup,
)
from ....utils.data_access import check_access_to_sharing_service_async
from ....utils.parse import str_to_bool
from ...base import BaseHandler

SharingServiceId = Annotated[
    int, Field(description="The ID of the external sharing service")
]

log = make_log("api/sharing_service_group")


class SharingServiceGroupHandler(BaseHandler):
    @permissions(["Manage sharing services"])
    async def put(
        self,
        sharing_service_id: SharingServiceId,
        group_id: Annotated[
            int | None, Field(description="ID of the group to edit")
        ] = None,
        *,
        body: SharingServiceGroupPutBody = None,
    ) -> SharingServiceGroupPutResponse:
        """
        ---
        summary: Add or edit a group for an external sharing service
        description: Add or edit a group for an external sharing service
        tags:
            - external sharing service
        """
        body = self.parse_body(SharingServiceGroupPutBody)
        auto_share_to_tns = (
            str_to_bool(body.auto_share_to_tns)
            if "auto_share_to_tns" in body.model_fields_set
            else None
        )
        auto_share_to_hermes = (
            str_to_bool(body.auto_share_to_hermes)
            if "auto_share_to_hermes" in body.model_fields_set
            else None
        )
        auto_sharing_allow_bots = (
            str_to_bool(body.auto_sharing_allow_bots)
            if "auto_sharing_allow_bots" in body.model_fields_set
            else None
        )
        owner = str_to_bool(body.owner) if "owner" in body.model_fields_set else None

        group_id = body.group_id if "group_id" in body.model_fields_set else group_id
        if group_id is None:
            return self.error(
                "You must specify a group_id when giving or editing the access to a sharing service for a group"
            )
        try:
            group_id = int(group_id)
            sharing_service_id = int(sharing_service_id)
        except ValueError:
            return self.error(
                f"Invalid group_id/sharing_service_id: {group_id}/{sharing_service_id}, must be integers"
            )

        async with self.AsyncSession() as session:
            # Check if the user has access to the sharing_service and group
            await check_access_to_sharing_service_async(
                session, session.user_or_token, sharing_service_id
            )
            self.current_user.assert_group_accessible(group_id)

            # check if a sharing service group already exist
            group = await session.scalar(
                SharingServiceGroup.select(session.user_or_token)
                .options(
                    selectinload(SharingServiceGroup.auto_publishers),
                    selectinload(SharingServiceGroup.sharing_service).selectinload(
                        SharingService.groups
                    ),
                )
                .where(
                    SharingServiceGroup.sharing_service_id == sharing_service_id,
                    SharingServiceGroup.group_id == group_id,
                )
            )

            if group:
                # If this is an edit, check if the user has selected at least one field to update
                if (
                    auto_share_to_tns is None
                    and auto_share_to_hermes is None
                    and auto_sharing_allow_bots is None
                    and owner is None
                ):
                    return self.error(
                        "You must update at least one of: auto_share_to_tns, auto_share_to_hermes, owner, or auto_sharing_allow_bots when editing a sharing service group."
                    )
                if (
                    auto_share_to_tns is not None
                    and auto_share_to_tns != group.auto_share_to_tns
                ):
                    group.auto_share_to_tns = auto_share_to_tns
                if (
                    auto_share_to_hermes is not None
                    and auto_share_to_hermes != group.auto_share_to_hermes
                ):
                    group.auto_share_to_hermes = auto_share_to_hermes
                if (
                    auto_sharing_allow_bots is not None
                    and auto_sharing_allow_bots != group.auto_sharing_allow_bots
                ):
                    # if the user is trying to set auto_sharing_allow_bots to False,
                    # we need to verify that none of the existing auto publishers are bots
                    if auto_sharing_allow_bots is False:
                        ap_result = await session.scalars(
                            sa.select(GroupUser)
                            .options(selectinload(GroupUser.user))
                            .where(
                                GroupUser.id.in_(
                                    [r.group_user_id for r in group.auto_publishers]
                                )
                            )
                        )
                        if any(
                            group_user.user.is_bot for group_user in ap_result.all()
                        ):
                            return self.error(
                                "Cannot set auto_sharing_allow_bots to False when one or more auto_publishers are bots. Remove the bots from the auto_publishers first."
                            )
                    group.auto_sharing_allow_bots = auto_sharing_allow_bots

                if owner is not None and owner != group.owner:
                    # Check if this is the only owner group
                    owners = [
                        group.group_id
                        for group in group.sharing_service.groups
                        if group.owner
                    ]

                    if owners == [group_id]:
                        return self.error(
                            "Cannot remove ownership from the only group owning this sharing service. Please assign another group as owner first."
                        )

                    group.owner = owner

                await session.commit()
                self.push(
                    action="skyportal/REFRESH_SHARING_SERVICES",
                )
                return self.success(data={"id": group.id})
            else:
                # Check if the association already exists but is inaccessible to the current user
                existing_association = await session.scalar(
                    sa.select(SharingServiceGroup).where(
                        SharingServiceGroup.sharing_service_id == sharing_service_id,
                        SharingServiceGroup.group_id == group_id,
                    )
                )
                if existing_association is not None:
                    return self.error(
                        f"Group {group_id} already has access to sharing service {sharing_service_id}, but user is not allowed to edit it"
                    )

                sharing_service_group = SharingServiceGroup(
                    sharing_service_id=sharing_service_id,
                    group_id=group_id,
                    auto_share_to_tns=auto_share_to_tns,
                    auto_share_to_hermes=auto_share_to_hermes,
                    auto_sharing_allow_bots=auto_sharing_allow_bots,
                    owner=owner,
                )

                session.add(sharing_service_group)
                await session.commit()
                self.push(
                    action="skyportal/REFRESH_SHARING_SERVICES",
                )
                return self.success(data={"id": sharing_service_group.id})

    @permissions(["Manage sharing services"])
    async def delete(
        self,
        sharing_service_id: SharingServiceId,
        group_id: Annotated[
            int,
            Field(
                description="The ID of the group to remove from the external sharing service"
            ),
        ],
    ):
        """
        ---
        summary: Delete a group from an external sharing service
        description: Delete a group from an external sharing service
        tags:
            - external sharing service
        responses:
            200:
                content:
                    application/json:
                        schema: Success
            400:
                content:
                    application/json:
                        schema: Error
        """
        if group_id is None:
            return self.error(
                "You must specify a group_id when giving or editing the access to a sharing service for a group"
            )
        try:
            group_id = int(group_id)
            sharing_service_id = int(sharing_service_id)
        except (TypeError, ValueError):
            return self.error(
                f"Invalid group_id/sharing_service_id: {group_id}/{sharing_service_id}"
            )
        async with self.AsyncSession() as session:
            # Check if the user has access to the sharing_service and group
            await check_access_to_sharing_service_async(
                session, session.user_or_token, sharing_service_id
            )
            self.current_user.assert_group_accessible(group_id)

            # check if the group already has access to the sharing_service
            sharing_service_group = await session.scalar(
                SharingServiceGroup.select(session.user_or_token, mode="delete")
                .options(
                    selectinload(SharingServiceGroup.sharing_service).selectinload(
                        SharingService.groups
                    )
                )
                .where(
                    SharingServiceGroup.sharing_service_id == sharing_service_id,
                    SharingServiceGroup.group_id == group_id,
                )
            )

            if sharing_service_group is None:
                return self.error(
                    f"Group {group_id} does not have access to sharing service {sharing_service_id}, or user is not allowed to remove it"
                )

            # Prevent removing the last owner group
            owners = [
                g for g in sharing_service_group.sharing_service.groups if g.owner
            ]

            if len(owners) == 1 and sharing_service_group.owner:
                return self.error(
                    "Cannot delete the only group owning this sharing service, add another group as an owner first."
                )

            await session.delete(sharing_service_group)
            await session.commit()
            self.push(
                action="skyportal/REFRESH_SHARING_SERVICES",
            )
            return self.success()
