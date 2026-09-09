import React from "react";

import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import Popper from "@mui/material/Popper";
import Paper from "@mui/material/Paper";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import MUINotificationsIcon from "@mui/icons-material/NotificationsOutlined";
import NotificationsOffIcon from "@mui/icons-material/NotificationsOffOutlined";
import DoneIcon from "@mui/icons-material/Done";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import RemoveDoneIcon from "@mui/icons-material/RemoveDone";
import DeleteIcon from "@mui/icons-material/DeleteOutlineOutlined";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweepOutlined";
import ChatBubbleIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import CategoryIcon from "@mui/icons-material/CategoryOutlined";
import ArticleIcon from "@mui/icons-material/ArticleOutlined";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import FlareIcon from "@mui/icons-material/FlareOutlined";
import StarIcon from "@mui/icons-material/Star";
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

import {
  UserNotification,
  useGetNotificationsQuery,
  useUpdateNotificationMutation,
  useUpdateAllNotificationsMutation,
  useDeleteNotificationMutation,
  useDeleteAllNotificationsMutation,
} from "../ducks/userNotifications";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const POPPER_MODIFIERS = [
  { name: "offset", options: { offset: [0, 8] } },
  { name: "preventOverflow", options: { padding: 8 } },
];

const typeIcon = ({ notification_type, url }: UserNotification) => {
  const type = (notification_type || "").toLowerCase();
  if (type.includes("mention") || type.includes("comment"))
    return <ChatBubbleIcon />;
  if (type.includes("reminder")) return <AlarmIcon />;
  if (type.includes("report") || type.includes("summary"))
    return <ArticleIcon />;
  if (type.includes("classification")) return <CategoryIcon />;
  if (type.includes("spectrum") || type.includes("photometry"))
    return <ShowChartIcon />;
  if (type.includes("gcn")) return <FlareIcon />;
  if (type.includes("favorite")) return <StarIcon />;
  if (type.includes("group") || type.includes("user")) return <GroupIcon />;
  if (type.includes("shift")) return <EventIcon />;
  if (type.includes("analysis")) return <ScienceIcon />;
  if (type.includes("facility") || type.includes("followup"))
    return <SendIcon />;
  if (type.includes("observation")) return <VisibilityIcon />;
  if (type.includes("api")) return <AutorenewIcon />;

  // many notifications carry no type, so fall back on where they point to
  const target = url || "";
  if (target.startsWith("/shift")) return <EventIcon />;
  if (target.startsWith("/group")) return <GroupIcon />;
  if (target.startsWith("/gcn_events")) return <FlareIcon />;
  if (target.startsWith("/data_access")) return <LockIcon />;
  if (target.startsWith("/source")) return <SourceIcon />;
  return <MUINotificationsIcon />;
};

const Notifications = () => {
  const { data: notifications } = useGetNotificationsQuery();
  const [updateNotification] = useUpdateNotificationMutation();
  const [updateAllNotifications] = useUpdateAllNotificationsMutation();
  const [deleteNotificationMutation] = useDeleteNotificationMutation();
  const [deleteAllNotificationsMutation] = useDeleteAllNotificationsMutation();

  const count = notifications?.length || 0;
  const unreadCount = notifications
    ? notifications.filter((n) => !n.viewed).length
    : 0;

  // Popover logic
  const [anchorEl, setAnchorEl] = React.useState<any>(null);
  const handleClickOpen = (event: any) => {
    setAnchorEl(anchorEl ? null : event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const open = Boolean(anchorEl);

  React.useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") handleClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  const deleteAllNotifications = () => {
    deleteAllNotificationsMutation();
    handleClose();
  };

  const markAllRead = () => {
    updateAllNotifications({ viewed: true });
  };

  const markAllUnread = () => {
    updateAllNotifications({ viewed: false });
  };

  const markRead = (notificationID: number) => {
    updateNotification({
      notificationID,
      data: { viewed: true },
    });
  };

  const markUnread = (notificationID: number) => {
    updateNotification({
      notificationID,
      data: { viewed: false },
    });
  };

  const deleteNotification = (notificationID: number) => {
    deleteNotificationMutation(notificationID);
  };

  return (
    <>
      <Tooltip title={open ? "" : "Notifications"}>
        <IconButton
          onClick={handleClickOpen}
          data-testid="notificationsButton"
          size="large"
          style={{ padding: 0, margin: 0 }}
        >
          <Badge
            badgeContent={unreadCount}
            overlap="circular"
            color={unreadCount > 0 ? "error" : "primary"}
            data-testid="notificationsBadge"
          >
            <MUINotificationsIcon fontSize="large" color="primary" />
          </Badge>
        </IconButton>
      </Tooltip>
      <Popper
        open={open}
        anchorEl={anchorEl}
        placement="bottom"
        modifiers={POPPER_MODIFIERS}
        sx={{ zIndex: (theme) => theme.zIndex.modal }}
      >
        <ClickAwayListener onClickAway={handleClose}>
          <Paper
            elevation={8}
            sx={{
              borderRadius: 2,
              width: "26rem",
              maxWidth: "calc(100vw - 1rem)",
              overflow: "hidden",
            }}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                px: 2,
                py: 1.25,
                bgcolor: "action.hover",
              }}
            >
              <Typography sx={{ fontWeight: 600 }}>Notifications</Typography>
              {unreadCount > 0 && (
                <Chip
                  label={`${unreadCount} new`}
                  size="small"
                  color="primary"
                  sx={{
                    height: "1.25rem",
                    fontSize: "0.7rem",
                    fontWeight: 600,
                  }}
                />
              )}
              <Box sx={{ flexGrow: 1 }} />
              {count > 0 && (
                <>
                  <Tooltip
                    title={
                      unreadCount > 0 ? "Mark all read" : "Mark all unread"
                    }
                  >
                    <IconButton
                      size="small"
                      onClick={unreadCount > 0 ? markAllRead : markAllUnread}
                      data-testid={
                        unreadCount > 0
                          ? "markAllReadButton"
                          : "markAllUnreadButton"
                      }
                    >
                      {unreadCount > 0 ? (
                        <DoneAllIcon fontSize="small" />
                      ) : (
                        <RemoveDoneIcon fontSize="small" />
                      )}
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete all">
                    <IconButton
                      size="small"
                      onClick={deleteAllNotifications}
                      data-testid="deleteAllNotificationsButton"
                    >
                      <DeleteSweepIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </>
              )}
            </Box>
            <Divider />
            {count === 0 ? (
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 1,
                  px: 3,
                  py: 4,
                }}
              >
                <NotificationsOffIcon sx={{ color: "text.disabled" }} />
                <Typography variant="body2" color="text.secondary">
                  No notifications
                </Typography>
              </Box>
            ) : (
              <List
                disablePadding
                sx={{ maxHeight: "60vh", overflowY: "auto" }}
              >
                {notifications?.map((notification, index) => (
                  <ListItem
                    key={notification.id}
                    disablePadding
                    divider={index < count - 1}
                    sx={{
                      ...(!notification.viewed && {
                        bgcolor: (theme) =>
                          alpha(
                            theme.palette.primary.main,
                            theme.palette.mode === "dark" ? 0.14 : 0.07,
                          ),
                        "& > .MuiListItemButton-root:hover": {
                          bgcolor: (theme) =>
                            alpha(
                              theme.palette.primary.main,
                              theme.palette.mode === "dark" ? 0.22 : 0.14,
                            ),
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
                        <Tooltip
                          title={
                            notification.viewed ? "Mark unread" : "Mark read"
                          }
                        >
                          <IconButton
                            size="small"
                            data-testid={`${
                              notification.viewed
                                ? "markUnreadButton"
                                : "markReadButton"
                            }${notification.id}`}
                            onClick={() =>
                              notification.viewed
                                ? markUnread(notification.id)
                                : markRead(notification.id)
                            }
                          >
                            {notification.viewed ? (
                              <RemoveDoneIcon fontSize="small" />
                            ) : (
                              <DoneIcon fontSize="small" />
                            )}
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <IconButton
                            size="small"
                            data-testid={`deleteNotificationButton${notification.id}`}
                            onClick={() => deleteNotification(notification.id)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    }
                  >
                    <ListItemButton
                      component="a"
                      href={notification.url || undefined}
                      onClick={() => markRead(notification.id)}
                      data-testid={`notification${notification.id}`}
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
                            notification.viewed
                              ? theme.palette.action.hover
                              : alpha(theme.palette.primary.main, 0.2),
                          color: notification.viewed
                            ? "text.secondary"
                            : "primary.main",
                          "& svg": { fontSize: "1.2rem" },
                        }}
                      >
                        {typeIcon(notification)}
                      </Box>
                      <Box sx={{ minWidth: 0 }}>
                        <Box
                          sx={{
                            fontSize: "0.875rem",
                            lineHeight: 1.45,
                            overflowWrap: "anywhere",
                            fontWeight: notification.viewed ? 400 : 600,
                            "& p": { m: 0 },
                            "& em": { fontStyle: "normal", fontWeight: 600 },
                          }}
                        >
                          <ReactMarkdown>{notification.text}</ReactMarkdown>
                        </Box>
                        {notification.created_at && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ display: "block", mt: 0.25 }}
                          >
                            {dayjs().to(
                              dayjs.utc(`${notification.created_at}Z`),
                            )}
                          </Typography>
                        )}
                      </Box>
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </ClickAwayListener>
      </Popper>
    </>
  );
};

export default Notifications;
