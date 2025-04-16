import sqlalchemy as sa

from baselayer.app.access import permissions
from baselayer.log import make_log

from ....models import (
    GroupUser,
    TNSRobot,
    TNSRobotGroup,
)
from ...base import BaseHandler

log = make_log("api/tns_robot_group")


class TNSRobotGroupHandler(BaseHandler):
    @permissions(["Manage TNS robots"])
    def put(self, tnsrobot_id, group_id=None):
        """
        ---
        summary: Add or edit a group for a TNS robot
        description: Add or edit a group for a TNS robot
        tags:
            - tns robot
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: integer
              description: ID of the TNS robot
            - in: path
              name: group_id
              required: false
              schema:
                type: integer
              description: ID of the group to edit
        requestBody:
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            group_id:
                                type: integer
                                description: ID of the group to add
                            auto_report:
                                type: boolean
                                description: Whether to automatically report to this group
                            owner:
                                type: boolean
                                description: Whether this group is the owner of the TNS robot
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
        # the PUT handler is used to add or edit a group
        data = self.get_json()
        auto_report = data.get("auto_report", None)
        auto_report_allow_bots = data.get("auto_report_allow_bots", None)
        owner = data.get("owner", None)
        if group_id is None:
            group_id = int(data.get("group_id", None))

        try:
            group_id = int(group_id)
        except ValueError:
            return self.error(f"Invalid group_id: {group_id}, must be an integer")

        if auto_report is not None:
            # try to convert the auto_report to a boolean
            if str(auto_report) in ["True", "true", "1", "t"]:
                auto_report = True
            elif str(auto_report) in ["False", "false", "0", "f"]:
                auto_report = False
            else:
                return self.error(f"Invalid auto_report value: {auto_report}")

        if auto_report_allow_bots is not None:
            # try to convert the auto_report_allow_bots to a boolean
            if str(auto_report_allow_bots) in ["True", "true", "1", "t"]:
                auto_report_allow_bots = True
            elif str(auto_report_allow_bots) in ["False", "false", "0", "f"]:
                auto_report_allow_bots = False
            else:
                return self.error(
                    f"Invalid auto_report_allow_bots value: {auto_report_allow_bots}"
                )

        if owner is not None:
            # try to convert the owner to a boolean
            if str(owner) in ["True", "true", "1", "t"]:
                owner = True
            elif str(owner) in ["False", "false", "0", "f"]:
                owner = False
            else:
                return self.error(f"Invalid owner value: {owner}")

        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(
                    f"No TNSRobot with ID {tnsrobot_id}, or unnaccessible"
                )

            if group_id is None:
                return self.error(
                    "You must specify a group_id when giving or editing the access to a TNSRobot for a group"
                )

            # verify that this group is accessible by the user
            if not self.current_user.is_system_admin and group_id not in [
                g.id for g in self.current_user.accessible_groups
            ]:
                return self.error(
                    f"Group {group_id} is not accessible by the current user"
                )

            # check if the group already has access to the tnsrobot
            tnsrobot_group = session.scalar(
                TNSRobotGroup.select(session.user_or_token, mode="update").where(
                    TNSRobotGroup.tnsrobot_id == tnsrobot_id,
                    TNSRobotGroup.group_id == group_id,
                )
            )

            if tnsrobot_group is not None:
                # the user wants to edit the tnsrobot_group
                if (
                    auto_report is None
                    and owner is None
                    and auto_report_allow_bots is None
                ):
                    return self.error(
                        "You must specify auto_report, owner and/or auto_report_allow_bots when editing a TNSRobotGroup"
                    )

                if (
                    auto_report is not None
                    and auto_report != tnsrobot_group.auto_report
                ):
                    tnsrobot_group.auto_report = auto_report
                if (
                    auto_report_allow_bots is not None
                    and auto_report_allow_bots != tnsrobot_group.auto_report_allow_bots
                ):
                    # if the user is trying to set auto_report_allow_bots to False,
                    # we need to verify that none of the existing autoreporter are bots
                    if auto_report_allow_bots is False:
                        autoreporters_group_users = session.scalars(
                            sa.select(GroupUser).where(
                                GroupUser.id.in_(
                                    [
                                        r.group_user_id
                                        for r in tnsrobot_group.autoreporters
                                    ]
                                )
                            )
                        )
                        if any(gu.user.is_bot for gu in autoreporters_group_users):
                            return self.error(
                                "Cannot set auto_report_allow_bots to False when one or more autoreporters are bots. Remove the bots from the autoreporters first."
                            )
                    tnsrobot_group.auto_report_allow_bots = auto_report_allow_bots

                if owner is not None and owner != tnsrobot_group.owner:
                    # here we want to be careful not to remove the last owner
                    # so we check if the tnsrobot has any other groups that are owners.
                    # If this is the only one, we return an error
                    owners = []
                    for g in tnsrobot_group.tnsrobot.groups:
                        if g.owner is True:
                            owners.append(g.group_id)
                    if len(owners) == 1 and owners[0] == group_id:
                        return self.error(
                            "Cannot remove ownership from the only tnsrobot_group owning this robot, add another group as an owner first."
                        )
                    tnsrobot_group.owner = owner

                session.commit()
                self.push(
                    action="skyportal/REFRESH_TNSROBOTS",
                )
                return self.success(data=tnsrobot_group)
            else:
                # verify that we don't actually have a tnsrobot_group with this group and tnsrobot
                # but the current user simply does not have access to it
                existing_tnsrobot_group = session.scalar(
                    sa.select(TNSRobotGroup).where(
                        TNSRobotGroup.tnsrobot_id == tnsrobot_id,
                        TNSRobotGroup.group_id == group_id,
                    )
                )
                if existing_tnsrobot_group is not None:
                    return self.error(
                        f"Group {group_id} already has access to TNSRobot {tnsrobot_id}, but user is not allowed to edit it"
                    )

                # create the new tnsrobot_group
                tnsrobot_group = TNSRobotGroup(
                    tnsrobot_id=tnsrobot_id,
                    group_id=group_id,
                    auto_report=bool(auto_report),
                    auto_report_allow_bots=bool(auto_report_allow_bots),
                    owner=bool(owner),
                )

                session.add(tnsrobot_group)
                session.commit()
                self.push(
                    action="skyportal/REFRESH_TNSROBOTS",
                )
                return self.success(data={"id": tnsrobot_group.id})

    @permissions(["Manage TNS robots"])
    def delete(self, tnsrobot_id, group_id):
        """
        ---
        summary: Delete a group from a TNS robot
        description: Delete a group from a TNSRobot
        tags:
            - tns robot
        parameters:
            - in: path
              name: tnsrobot_id
              required: true
              schema:
                type: string
              description: The ID of the TNSRobot
            - in: path
              name: group_id
              required: true
              schema:
                type: string
              description: The ID of the group to remove from the TNSRobot
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
        # the DELETE handler is used to remove a group from a TNSRobot
        with self.Session() as session:
            # verify that the user has access to the tnsrobot
            tnsrobot = session.scalar(
                TNSRobot.select(session.user_or_token).where(TNSRobot.id == tnsrobot_id)
            )
            if tnsrobot is None:
                return self.error(
                    f"No TNSRobot with ID {tnsrobot_id}, or unnaccessible"
                )

            if group_id is None:
                return self.error(
                    "You must specify a group_id when giving or editing  the access to a TNSRobot for a group"
                )

            # verify that this group is accessible by the user
            if not self.current_user.is_system_admin and group_id not in [
                g.id for g in self.current_user.accessible_groups
            ]:
                return self.error(
                    f"Group {group_id} is not accessible by the current user"
                )

            # check if the group already has access to the tnsrobot
            tnsrobot_group = session.scalar(
                TNSRobotGroup.select(session.user_or_token, mode="delete").where(
                    TNSRobotGroup.tnsrobot_id == tnsrobot_id,
                    TNSRobotGroup.group_id == group_id,
                )
            )

            if tnsrobot_group is None:
                return self.error(
                    f"Group {group_id} does not have access to TNSRobot {tnsrobot_id}, or user is not allowed to remove it"
                )

            # here we want to be careful not to remove the last owner
            owners_nb = 0
            for g in tnsrobot_group.tnsrobot.groups:
                if g.owner is True:
                    owners_nb += 1
            if owners_nb == 1 and tnsrobot_group.owner is True:
                return self.error(
                    "Cannot delete the only tnsrobot_group owning this robot, add another group as an owner first."
                )

            session.delete(tnsrobot_group)
            session.commit()
            self.push(
                action="skyportal/REFRESH_TNSROBOTS",
            )
            return self.success()
