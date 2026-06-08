import React from "react";

import Badge from "@mui/material/Badge";
import MUINotificationsIcon from "@mui/icons-material/NotificationsOutlined";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import { makeStyles } from "tss-react/mui";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Divider from "@mui/material/Divider";
import ReactMarkdown from "react-markdown";
import Button from "./Button";

import {
  useGetNotificationsQuery,
  useUpdateNotificationMutation,
  useUpdateAllNotificationsMutation,
  useDeleteNotificationMutation,
  useDeleteAllNotificationsMutation,
} from "../ducks/userNotifications";

const useStyles = makeStyles()((theme) => ({
  root: {
    width: "100%",
    maxWidth: 360,
    backgroundColor: theme.palette.background.paper,
  },
  readMessage: {
    fontWeight: "normal",
  },
  unreadMessage: {
    fontWeight: "bold",
  },
  centered: {
    display: "flex",
    justifyContent: "center",
  },
}));

const Notifications = () => {
  const { classes } = useStyles();
  const { data: notifications } = useGetNotificationsQuery();
  const [updateNotification] = useUpdateNotificationMutation();
  const [updateAllNotifications] = useUpdateAllNotificationsMutation();
  const [deleteNotificationMutation] = useDeleteNotificationMutation();
  const [deleteAllNotificationsMutation] = useDeleteAllNotificationsMutation();

  const unreadCount = notifications
    ? notifications.filter((n) => !n.viewed).length
    : 0;

  // Popover logic
  const [anchorEl, setAnchorEl] = React.useState<any>(null);
  const handleClickOpen = (event: any) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const open = Boolean(anchorEl);

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
      <IconButton
        onClick={handleClickOpen}
        data-testid="notificationsButton"
        size="large"
        style={{ padding: 0, margin: 0 }}
      >
        <Badge
          badgeContent={unreadCount}
          overlap="circular"
          color={unreadCount > 0 ? "secondary" : "primary"}
          data-testid="notificationsBadge"
        >
          <MUINotificationsIcon fontSize="large" color="primary" />
        </Badge>
      </IconButton>
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "center",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "center",
        }}
        disableScrollLock
      >
        <div className={classes.root}>
          <List className={classes.root}>
            {notifications &&
              notifications.map((notification) => (
                <div key={notification.id}>
                  <ListItem
                    {...({ button: !!notification.url } as any)}
                    component={notification.url ? "a" : "li"}
                    href={notification.url ? notification.url : "#"}
                    className={
                      notification.viewed
                        ? classes.readMessage
                        : classes.unreadMessage
                    }
                    onClick={() => {
                      markRead(notification.id);
                    }}
                    data-testid={`notification${notification.id}`}
                  >
                    <ReactMarkdown>{notification.text}</ReactMarkdown>
                  </ListItem>
                  <ListItem className={classes.centered}>
                    {!notification.viewed && (
                      <Button
                        data-testid={`markReadButton${notification.id}`}
                        size="small"
                        onClick={() => {
                          markRead(notification.id);
                        }}
                      >
                        Mark read
                      </Button>
                    )}
                    {notification.viewed && (
                      <Button
                        data-testid={`markUnreadButton${notification.id}`}
                        size="small"
                        onClick={() => {
                          markUnread(notification.id);
                        }}
                      >
                        Mark unread
                      </Button>
                    )}
                    |
                    <Button
                      data-testid={`deleteNotificationButton${notification.id}`}
                      size="small"
                      onClick={() => {
                        deleteNotification(notification.id);
                      }}
                    >
                      Delete
                    </Button>
                  </ListItem>
                  <Divider />
                </div>
              ))}
            {notifications && notifications.length > 0 && (
              <ListItem className={classes.centered}>
                {unreadCount > 0 && (
                  <Button onClick={markAllRead} data-testid="markAllReadButton">
                    Mark all read
                  </Button>
                )}
                {unreadCount === 0 && (
                  <Button
                    onClick={markAllUnread}
                    data-testid="markAllUnreadButton"
                  >
                    Mark all unread
                  </Button>
                )}
                |
                <Button
                  onClick={deleteAllNotifications}
                  data-testid="deleteAllNotificationsButton"
                >
                  Delete all
                </Button>
              </ListItem>
            )}
            {(!notifications || notifications.length === 0) && (
              <ListItem className={classes.centered}>
                <em>No notifications</em>
              </ListItem>
            )}
          </List>
        </div>
      </Popover>
    </>
  );
};

export default Notifications;
