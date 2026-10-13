import { Fragment, ReactNode, useState } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListSubheader from "@mui/material/ListSubheader";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha, Theme } from "@mui/material/styles";

import NotificationsIcon from "@mui/icons-material/NotificationsOutlined";
import NotificationsOffIcon from "@mui/icons-material/NotificationsOffOutlined";
import DoneIcon from "@mui/icons-material/Done";
import RemoveDoneIcon from "@mui/icons-material/RemoveDone";
import DeleteIcon from "@mui/icons-material/DeleteOutlineOutlined";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
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
import RocketLaunchIcon from "@mui/icons-material/RocketLaunchOutlined";
import FeedbackIcon from "@mui/icons-material/FeedbackOutlined";
import ForumIcon from "@mui/icons-material/ForumOutlined";

import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import ReactMarkdown from "react-markdown";

import { Link } from "react-router-dom";

import { PanelEmptyState } from "./HeaderPanel";
import { UserNotification } from "../ducks/userNotifications";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const unreadTint = (theme: Theme, light: number, dark: number) =>
  alpha(
    theme.palette.primary.main,
    theme.palette.mode === "dark" ? dark : light,
  );

interface Category {
  label: string;
  icon: ReactNode;
}

const category = (
  notificationType?: string | null,
  url?: string | null,
): Category => {
  const type = (notificationType || "").toLowerCase();
  if (type.includes("mention") || type.includes("comment"))
    return { label: "Comments", icon: <ChatBubbleIcon /> };
  if (type === "direct_messages" || type === "group_discussions")
    return { label: "Discussions", icon: <ForumIcon /> };
  if (type.includes("reminder"))
    return { label: "Reminders", icon: <AlarmIcon /> };
  if (type.includes("report") || type.includes("summary"))
    return { label: "Reports", icon: <ArticleIcon /> };
  if (type.includes("classification"))
    return { label: "Classifications", icon: <CategoryIcon /> };
  if (type.includes("spectrum") || type.includes("photometry"))
    return { label: "Spectra & photometry", icon: <ShowChartIcon /> };
  if (type.includes("gcn")) return { label: "GCN events", icon: <FlareIcon /> };
  if (type.includes("group") || type.includes("user"))
    return { label: "Groups", icon: <GroupIcon /> };
  if (type.includes("shift")) return { label: "Shifts", icon: <EventIcon /> };
  if (type.includes("analysis"))
    return { label: "Analyses", icon: <ScienceIcon /> };
  if (type.includes("facility") || type.includes("followup"))
    return { label: "Follow-up", icon: <SendIcon /> };
  if (type.includes("observation"))
    return { label: "Observations", icon: <VisibilityIcon /> };
  if (type.includes("api"))
    return { label: "Recurring APIs", icon: <AutorenewIcon /> };
  if (type.includes("deployment"))
    return { label: "Deployments", icon: <RocketLaunchIcon /> };
  if (type.includes("feedback"))
    return { label: "Feedback", icon: <FeedbackIcon /> };

  // many notifications have no type at all, so fall back on where they point to
  const target = url || "";
  if (target.startsWith("/shift"))
    return { label: "Shifts", icon: <EventIcon /> };
  if (target.startsWith("/group"))
    return { label: "Groups", icon: <GroupIcon /> };
  if (target.startsWith("/gcn_events"))
    return { label: "GCN events", icon: <FlareIcon /> };
  if (target.startsWith("/data_access"))
    return { label: "Data access", icon: <LockIcon /> };
  if (target.startsWith("/source"))
    return { label: "Sources", icon: <SourceIcon /> };
  return { label: "Other", icon: <NotificationsIcon /> };
};

// like iOS, a stack sits where its newest notification would
const stackByCategory = (items: UserNotification[]) => {
  const stacks = new Map<string, Category & { items: UserNotification[] }>();
  items.forEach((n) => {
    const cat = category(n.notification_type, n.url);
    if (!stacks.has(cat.label)) stacks.set(cat.label, { ...cat, items: [] });
    stacks.get(cat.label)!.items.push(n);
  });
  return [...stacks.values()];
};

const ROW_SX = {
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
};

const unreadSx = {
  bgcolor: (theme: Theme) => unreadTint(theme, 0.07, 0.14),
  "& > .MuiListItemButton-root:hover": {
    bgcolor: (theme: Theme) => unreadTint(theme, 0.14, 0.22),
  },
};

interface RowActionsProps {
  viewed: boolean;
  onToggleViewed: () => void;
  onDelete: () => void;
  testIdSuffix: string;
  plural?: boolean;
}

const RowActions = ({
  viewed,
  onToggleViewed,
  onDelete,
  testIdSuffix,
  plural = false,
}: RowActionsProps) => (
  <Box sx={{ display: "flex" }}>
    <Tooltip
      title={`${viewed ? "Mark unread" : "Mark read"}${plural ? " (all)" : ""}`}
    >
      <IconButton
        size="small"
        data-testid={`${
          viewed ? "markUnreadButton" : "markReadButton"
        }${testIdSuffix}`}
        onClick={onToggleViewed}
      >
        {viewed ? (
          <RemoveDoneIcon fontSize="small" />
        ) : (
          <DoneIcon fontSize="small" />
        )}
      </IconButton>
    </Tooltip>
    <Tooltip title={plural ? "Delete all" : "Delete"}>
      <IconButton
        size="small"
        data-testid={`deleteNotificationButton${testIdSuffix}`}
        onClick={onDelete}
      >
        <DeleteIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  </Box>
);

interface NotificationRowProps {
  notification: UserNotification;
  icon: ReactNode;
  divider: boolean;
  actions: ReactNode;
  onClick: () => void;
  // set on a collapsed stack: the row expands instead of navigating
  moreCount?: number;
}

const NotificationRow = ({
  notification: { id, text, url, viewed, created_at },
  icon,
  divider,
  actions,
  onClick,
  moreCount = 0,
}: NotificationRowProps) => {
  const navigates = Boolean(url) && moreCount === 0;
  return (
    <ListItem
      disablePadding
      divider={divider}
      sx={{ ...(!viewed && unreadSx), ...ROW_SX }}
      secondaryAction={actions}
    >
      <ListItemButton
        {...({
          component: navigates ? Link : "div",
          to: navigates ? url : undefined,
        } as any)}
        onClick={onClick}
        data-testid={
          moreCount > 0 ? `notificationStack${id}` : `notification${id}`
        }
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
          {icon}
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
          {(created_at || moreCount > 0) && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", mt: 0.25 }}
            >
              {created_at && dayjs().to(dayjs.utc(`${created_at}Z`))}
              {created_at && moreCount > 0 && " · "}
              {moreCount > 0 && `${moreCount} more`}
            </Typography>
          )}
        </Box>
      </ListItemButton>
    </ListItem>
  );
};

const STACK_RADIUS = 8;

// the edges of the cards hidden behind a collapsed stack
const StackEdges = ({ count, viewed }: { count: number; viewed: boolean }) => (
  <Box>
    {[1, 2].slice(0, count).map((depth) => (
      <Box
        key={depth}
        sx={{
          height: 5,
          mx: depth * 1.5,
          borderBottomLeftRadius: STACK_RADIUS,
          borderBottomRightRadius: STACK_RADIUS,
          border: 1,
          borderTop: 0,
          borderColor: "divider",
          bgcolor: (theme) =>
            viewed
              ? theme.palette.action.hover
              : unreadTint(theme, 0.07 / depth, 0.14 / depth),
        }}
      />
    ))}
  </Box>
);

interface NotificationListProps {
  notifications: UserNotification[];
  onOpen: (notificationID: number, url?: string | null) => void;
  onSetViewed: (notificationID: number, viewed: boolean) => void;
  onDelete: (notificationID: number) => void;
}

const NotificationList = ({
  notifications,
  onOpen,
  onSetViewed,
  onDelete,
}: NotificationListProps) => {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const toggleExpanded = (key: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (!next.delete(key)) next.add(key);
      return next;
    });

  if (notifications.length === 0)
    return (
      <PanelEmptyState
        icon={<NotificationsOffIcon />}
        text="No notifications"
      />
    );

  // unread on top, read below; each keeps the API's newest-first order
  const sections = [
    { title: "Unread", items: notifications.filter((n) => !n.viewed) },
    { title: "Read", items: notifications.filter((n) => n.viewed) },
  ].filter(({ items }) => items.length > 0);

  const singleActions = ({ id, viewed }: UserNotification) => (
    <RowActions
      viewed={viewed}
      onToggleViewed={() => onSetViewed(id, !viewed)}
      onDelete={() => onDelete(id)}
      testIdSuffix={`${id}`}
    />
  );

  return (
    <List disablePadding>
      {sections.map(({ title, items }) => {
        const stacks = stackByCategory(items);
        return (
          <Fragment key={title}>
            <ListSubheader
              disableSticky
              data-testid={`notificationsSection${title}`}
              sx={{
                lineHeight: 2.25,
                fontSize: "0.75rem",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                color: "text.secondary",
                bgcolor: "transparent",
              }}
            >
              {title}
            </ListSubheader>
            {stacks.map(({ label, icon, items: stackItems }, stackIndex) => {
              const isLastStack = stackIndex === stacks.length - 1;
              const newest = stackItems[0]!; // stacks are never empty
              const key = `${title}:${label}`;

              if (stackItems.length === 1)
                return (
                  <NotificationRow
                    key={newest.id}
                    notification={newest}
                    icon={icon}
                    divider={!isLastStack}
                    actions={singleActions(newest)}
                    onClick={() => onOpen(newest.id, newest.url)}
                  />
                );

              const isOpen = expanded.has(key);
              return (
                <Box
                  key={key}
                  sx={{
                    p: 1,
                    borderBottom: isLastStack ? 0 : 1,
                    borderColor: "divider",
                  }}
                >
                  <Box
                    sx={{
                      border: 1,
                      borderColor: "divider",
                      borderRadius: `${STACK_RADIUS}px`,
                      overflow: "hidden",
                    }}
                  >
                    <Collapse in={isOpen} timeout={250} unmountOnExit>
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          pl: 2,
                          pr: 1,
                          py: 0.5,
                          borderBottom: 1,
                          borderColor: "divider",
                        }}
                      >
                        <Typography
                          variant="subtitle2"
                          sx={{ fontWeight: 600 }}
                        >
                          {label}
                        </Typography>
                        <Button
                          size="small"
                          endIcon={<ExpandLessIcon />}
                          onClick={() => toggleExpanded(key)}
                          data-testid={`collapseStack${newest.id}`}
                          sx={{ textTransform: "none" }}
                        >
                          Show less
                        </Button>
                      </Box>
                    </Collapse>
                    <NotificationRow
                      notification={newest}
                      icon={icon}
                      divider={isOpen}
                      moreCount={isOpen ? 0 : stackItems.length - 1}
                      onClick={() =>
                        isOpen
                          ? onOpen(newest.id, newest.url)
                          : toggleExpanded(key)
                      }
                      actions={
                        isOpen ? (
                          singleActions(newest)
                        ) : (
                          <RowActions
                            plural
                            viewed={newest.viewed}
                            onToggleViewed={() =>
                              stackItems.forEach((n) =>
                                onSetViewed(n.id, !newest.viewed),
                              )
                            }
                            onDelete={() =>
                              stackItems.forEach((n) => onDelete(n.id))
                            }
                            testIdSuffix={`Stack${newest.id}`}
                          />
                        )
                      }
                    />
                    <Collapse in={isOpen} timeout={250} unmountOnExit>
                      {stackItems.slice(1).map((n, index) => (
                        <Box
                          key={n.id}
                          sx={{
                            // cards slide out from behind the front one, one after another
                            "@keyframes notification-stack-in": {
                              from: {
                                opacity: 0,
                                transform: "translateY(-12px)",
                              },
                              to: { opacity: 1, transform: "none" },
                            },
                            animation: `notification-stack-in 220ms ease-out ${
                              index * 40
                            }ms both`,
                          }}
                        >
                          <NotificationRow
                            notification={n}
                            icon={icon}
                            divider={index < stackItems.length - 2}
                            actions={singleActions(n)}
                            onClick={() => onOpen(n.id, n.url)}
                          />
                        </Box>
                      ))}
                    </Collapse>
                  </Box>
                  <Collapse in={!isOpen} timeout={250}>
                    <StackEdges
                      count={stackItems.length - 1}
                      viewed={newest.viewed}
                    />
                  </Collapse>
                </Box>
              );
            })}
          </Fragment>
        );
      })}
    </List>
  );
};

export default NotificationList;
