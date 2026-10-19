import { ReactNode, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import AddCommentIcon from "@mui/icons-material/AddCommentOutlined";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import GroupAddIcon from "@mui/icons-material/GroupAddOutlined";
import NotificationsIcon from "@mui/icons-material/NotificationsOutlined";
import NotificationsOffIcon from "@mui/icons-material/NotificationsOffOutlined";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SearchIcon from "@mui/icons-material/Search";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";

import Button from "../Button";
import CommentThreadView from "../comment/CommentThread";
import CommentThreadAvatar, { RESOURCES } from "./CommentThreadAvatar";
import DiscussionAvatar from "./DiscussionAvatar";
import DiscussionThread from "./DiscussionThread";
import DiscussionNotifications from "./DiscussionNotifications";
import NewDiscussion, { NewKind } from "./NewDiscussion";
import { discussionTitle, shortTime } from "./names";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  CommentThread,
  Discussion,
  DiscussionUser,
  useGetCommentThreadsQuery,
  useGetDiscussionsQuery,
} from "../../ducks/discussions";

type Filter = "all" | "direct" | "groups" | "comments";

const FILTERS: Record<Filter, string> = {
  all: "All",
  direct: "Direct",
  groups: "Groups",
  comments: "Comments",
};

interface Entry {
  key: string;
  time: string;
  title: string;
  snippet: string;
  unread: number;
  muted: boolean;
  discussion?: Discussion;
  thread?: CommentThread;
}

const threadKey = (thread: CommentThread) =>
  `${thread.resource_type}:${thread.resource_id}:${thread.channel ?? ""}`;

const snippetOf = (author: DiscussionUser, text: string, myId?: number) =>
  `${author.id === myId ? "You" : author.first_name || author.username}: ${text.replace(/[*~`]/g, "").replace(/\s+/g, " ")}`;

const ActionTile = ({
  icon,
  title,
  text,
  onClick,
}: {
  icon: ReactNode;
  title: string;
  text: string;
  onClick: () => void;
}) => (
  <Box
    role="button"
    tabIndex={0}
    onClick={onClick}
    onKeyDown={(event) => {
      if (event.key === "Enter") onClick();
    }}
    sx={{
      width: "15rem",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      textAlign: "center",
      gap: 1,
      padding: 2.5,
      borderRadius: 3,
      border: 1,
      borderColor: "divider",
      backgroundColor: "background.paper",
      cursor: "pointer",
      transition: "border-color 120ms, box-shadow 120ms",
      "&:hover, &:focus-visible": {
        borderColor: "primary.main",
        boxShadow: 2,
        outline: "none",
      },
    }}
  >
    <Avatar sx={{ width: 48, height: 48, bgcolor: "primary.main" }}>
      {icon}
    </Avatar>
    <Typography sx={{ fontWeight: 600 }}>{title}</Typography>
    <Typography variant="body2" color="textSecondary">
      {text}
    </Typography>
  </Box>
);

const CommentThreadPane = ({
  thread,
  onBack,
}: {
  thread: CommentThread;
  onBack?: (() => void) | undefined;
}) => {
  const resourceId = thread.resource_id;
  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          padding: "0.75rem 1rem",
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        {onBack && (
          <IconButton size="small" onClick={onBack}>
            <ArrowBackIcon fontSize="small" />
          </IconButton>
        )}
        <CommentThreadAvatar type={thread.resource_type} size={40} />
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography variant="h6" noWrap sx={{ lineHeight: 1.3 }}>
            {thread.label}
          </Typography>
          <Typography variant="body2" color="textSecondary" noWrap>
            {RESOURCES[thread.resource_type].name} comments
            {thread.channel && `, conversation "${thread.channel}"`}
          </Typography>
        </Box>
        <Button
          secondary
          size="small"
          component={Link}
          to={thread.url}
          endIcon={<OpenInNewIcon fontSize="small" />}
        >
          Open
        </Button>
      </Box>
      <Box sx={{ flexGrow: 1, minHeight: 0 }}>
        {thread.resource_type === "sources" && (
          <CommentThreadView
            key={threadKey(thread)}
            objID={resourceId}
            channel={thread.channel ?? undefined}
          />
        )}
        {thread.resource_type === "gcn_event" && (
          <CommentThreadView
            resourceType="gcn_event"
            gcnEventID={Number(resourceId)}
            gcnEventDateobs={thread.dateobs ?? null}
          />
        )}
        {thread.resource_type === "earthquake" && (
          <CommentThreadView
            resourceType="earthquake"
            earthquakeID={resourceId}
            earthquakeEventID={thread.event_id ?? null}
          />
        )}
        {thread.resource_type === "shift" && (
          <CommentThreadView
            resourceType="shift"
            shiftID={Number(resourceId)}
          />
        )}
      </Box>
    </Box>
  );
};

const Discussions = () => {
  const [params, setParams] = useSearchParams();
  const narrow = useMediaQuery((theme: any) => theme.breakpoints.down("md"));
  const myId = useGetProfileQuery().data?.id;
  const { data: discussions } = useGetDiscussionsQuery();
  const { data: threads } = useGetCommentThreadsQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const discussionId = params.get("id") ? Number(params.get("id")) : null;
  const selectedThread = params.get("thread");
  const creating = params.get("new") as NewKind | null;
  const settings = params.get("settings") === "notifications";

  const entries = useMemo(() => {
    const fromDiscussions: Entry[] = (discussions ?? [])
      .filter(
        (discussion) =>
          !discussion.is_direct ||
          discussion.last_message ||
          discussion.creator_id === myId ||
          discussion.id === discussionId,
      )
      .map((discussion) => ({
        key: `discussion:${discussion.id}`,
        time: discussion.last_message?.created_at ?? discussion.created_at,
        title: discussionTitle(discussion, myId),
        snippet: discussion.last_message
          ? snippetOf(
              discussion.last_message.author,
              discussion.last_message.text,
              myId,
            )
          : "No message yet",
        unread: discussion.unread,
        muted: discussion.muted,
        discussion,
      }));
    const fromThreads: Entry[] = (threads ?? []).map((thread) => ({
      key: threadKey(thread),
      time: thread.last_comment.created_at,
      title: thread.channel
        ? `${thread.label} · ${thread.channel}`
        : thread.label,
      snippet: snippetOf(
        thread.last_comment.author,
        thread.last_comment.text,
        myId,
      ),
      unread: 0,
      muted: false,
      thread,
    }));
    const query = search.trim().toLowerCase();
    return [
      ...fromDiscussions.filter(
        ({ discussion }) =>
          filter === "all" ||
          (filter === "direct" && discussion?.is_direct) ||
          (filter === "groups" && !discussion?.is_direct),
      ),
      ...(filter === "all" || filter === "comments" ? fromThreads : []),
    ]
      .filter(
        (entry) =>
          !query ||
          entry.title.toLowerCase().includes(query) ||
          entry.snippet.toLowerCase().includes(query),
      )
      .sort((a, b) => (a.time < b.time ? 1 : -1));
  }, [discussions, threads, filter, search, myId, discussionId]);

  const discussion = discussions?.find((d) => d.id === discussionId);
  const thread = threads?.find((t) => threadKey(t) === selectedThread);
  const showingThread = !discussionId && thread;
  const selected = discussion
    ? `discussion:${discussion.id}`
    : showingThread
      ? selectedThread
      : null;

  const open = (entry: Entry) => {
    setParams(
      entry.discussion
        ? { id: String(entry.discussion.id) }
        : { thread: entry.key },
    );
  };

  const back = () => {
    setParams({});
  };

  const create = (kind: NewKind) => setParams({ new: kind });

  const hasSelection = Boolean(
    creating || settings || discussion || showingThread,
  );
  const loading = !discussions || !threads;

  const list = (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        minHeight: 0,
        height: "100%",
        width: narrow ? "100%" : "24rem",
        flexShrink: 0,
        borderRight: narrow ? 0 : 1,
        borderColor: "divider",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          padding: "0.75rem 0.75rem 0.25rem 1rem",
        }}
      >
        <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600 }}>
          Discussions
        </Typography>
        <Tooltip title="New direct message">
          <IconButton
            color="primary"
            onClick={() => create("direct")}
            data-testid="newDirectMessageButton"
          >
            <AddCommentIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="New group conversation">
          <IconButton
            color="primary"
            onClick={() => create("group")}
            data-testid="newGroupConversationButton"
          >
            <GroupAddIcon />
          </IconButton>
        </Tooltip>
        <Tooltip title="Notification settings">
          <IconButton
            color={settings ? "primary" : "default"}
            onClick={() => setParams({ settings: "notifications" })}
            data-testid="discussionNotificationsButton"
          >
            <NotificationsIcon />
          </IconButton>
        </Tooltip>
      </Box>
      <Box sx={{ padding: "0 0.75rem" }}>
        <TextField
          size="small"
          fullWidth
          placeholder="Search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
        />
      </Box>
      <Tabs
        value={filter}
        onChange={(_, value) => setFilter(value)}
        variant="fullWidth"
        sx={{ borderBottom: 1, borderColor: "divider", minHeight: 40 }}
      >
        {Object.entries(FILTERS).map(([value, label]) => (
          <Tab
            key={value}
            value={value}
            label={label}
            sx={{ minHeight: 40, minWidth: 0, paddingX: 1 }}
          />
        ))}
      </Tabs>
      <List sx={{ flexGrow: 1, minHeight: 0, overflowY: "auto", padding: 0.5 }}>
        {!loading && entries.length === 0 && (
          <Typography
            variant="body2"
            color="textSecondary"
            sx={{ textAlign: "center", padding: 3 }}
          >
            {search
              ? "Nothing matches your search."
              : "Nothing here yet. Start a conversation from the buttons above, or from someone's profile."}
          </Typography>
        )}
        {entries.map((entry) => (
          <ListItemButton
            key={entry.key}
            selected={entry.key === selected}
            onClick={() => open(entry)}
            sx={{ borderRadius: 2, gap: 1.5, alignItems: "center" }}
          >
            {entry.discussion ? (
              <DiscussionAvatar
                discussion={entry.discussion}
                myId={myId}
                size={40}
              />
            ) : (
              entry.thread && (
                <CommentThreadAvatar
                  type={entry.thread.resource_type}
                  size={40}
                />
              )
            )}
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <Box sx={{ display: "flex", alignItems: "baseline", gap: 1 }}>
                <Typography
                  noWrap
                  sx={{
                    flexGrow: 1,
                    fontWeight: entry.unread && !entry.muted ? 700 : 500,
                  }}
                >
                  {entry.title}
                </Typography>
                <Typography
                  variant="caption"
                  color="textSecondary"
                  sx={{ flexShrink: 0 }}
                >
                  {shortTime(entry.time)}
                </Typography>
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <Typography
                  variant="body2"
                  color="textSecondary"
                  noWrap
                  sx={{ flexGrow: 1 }}
                >
                  {entry.snippet}
                </Typography>
                {entry.muted && (
                  <NotificationsOffIcon
                    sx={{ fontSize: "1rem", color: "text.disabled" }}
                  />
                )}
                {entry.unread > 0 && (
                  <Chip
                    label={entry.unread}
                    size="small"
                    color={entry.muted ? "default" : "primary"}
                    sx={{ height: 18, minWidth: 18, fontSize: "0.7rem" }}
                  />
                )}
              </Box>
            </Box>
          </ListItemButton>
        ))}
      </List>
    </Box>
  );

  const pane = creating ? (
    <NewDiscussion
      key={creating}
      kind={creating}
      onOpen={(id) => setParams({ id: String(id) })}
      onBack={narrow ? back : undefined}
    />
  ) : settings ? (
    <DiscussionNotifications
      onOpen={(id) => setParams({ id: String(id) })}
      onBack={narrow ? back : undefined}
    />
  ) : discussion ? (
    <DiscussionThread
      key={discussion.id}
      discussion={discussion}
      onBack={narrow ? back : undefined}
    />
  ) : showingThread ? (
    <CommentThreadPane thread={thread} onBack={narrow ? back : undefined} />
  ) : (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        gap: 3,
        padding: 2,
      }}
    >
      <Typography color="textSecondary">
        {discussionId && discussions
          ? "This discussion does not exist or you are not part of it."
          : "Pick a conversation, or start a new one."}
      </Typography>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: 2,
        }}
      >
        <ActionTile
          icon={<AddCommentIcon />}
          title="Direct message"
          text="A private conversation with one person."
          onClick={() => create("direct")}
        />
        <ActionTile
          icon={<GroupAddIcon />}
          title="Group conversation"
          text="Several people, or everyone in one of your groups."
          onClick={() => create("group")}
        />
      </Box>
    </Box>
  );

  return (
    <Box
      sx={{
        display: "flex",
        height: "calc(100vh - 4rem)",
        margin: "-0.625rem",
        overflow: "hidden",
        backgroundColor: "background.paper",
      }}
    >
      {(!narrow || !hasSelection) && list}
      {(!narrow || hasSelection) && (
        <Box sx={{ flexGrow: 1, minWidth: 0, minHeight: 0 }}>{pane}</Box>
      )}
    </Box>
  );
};

export default Discussions;
