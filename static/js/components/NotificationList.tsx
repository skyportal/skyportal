import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha, Theme } from "@mui/material/styles";

import NotificationsIcon from "@mui/icons-material/NotificationsOutlined";
import NotificationsOffIcon from "@mui/icons-material/NotificationsOffOutlined";
import DoneIcon from "@mui/icons-material/Done";
import RemoveDoneIcon from "@mui/icons-material/RemoveDone";
import DeleteIcon from "@mui/icons-material/DeleteOutlineOutlined";
import ChatBubbleIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import CategoryIcon from "@mui/icons-material/CategoryOutlined";
import ArticleIcon from "@mui/icons-material/ArticleOutlined";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import FlareIcon from "@mui/icons-material/FlareOutlined";
import SourceIcon from "@mui/icons-material/AdjustOutlined";
import LockIcon from "@mui/icons-material/LockOutlined";
import GroupIcon from "@mui/icons-material/GroupOutlined";
import EventIcon from "@mui/icons-material/EventOutlined";
import AlarmIcon from "@mui/icons-material/AlarmOutlined";
import ScienceIcon from "@mui/icons-material/ScienceOutlined";
import SendIcon from "@mui/icons-material/SendOutlined";
import VisibilityIcon from "@mui/icons-material/VisibilityOutlined";
import AutorenewIcon from "@mui/icons-material/AutorenewOutlined";

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import ReactMarkdown from "react-markdown";

import { PanelEmptyState } from "./HeaderPanel";
import { UserNotification } from "../ducks/userNotifications";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const unreadTint = (theme: Theme, light: number, dark: number) =>
  alpha(
    theme.palette.primary.main,
    theme.palette.mode === "dark" ? dark : light,
  );

const typeIcon = (notificationType?: string | null, url?: string | null) => {
  const type = (notificationType || "").toLowerCase();
  if (type.includes("mention") || type.includes("comment"))
    return <ChatBubbleIcon />;
  if (type.includes("reminder")) return <AlarmIcon />;
  if (type.includes("report") || type.includes("summary"))
    return <ArticleIcon />;
  if (type.includes("classification")) return <CategoryIcon />;
  if (type.includes("spectrum") || type.includes("photometry"))
    return <ShowChartIcon />;
  if (type.includes("gcn")) return <FlareIcon />;
  if (type.includes("group") || type.includes("user")) return <GroupIcon />;
  if (type.includes("shift")) return <EventIcon />;
  if (type.includes("analysis")) return <ScienceIcon />;
  if (type.includes("facility") || type.includes("followup"))
    return <SendIcon />;
  if (type.includes("observation")) return <VisibilityIcon />;
  if (type.includes("api")) return <AutorenewIcon />;

  // many notifications have no type at all, so fall back on where they point to
  const target = url || "";
  if (target.startsWith("/shift")) return <EventIcon />;
  if (target.startsWith("/group")) return <GroupIcon />;
  if (target.startsWith("/gcn_events")) return <FlareIcon />;
  if (target.startsWith("/data_access")) return <LockIcon />;
  if (target.startsWith("/source")) return <SourceIcon />;
  return <NotificationsIcon />;
};

interface NotificationListProps {
  notifications: UserNotification[];
  onSetViewed: (notificationID: number, viewed: boolean) => void;
  onDelete: (notificationID: number) => void;
}

const NotificationList = ({
  notifications,
  onSetViewed,
  onDelete,
}: NotificationListProps) => {
  if (notifications.length === 0)
    return (
      <PanelEmptyState
        icon={<NotificationsOffIcon />}
        text="No notifications"
      />
    );

  return (
    <List disablePadding>
      {notifications.map(
        ({ id, text, url, viewed, notification_type, created_at }, index) => (
          <ListItem
            key={id}
            disablePadding
            divider={index < notifications.length - 1}
            sx={{
              ...(!viewed && {
                bgcolor: (theme) => unreadTint(theme, 0.07, 0.14),
                "& > .MuiListItemButton-root:hover": {
                  bgcolor: (theme: Theme) => unreadTint(theme, 0.14, 0.22),
                },
              }),
              "& > .MuiListItemButton-root": { pr: 10 },
              "& .MuiListItemSecondaryAction-root": {
                opacity: 0,
                transition: "opacity 150ms",
              },
              "&:hover .MuiListItemSecondaryAction-root, &:focus-within .MuiListItemSecondaryAction-root":
                {
                  opacity: 1,
                },
              "@media (hover: none)": {
                "& .MuiListItemSecondaryAction-root": { opacity: 1 },
              },
            }}
            secondaryAction={
              <Box sx={{ display: "flex" }}>
                <Tooltip title={viewed ? "Mark unread" : "Mark read"}>
                  <IconButton
                    size="small"
                    data-testid={`${
                      viewed ? "markUnreadButton" : "markReadButton"
                    }${id}`}
                    onClick={() => onSetViewed(id, !viewed)}
                  >
                    {viewed ? (
                      <RemoveDoneIcon fontSize="small" />
                    ) : (
                      <DoneIcon fontSize="small" />
                    )}
                  </IconButton>
                </Tooltip>
                <Tooltip title="Delete">
                  <IconButton
                    size="small"
                    data-testid={`deleteNotificationButton${id}`}
                    onClick={() => onDelete(id)}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            }
          >
            <ListItemButton
              component="a"
              href={url || undefined}
              onClick={() => onSetViewed(id, true)}
              data-testid={`notification${id}`}
              sx={{ alignItems: "flex-start", gap: 1.5, py: 1.5 }}
            >
              <Box
                sx={{
                  flexShrink: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "2rem",
                  height: "2rem",
                  borderRadius: "50%",
                  bgcolor: (theme) =>
                    viewed
                      ? theme.palette.action.hover
                      : alpha(theme.palette.primary.main, 0.2),
                  color: viewed ? "text.secondary" : "primary.main",
                  "& svg": { fontSize: "1.2rem" },
                }}
              >
                {typeIcon(notification_type, url)}
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <Box
                  sx={{
                    fontSize: "0.875rem",
                    lineHeight: 1.45,
                    overflowWrap: "anywhere",
                    fontWeight: viewed ? 400 : 600,
                    "& p": { m: 0 },
                    "& em": { fontStyle: "normal", fontWeight: 600 },
                  }}
                >
                  <ReactMarkdown>{text}</ReactMarkdown>
                </Box>
                {created_at && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: "block", mt: 0.25 }}
                  >
                    {dayjs().to(dayjs.utc(`${created_at}Z`))}
                  </Typography>
                )}
              </Box>
            </ListItemButton>
          </ListItem>
        ),
      )}
    </List>
  );
};

export default NotificationList;
