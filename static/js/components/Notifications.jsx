import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import Badge from "@mui/material/Badge";
import MUINotificationsIcon from "@mui/icons-material/NotificationsOutlined";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import makeStyles from "@mui/styles/makeStyles";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Divider from "@mui/material/Divider";
import ReactMarkdown from "react-markdown";
import Button from "./Button";

import * as userNotificationsActions from "../ducks/userNotifications";

const useStyles = makeStyles((theme) => ({
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
  const classes = useStyles();
  const dispatch = useDispatch();
  const notifications = useSelector((state) => state.userNotifications);

  const [unreadCount, setUnreadCount] = useState(
    notifications ? notifications.filter((n) => !n.viewed).length : 0,
  );

  useEffect(() => {
    if (notifications === null) {
      dispatch(userNotificationsActions.fetchNotifications());
    } else {
      setUnreadCount(notifications.filter((n) => !n.viewed).length);
    }
  }, [dispatch, notifications]);

  // Popover logic
  const [anchorEl, setAnchorEl] = React.useState(null);
  const handleClickOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const open = Boolean(anchorEl);

  const deleteAllNotifications = () => {
    dispatch(userNotificationsActions.deleteAllNotifications());
    handleClose();
  };

  const markAllRead = () => {
    dispatch(userNotificationsActions.updateAllNotifications({ viewed: true }));
  };

  const markAllUnread = () => {
    dispatch(
      userNotificationsActions.updateAllNotifications({ viewed: false }),
    );
  };

  const markRead = (notificationID) => {
    dispatch(
      userNotificationsActions.updateNotification({
        notificationID,
        data: { viewed: true },
      }),
    );
  };

  const markUnread = (notificationID) => {
    dispatch(
      userNotificationsActions.updateNotification({
        notificationID,
        data: { viewed: false },
      }),
    );
  };

  const deleteNotification = (notificationID) => {
    dispatch(userNotificationsActions.deleteNotification(notificationID));
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
                    button={!!notification.url}
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
