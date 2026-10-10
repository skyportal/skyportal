import {
  Fragment,
  KeyboardEvent,
  ReactNode,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import dayjs from "dayjs";

import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/DeleteOutlined";
import EditIcon from "@mui/icons-material/Edit";
import LogoutIcon from "@mui/icons-material/Logout";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActiveOutlined";
import NotificationsOffIcon from "@mui/icons-material/NotificationsOffOutlined";
import PeopleIcon from "@mui/icons-material/PeopleOutlined";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha, useTheme } from "@mui/material/styles";

import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import CommentForm from "../comment/CommentForm";
import {
  emojiSupport,
  highlightMentions,
  markdownLink,
} from "../comment/Comment";
import UserAvatar from "../user/UserAvatar";
import DiscussionAvatar from "./DiscussionAvatar";
import DiscussionMembersDialog from "./DiscussionMembersDialog";
import { discussionTitle, fromServer, otherMembers, userName } from "./names";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  Discussion,
  DiscussionMessage,
  useDeleteDiscussionMessageMutation,
  useDeleteDiscussionMutation,
  useEditDiscussionMessageMutation,
  useGetDiscussionMessagesInfiniteQuery,
  useRemoveDiscussionMemberMutation,
  useRenameDiscussionMutation,
  useSendDiscussionMessageMutation,
  useUpdateDiscussionMembershipMutation,
} from "../../ducks/discussions";

const GROUPING_MINUTES = 5;

const startsRun = (message: DiscussionMessage, previous?: DiscussionMessage) =>
  !previous ||
  previous.author.id !== message.author.id ||
  fromServer(message.created_at).diff(
    fromServer(previous.created_at),
    "minute",
  ) >= GROUPING_MINUTES;

const dayLabel = (time: string) => {
  const date = fromServer(time);
  if (date.isSame(dayjs(), "day")) return "Today";
  if (date.isSame(dayjs().subtract(1, "day"), "day")) return "Yesterday";
  return date.format("dddd, MMMM D, YYYY");
};

const edited = (message: DiscussionMessage) =>
  fromServer(message.modified).diff(fromServer(message.created_at), "second") >
  1;

interface DiscussionThreadProps {
  discussion: Discussion;
  onBack?: (() => void) | undefined;
}

const DiscussionThread = ({ discussion, onBack }: DiscussionThreadProps) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const myId = useGetProfileQuery().data?.id;
  const { data, isSuccess, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useGetDiscussionMessagesInfiniteQuery(discussion.id);
  const messages = useMemo(
    () =>
      [...(data?.pages ?? [])].reverse().flatMap((page) => page.messages ?? []),
    [data],
  );
  const [sendMessage] = useSendDiscussionMessageMutation();
  const [editMessage] = useEditDiscussionMessageMutation();
  const [deleteMessage] = useDeleteDiscussionMessageMutation();
  const [updateMembership] = useUpdateDiscussionMembershipMutation();
  const [renameDiscussion] = useRenameDiscussionMutation();
  const [deleteDiscussion] = useDeleteDiscussionMutation();
  const [removeMember] = useRemoveDiscussionMemberMutation();
  const [editing, setEditing] = useState<number | null>(null);
  const [renaming, setRenaming] = useState<string | null>(null);
  const [membersOpen, setMembersOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const listRef = useRef<HTMLDivElement | null>(null);
  const atBottom = useRef(true);
  const heightBelowTop = useRef<number | null>(null);

  const title = discussionTitle(discussion, myId);
  const isFree = !discussion.is_direct && !discussion.group;
  const isCreator = discussion.creator_id === myId;
  const other = discussion.is_direct
    ? otherMembers(discussion, myId)[0]
    : undefined;

  useEffect(() => {
    if (discussion.unread > 0) {
      updateMembership({ id: discussion.id, read: true });
    }
  }, [discussion.id, discussion.unread, updateMembership]);

  const oldestId = messages[0]?.id;
  const newest = messages[messages.length - 1];

  const loadOlder = () => {
    const list = listRef.current;
    if (!list || !hasNextPage || isFetchingNextPage) return;
    heightBelowTop.current = list.scrollHeight - list.scrollTop;
    fetchNextPage();
  };

  const onScroll = () => {
    const list = listRef.current;
    if (!list) return;
    atBottom.current =
      list.scrollHeight - list.scrollTop - list.clientHeight < 80;
    if (list.scrollTop < 100) loadOlder();
  };

  useLayoutEffect(() => {
    const list = listRef.current;
    if (!list || heightBelowTop.current === null) return;
    list.scrollTop = list.scrollHeight - heightBelowTop.current;
    heightBelowTop.current = null;
  }, [oldestId]);

  useLayoutEffect(() => {
    const list = listRef.current;
    if (list && (atBottom.current || newest?.author.id === myId)) {
      list.scrollTop = list.scrollHeight;
      atBottom.current = true;
    }
  }, [newest?.id]);

  useEffect(() => {
    const list = listRef.current;
    if (list && list.scrollHeight <= list.clientHeight) loadOlder();
  }, [messages.length, hasNextPage]);

  const commitRename = () => {
    const name = renaming?.trim();
    setRenaming(null);
    if (name && name !== discussion.name) {
      renameDiscussion({ id: discussion.id, name });
    }
  };

  const onRenameKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter") commitRename();
    if (event.key === "Escape") setRenaming(null);
  };

  const leave = () =>
    removeMember({ id: discussion.id, userId: myId! })
      .unwrap()
      .then(() => navigate("/discussions"))
      .catch(() => {});

  const members = (
    <Tooltip title="See the members">
      <Box
        component="button"
        onClick={() => setMembersOpen(true)}
        data-testid="discussionMembersButton"
        sx={{
          display: "inline-flex",
          alignItems: "center",
          gap: 0.5,
          padding: 0,
          border: 0,
          background: "none",
          color: "inherit",
          font: "inherit",
          cursor: "pointer",
          verticalAlign: "bottom",
          "&:hover": { color: "primary.main" },
        }}
      >
        <PeopleIcon sx={{ fontSize: "1.1rem" }} />
        {discussion.member_count} members
      </Box>
    </Tooltip>
  );

  const subtitle = discussion.is_direct ? (
    other && (
      <Link component={RouterLink} to={`/user/${other.id}`} color="inherit">
        @{other.username}
      </Link>
    )
  ) : discussion.group ? (
    <>
      Everyone in{" "}
      <Link
        component={RouterLink}
        to={`/group/${discussion.group.id}`}
        color="inherit"
      >
        {discussion.group.name}
      </Link>
      {", "}
      {members}
    </>
  ) : (
    members
  );

  const action = (
    tooltip: string,
    icon: ReactNode,
    onClick: () => void,
    testId?: string,
  ) => (
    <Tooltip title={tooltip}>
      <IconButton size="small" onClick={onClick} data-testid={testId}>
        {icon}
      </IconButton>
    </Tooltip>
  );

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
      }}
    >
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
        <DiscussionAvatar discussion={discussion} myId={myId} size={40} />
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          {renaming !== null ? (
            <TextField
              autoFocus
              size="small"
              variant="standard"
              value={renaming}
              onChange={(event) => setRenaming(event.target.value)}
              onKeyDown={onRenameKeyDown}
              onBlur={commitRename}
            />
          ) : (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <Typography variant="h6" noWrap sx={{ lineHeight: 1.3 }}>
                {title}
              </Typography>
              {!discussion.is_direct && (
                <Tooltip title="Rename">
                  <IconButton
                    size="small"
                    onClick={() => setRenaming(discussion.name ?? title)}
                    data-testid="renameDiscussionButton"
                    sx={{ color: "text.secondary" }}
                  >
                    <EditIcon sx={{ fontSize: "1rem" }} />
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          )}
          <Typography variant="body2" color="textSecondary" noWrap>
            {subtitle}
          </Typography>
        </Box>
        <Box sx={{ display: "flex", flexShrink: 0 }}>
          {action(
            discussion.muted ? "Turn notifications back on" : "Mute",
            discussion.muted ? (
              <NotificationsOffIcon fontSize="small" />
            ) : (
              <NotificationsActiveIcon fontSize="small" />
            ),
            () =>
              updateMembership({ id: discussion.id, muted: !discussion.muted }),
            "muteDiscussionButton",
          )}
          {isFree &&
            !isCreator &&
            action("Leave", <LogoutIcon fontSize="small" />, leave)}
          {isCreator &&
            !discussion.is_direct &&
            action("Delete", <DeleteIcon fontSize="small" />, () =>
              setConfirmDelete(true),
            )}
        </Box>
      </Box>
      <Box
        ref={listRef}
        onScroll={onScroll}
        sx={{ flexGrow: 1, minHeight: 0, overflowY: "auto", padding: "1rem" }}
      >
        {isFetchingNextPage && (
          <Box sx={{ display: "flex", justifyContent: "center" }}>
            <CircularProgress size={20} />
          </Box>
        )}
        {isSuccess && messages.length === 0 && (
          <Typography
            variant="body2"
            color="textSecondary"
            sx={{ textAlign: "center", fontStyle: "italic", marginTop: 4 }}
          >
            No message yet. Say hello!
          </Typography>
        )}
        {messages.map((message, index) => {
          const previous = messages[index - 1];
          const mine = message.author.id === myId;
          const newDay =
            !previous ||
            !fromServer(previous.created_at).isSame(
              fromServer(message.created_at),
              "day",
            );
          const run = newDay || startsRun(message, previous);
          return (
            <Fragment key={message.id}>
              {newDay && (
                <Typography
                  variant="caption"
                  color="textSecondary"
                  component="div"
                  sx={{ textAlign: "center", margin: "1rem 0 0.5rem" }}
                >
                  {dayLabel(message.created_at)}
                </Typography>
              )}
              <Box
                sx={{
                  display: "flex",
                  gap: 1,
                  marginTop: run ? 1.5 : 0.25,
                  flexDirection: mine ? "row-reverse" : "row",
                  "&:hover .messageActions": { visibility: "visible" },
                }}
              >
                {!mine && (
                  <Box sx={{ width: 32, flexShrink: 0 }}>
                    {run && (
                      <UserAvatar
                        size={32}
                        userId={message.author.id}
                        firstName={message.author.first_name}
                        lastName={message.author.last_name}
                        username={message.author.username}
                        gravatarUrl={message.author.gravatar_url ?? ""}
                        isBot={message.author.is_bot}
                      />
                    )}
                  </Box>
                )}
                <Box
                  sx={{
                    maxWidth: "75%",
                    minWidth: 0,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: mine ? "flex-end" : "flex-start",
                  }}
                >
                  {run && (
                    <Typography
                      variant="caption"
                      color="textSecondary"
                      sx={{ margin: "0 0.5rem 0.125rem" }}
                    >
                      {!mine && (
                        <Box
                          component="span"
                          sx={{ fontWeight: 600, color: "text.primary" }}
                        >
                          {userName(message.author)}{" "}
                        </Box>
                      )}
                      {fromServer(message.created_at).format("HH:mm")}
                    </Typography>
                  )}
                  {editing === message.id ? (
                    <Box sx={{ width: "30rem", maxWidth: "100%" }}>
                      <CommentForm
                        textOnly
                        commentText={message.text}
                        editComment={({ text }: { text?: string }) => {
                          if (text?.trim()) {
                            editMessage({
                              id: discussion.id,
                              messageId: message.id,
                              text,
                            });
                          }
                        }}
                        onClose={() => setEditing(null)}
                      />
                    </Box>
                  ) : (
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 0.5,
                        flexDirection: mine ? "row-reverse" : "row",
                      }}
                    >
                      <Box
                        sx={{
                          borderRadius: "1rem",
                          padding: "0.375rem 0.875rem",
                          fontSize: "0.9rem",
                          overflowWrap: "anywhere",
                          backgroundColor: mine
                            ? alpha(theme.palette.primary.main, 0.15)
                            : alpha(theme.palette.text.primary, 0.06),
                          "& p": { margin: 0 },
                          "& p + p": { marginTop: "0.4em" },
                          "& pre": { whiteSpace: "pre-wrap" },
                        }}
                      >
                        <ReactMarkdown
                          remarkPlugins={[[remarkGfm, { singleTilde: false }]]}
                          components={{ text: emojiSupport, a: markdownLink }}
                        >
                          {highlightMentions(message.text)}
                        </ReactMarkdown>
                      </Box>
                      {edited(message) && (
                        <Typography variant="caption" color="textSecondary">
                          edited
                        </Typography>
                      )}
                      {mine && (
                        <Box
                          className="messageActions"
                          sx={{ visibility: "hidden", display: "flex" }}
                        >
                          <IconButton
                            size="small"
                            onClick={() => setEditing(message.id)}
                            sx={{ padding: "0.125rem" }}
                          >
                            <EditIcon sx={{ fontSize: "0.9rem" }} />
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() =>
                              deleteMessage({
                                id: discussion.id,
                                messageId: message.id,
                              })
                            }
                            sx={{
                              padding: "0.125rem",
                              "&:hover": { color: "error.main" },
                            }}
                          >
                            <CloseIcon sx={{ fontSize: "0.9rem" }} />
                          </IconButton>
                        </Box>
                      )}
                    </Box>
                  )}
                </Box>
              </Box>
            </Fragment>
          );
        })}
      </Box>
      <Box sx={{ borderTop: 1, borderColor: "divider" }}>
        <CommentForm
          textOnly
          placeholder={
            discussion.is_direct && other
              ? `Message ${userName(other)}`
              : `Message ${title}`
          }
          addComment={({ text }: { text: string }) =>
            sendMessage({ id: discussion.id, text })
          }
        />
      </Box>
      {!discussion.is_direct && (
        <DiscussionMembersDialog
          discussion={discussion}
          open={membersOpen}
          onClose={() => setMembersOpen(false)}
        />
      )}
      <ConfirmDeletionDialog
        dialogOpen={confirmDelete}
        closeDialog={() => setConfirmDelete(false)}
        deleteFunction={() => {
          setConfirmDelete(false);
          deleteDiscussion(discussion.id)
            .unwrap()
            .then(() => navigate("/discussions"))
            .catch(() => {});
        }}
        resourceName={`discussion "${title}" and all its messages`}
      />
    </Box>
  );
};

export default DiscussionThread;
