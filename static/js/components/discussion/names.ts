import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { getUserRealName } from "../user/UserAvatar";
import type { Discussion, DiscussionUser } from "../../ducks/discussions";

dayjs.extend(utc);

export const userName = (user: DiscussionUser) =>
  getUserRealName(user.first_name, user.last_name) || user.username;

export const otherMembers = (discussion: Discussion, myId?: number) =>
  (discussion.members ?? []).filter((member) => member.id !== myId);

export const discussionTitle = (discussion: Discussion, myId?: number) =>
  discussion.name ||
  discussion.group?.name ||
  otherMembers(discussion, myId).map(userName).join(", ") ||
  "Only you";

export const fromServer = (time: string) => dayjs.utc(`${time}Z`).local();

export const shortTime = (time: string) => {
  const date = fromServer(time);
  if (date.isSame(dayjs(), "day")) return date.format("HH:mm");
  if (date.isSame(dayjs(), "year")) return date.format("MMM D");
  return date.format("YYYY-MM-DD");
};
