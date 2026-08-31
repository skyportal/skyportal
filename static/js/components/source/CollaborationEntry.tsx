import { ReactNode } from "react";
import CloseIcon from "@mui/icons-material/Close";
import IconButton from "@mui/material/IconButton";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import { makeStyles } from "tss-react/mui";
import { alpha } from "@mui/material/styles";

import UserAvatar from "../user/UserAvatar";
import type { CollaborationUser } from "../../ducks/sourceInterests";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles()((theme) => ({
  entry: {
    fontSize: "90%",
    display: "flex",
    alignItems: "flex-start",
    padding: "0.125rem",
    margin: "0 0.125rem 0.125rem 0",
    borderRadius: "1rem",
    "&:hover": {
      backgroundColor: theme.palette.mode === "dark" ? "#3a3a3a" : "#e0e0e0",
    },
  },
  avatar: {
    margin: "0.5em",
  },
  content: {
    display: "flex",
    flexDirection: "column",
    flexGrow: 1,
    minWidth: 0,
    padding: "0.3125rem 0.625rem 0.3125rem 0",
  },
  header: {
    display: "flex",
    alignItems: "baseline",
  },
  username: {
    fontWeight: "bold",
    fontSize: "90%",
    whiteSpace: "nowrap",
    marginRight: "0.5em",
    color: "#76aace",
  },
  time: {
    color: "gray",
    fontSize: "80%",
    marginRight: "1em",
  },
  delete: {
    "&:hover": {
      color: "#e63946",
    },
  },
  bot: {
    fontSize: "80%",
    color: theme.palette.text.secondary,
    backgroundColor: alpha(theme.palette.text.primary, 0.05),
    "&:hover": {
      backgroundColor: alpha(theme.palette.text.primary, 0.09),
    },
  },
}));

interface CollaborationEntryProps {
  user: CollaborationUser;
  createdAt: string;
  onDelete?: (() => void) | undefined;
  children: ReactNode;
}

const CollaborationEntry = ({
  user,
  createdAt,
  onDelete,
  children,
}: CollaborationEntryProps) => {
  const { classes, cx } = useStyles();
  return (
    <div className={cx(classes.entry, user.is_bot && classes.bot)}>
      <div className={classes.avatar}>
        <UserAvatar
          size={24}
          firstName={user.first_name}
          lastName={user.last_name}
          username={user.username}
          gravatarUrl={user.gravatar_url}
          isBot={user.is_bot}
        />
      </div>
      <div className={classes.content}>
        <div className={classes.header}>
          <span className={classes.username}>{user.username}</span>
          <span className={classes.time}>
            {dayjs().to(dayjs.utc(`${createdAt}Z`))}
          </span>
        </div>
        {children}
      </div>
      {onDelete && (
        <IconButton size="small" className={classes.delete} onClick={onDelete}>
          <CloseIcon fontSize="small" />
        </IconButton>
      )}
    </div>
  );
};

export default CollaborationEntry;
