import { useState } from "react";

import Badge from "@mui/material/Badge";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";
import { alpha, Theme } from "@mui/material/styles";

import NotificationsIcon from "@mui/icons-material/NotificationsOutlined";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import RemoveDoneIcon from "@mui/icons-material/RemoveDone";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweepOutlined";

import HeaderPanel from "./HeaderPanel";
import NotificationList from "./NotificationList";
import AlertList, { Severity, useAlerts } from "./AlertList";
import {
  useGetNotificationsQuery,
  useUpdateNotificationMutation,
  useUpdateAllNotificationsMutation,
  useDeleteNotificationMutation,
  useDeleteAllNotificationsMutation,
} from "../ducks/userNotifications";

const TABS_SX = {
  minHeight: 0,
  "& .MuiTab-root": {
    minHeight: 0,
    minWidth: 0,
    gap: 0.75,
    px: 2,
    py: 1.5,
    fontSize: "0.875rem",
    fontWeight: 600,
    textTransform: "none",
  },
};

const countSx = (color: "primary" | Severity) => ({
  height: "1.125rem",
  fontSize: "0.68rem",
  fontWeight: 700,
  bgcolor: (theme: Theme) => alpha(theme.palette[color].main, 0.18),
  color: `${color}.main`,
  "& .MuiChip-label": { px: 0.75 },
});

const Notifications = () => {
  const { data } = useGetNotificationsQuery();
  const [updateNotification] = useUpdateNotificationMutation();
  const [updateAllNotifications] = useUpdateAllNotificationsMutation();
  const [deleteNotification] = useDeleteNotificationMutation();
  const [deleteAllNotifications] = useDeleteAllNotificationsMutation();
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [tab, setTab] = useState<"notifications" | "alerts">("notifications");

  const open = Boolean(anchorEl);
  const showingAlerts = tab === "alerts";
  const alerts = useAlerts(open && showingAlerts);

  const notifications = data || [];
  const unreadCount = notifications.filter((n) => !n.viewed).length;
  const hasUnread = unreadCount > 0;

  const close = () => setAnchorEl(null);
  const setViewed = (notificationID: number, viewed: boolean) =>
    updateNotification({ notificationID, data: { viewed } });

  return (
    <>
      <Tooltip title={open ? "" : "Notifications"}>
        <IconButton
          onClick={(event) => setAnchorEl(open ? null : event.currentTarget)}
          data-testid="notificationsButton"
          size="large"
          style={{ padding: 0, margin: 0 }}
        >
          <Badge
            badgeContent={unreadCount + alerts.unseenCount}
            overlap="circular"
            color="error"
            data-testid="notificationsBadge"
          >
            <NotificationsIcon fontSize="large" color="primary" />
          </Badge>
        </IconButton>
      </Tooltip>
      <HeaderPanel
        anchorEl={anchorEl}
        onClose={close}
        header={
          <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={TABS_SX}>
            <Tab
              value="notifications"
              label="Notifications"
              data-testid="notificationsTab"
              iconPosition="end"
              icon={
                hasUnread ? (
                  <Chip
                    label={unreadCount}
                    size="small"
                    sx={countSx("primary")}
                  />
                ) : undefined
              }
            />
            <Tab
              value="alerts"
              label="Alerts"
              data-testid="alertsTab"
              iconPosition="end"
              icon={
                alerts.unseenCount > 0 ? (
                  <Chip
                    label={alerts.unseenCount}
                    size="small"
                    sx={countSx(alerts.worstSeverity)}
                  />
                ) : undefined
              }
            />
          </Tabs>
        }
        actions={
          showingAlerts
            ? alerts.count > 0 && (
                <Tooltip title="Delete all">
                  <IconButton
                    size="small"
                    onClick={alerts.deleteAll}
                    data-testid="deleteAllAlertsButton"
                  >
                    <DeleteSweepIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )
            : notifications.length > 0 && (
                <>
                  <Tooltip
                    title={hasUnread ? "Mark all read" : "Mark all unread"}
                  >
                    <IconButton
                      size="small"
                      onClick={() =>
                        updateAllNotifications({ viewed: hasUnread })
                      }
                      data-testid={
                        hasUnread ? "markAllReadButton" : "markAllUnreadButton"
                      }
                    >
                      {hasUnread ? (
                        <DoneAllIcon fontSize="small" />
                      ) : (
                        <RemoveDoneIcon fontSize="small" />
                      )}
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete all">
                    <IconButton
                      size="small"
                      onClick={() => {
                        deleteAllNotifications();
                        close();
                      }}
                      data-testid="deleteAllNotificationsButton"
                    >
                      <DeleteSweepIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </>
              )
        }
      >
        {showingAlerts ? (
          <AlertList groups={alerts.groups} onDelete={alerts.delete} />
        ) : (
          <NotificationList
            notifications={notifications}
            onSetViewed={setViewed}
            onDelete={deleteNotification}
          />
        )}
      </HeaderPanel>
    </>
  );
};

export default Notifications;
