import GroupWorkIcon from "@mui/icons-material/GroupWork";
import GroupsIcon from "@mui/icons-material/Groups";
import Avatar from "@mui/material/Avatar";

import UserAvatar from "../user/UserAvatar";
import { otherMembers } from "./names";
import type { Discussion } from "../../ducks/discussions";

interface DiscussionAvatarProps {
  discussion: Discussion;
  myId?: number | undefined;
  size: number;
}

const DiscussionAvatar = ({
  discussion,
  myId,
  size,
}: DiscussionAvatarProps) => {
  const other = discussion.is_direct
    ? otherMembers(discussion, myId)[0]
    : undefined;
  if (other) {
    return (
      <UserAvatar
        size={size}
        userId={other.id}
        firstName={other.first_name}
        lastName={other.last_name}
        username={other.username}
        gravatarUrl={other.gravatar_url ?? ""}
        isBot={other.is_bot}
        noTooltip
      />
    );
  }
  return (
    <Avatar sx={{ width: size, height: size, bgcolor: "primary.main" }}>
      {discussion.group ? (
        <GroupWorkIcon sx={{ fontSize: size * 0.55 }} />
      ) : (
        <GroupsIcon sx={{ fontSize: size * 0.55 }} />
      )}
    </Avatar>
  );
};

export default DiscussionAvatar;
