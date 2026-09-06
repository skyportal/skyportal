import { KeyboardEvent, Suspense, lazy, useEffect, useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import ChatIcon from "@mui/icons-material/Chat";
import CloseIcon from "@mui/icons-material/Close";
import PictureInPictureAltIcon from "@mui/icons-material/PictureInPictureAlt";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import VerticalSplitIcon from "@mui/icons-material/VerticalSplit";
import CircularProgress from "@mui/material/CircularProgress";
import Fab from "@mui/material/Fab";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { makeStyles } from "tss-react/mui";
import { skipToken } from "@reduxjs/toolkit/query";
import dayjs from "dayjs";

import type { ChatSpace } from "../../contexts/CommentPanelContext";
import { useCommentPanel } from "../../contexts/CommentPanelContext";
import { useGetConfigQuery } from "../../ducks/config";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useDeleteAssistantConversationMutation,
  useGetAssistantConversationsQuery,
  useRenameAssistantConversationMutation,
} from "../../ducks/assistant";
import {
  useDeleteConversationMutation,
  useGetConversationsQuery,
} from "../../ducks/source";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import { DEFAULT_CHAT, INTERESTED_CHANNEL, MAIN_CHANNEL } from "./channels";

const SEEDED_KEY = "assistantChatSeeded";

const CommentThread = lazy(() => import("./CommentThread"));
const AssistantThread = lazy(() => import("./AssistantThread"));

const useStyles = makeStyles()((theme) => ({
  fab: {
    position: "fixed",
    right: "1.5rem",
    bottom: "1.5rem",
    zIndex: theme.zIndex.drawer,
  },
  inlinePanel: {
    display: "flex",
    flexDirection: "column",
    height: "60vh",
    overflow: "hidden",
  },
  panel: {
    position: "fixed",
    right: "1.5rem",
    bottom: "5.5rem",
    zIndex: theme.zIndex.drawer,
    display: "flex",
    flexDirection: "column",
    width: "26rem",
    maxWidth: "calc(100vw - 3rem)",
    height: "70vh",
    maxHeight: "calc(100vh - 10rem)",
    overflow: "hidden",
    [theme.breakpoints.down("sm")]: {
      inset: 0,
      width: "100%",
      maxWidth: "100%",
      height: "100%",
      maxHeight: "100%",
      borderRadius: 0,
    },
  },
  header: {
    display: "flex",
    alignItems: "center",
    padding: theme.spacing(1, 1, 0, 2),
  },
  headerFlush: {
    padding: theme.spacing(0, 1, 0, 0),
  },
  headerActions: {
    marginLeft: "auto",
    flexShrink: 0,
  },
  title: {
    padding: theme.spacing(0.5, 2, 0),
  },
  targetName: {
    lineHeight: "1em",
    fontWeight: 900,
  },
  spaceTabs: {
    minHeight: "auto",
    "& .MuiTab-root": {
      minHeight: "auto",
      minWidth: "auto",
      padding: theme.spacing(0.75, 1),
      fontSize: "0.8rem",
      textTransform: "none",
    },
  },
  splitIcon: {
    position: "relative",
    width: "1.5rem",
    height: "1.5rem",
  },
  splitBar: {
    position: "absolute",
    top: "50%",
    left: "50%",
    width: "141%",
    height: "5%",
    backgroundColor: "currentColor",
    transform: "translate(-50%, -50%) rotate(-45deg)",
  },
  empty: {
    display: "flex",
    height: "100%",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "0.75rem",
    fontStyle: "italic",
    color: theme.palette.text.secondary,
  },
  tabs: {
    display: "flex",
    alignItems: "center",
    borderBottom: `1px solid ${theme.palette.divider}`,
  },
  tabLabel: {
    display: "flex",
    alignItems: "center",
    gap: "0.25rem",
  },
  tabName: {
    maxWidth: "8rem",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  detach: {
    marginLeft: "auto",
    paddingRight: "0.25rem",
  },
  tabClose: {
    "&:hover": { color: theme.palette.error.main },
  },
  body: {
    flexGrow: 1,
    minHeight: 0,
  },
  loader: {
    display: "flex",
    flexGrow: 1,
    alignItems: "center",
    justifyContent: "center",
    height: "100%",
  },
}));

interface CommentPanelProps {
  /** Set on the instance a page renders in its own layout. */
  inline?: boolean;
}

const CommentPanel = ({ inline = false }: CommentPanelProps) => {
  const { classes, cx } = useStyles();
  const {
    target,
    inline: commentsInline,
    toggleInline,
    open,
    setOpen,
    space,
    setSpace,
    channel,
    setChannel,
    assistantChannel,
    setAssistantChannel,
  } = useCommentPanel();
  const assistantEnabled =
    useGetConfigQuery().data?.["assistantEnabled"] === true;
  const userId = useGetProfileQuery().data?.id;
  const [newChannel, setNewChannel] = useState<string | null>(null);
  const [added, setAdded] = useState<Record<ChatSpace, string[]>>({
    comments: [],
    assistant: [],
  });
  const [renaming, setRenaming] = useState<{ from: string; to: string } | null>(
    null,
  );
  const [hoveredChannel, setHoveredChannel] = useState<string | null>(null);
  const [channelToDelete, setChannelToDelete] = useState<string | null>(null);
  const downSm = useMediaQuery((theme: any) => theme.breakpoints.down("sm"));

  const commentsOnThePage = commentsInline && target?.type === "source";
  const spaces: ChatSpace[] = [
    ...(target && (inline || !commentsOnThePage)
      ? (["comments"] as const)
      : []),
    ...(!inline && assistantEnabled ? (["assistant"] as const) : []),
  ];
  const activeSpace: ChatSpace = spaces.includes(space)
    ? space
    : (spaces[0] ?? "assistant");
  const isComments = activeSpace === "comments";
  const visible = inline || open;

  const { data: openedChannels = [] } = useGetConversationsQuery(
    target?.type === "source" && isComments && visible ? target.id : skipToken,
  );
  const { data: assistantConversations = [], isSuccess: chatsLoaded } =
    useGetAssistantConversationsQuery(undefined, {
      skip: !assistantEnabled || !visible,
    });
  const [deleteConversation] = useDeleteConversationMutation();
  const [deleteAssistantConversation] =
    useDeleteAssistantConversationMutation();
  const [renameAssistantConversation] =
    useRenameAssistantConversationMutation();

  const hasInterested =
    openedChannels.includes(INTERESTED_CHANNEL) ||
    channel === INTERESTED_CHANNEL;

  const commentChannels = [
    MAIN_CHANNEL,
    ...(hasInterested ? [INTERESTED_CHANNEL] : []),
    ...new Set(
      [...openedChannels, ...added.comments].filter(
        (name) => name !== MAIN_CHANNEL && name !== INTERESTED_CHANNEL,
      ),
    ),
  ];
  const chats = [...new Set([...assistantConversations, ...added.assistant])];

  // Opened once per user, so deleting the last chat stays final.
  const seeded =
    !inline &&
    chatsLoaded &&
    userId !== undefined &&
    assistantConversations.length === 0;
  useEffect(() => {
    if (!seeded) return;
    const key = `${SEEDED_KEY}:${userId}`;
    if (window.localStorage.getItem(key) === "true") return;
    window.localStorage.setItem(key, "true");
    setAdded((current) => ({
      ...current,
      assistant: [...current.assistant, DEFAULT_CHAT],
    }));
  }, [seeded, userId]);

  const channels = isComments ? commentChannels : chats;
  const activeChannel = isComments
    ? channel
    : assistantChannel && chats.includes(assistantChannel)
      ? assistantChannel
      : chats[0];

  const selectChannel = (name: string | null) => {
    if (isComments) {
      setChannel(name ?? MAIN_CHANNEL);
    } else {
      setAssistantChannel(name);
    }
  };

  const closable = (name: string) =>
    !isComments || (name !== MAIN_CHANNEL && name !== INTERESTED_CHANNEL);

  const addConversation = () => {
    if (isComments) {
      setNewChannel("");
      return;
    }
    let index = 1;
    while (chats.includes(`Chat ${index}`)) index += 1;
    const name = `Chat ${index}`;
    setAdded({ ...added, assistant: [...added.assistant, name] });
    setAssistantChannel(name);
  };

  const createChannel = () => {
    const name = newChannel?.trim();
    if (name) {
      setAdded({ ...added, comments: [...added.comments, name] });
      setChannel(name);
    }
    setNewChannel(null);
  };

  const onNewChannelKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter") createChannel();
    if (event.key === "Escape") setNewChannel(null);
  };

  const commitRename = () => {
    if (!renaming) return;
    const { from, to } = renaming;
    const name = to.trim();
    setRenaming(null);
    if (!name || name === from || chats.includes(name)) return;
    setAdded({
      ...added,
      assistant: [...added.assistant.filter((other) => other !== from), name],
    });
    if (activeChannel === from) setAssistantChannel(name);
    if (assistantConversations.includes(from)) {
      renameAssistantConversation({ channel: from, name });
    }
  };

  const onRenameKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter") commitRename();
    if (event.key === "Escape") setRenaming(null);
  };

  const forgetChannel = (name: string) => {
    const fallback = channels.filter((other) => other !== name)[0];
    setAdded({
      ...added,
      [activeSpace]: added[activeSpace].filter((other) => other !== name),
    });
    if (activeChannel === name) selectChannel(fallback ?? null);
  };

  const removeChannel = (name: string) => {
    const stored = isComments
      ? target?.type === "source" && openedChannels.includes(name)
      : assistantConversations.includes(name);
    if (stored) {
      setChannelToDelete(name);
    } else {
      forgetChannel(name);
    }
  };

  const confirmRemoveChannel = () => {
    if (!channelToDelete) return;
    const name = channelToDelete;
    setChannelToDelete(null);
    const removal = isComments
      ? target?.type === "source" &&
        deleteConversation({ obj_id: target.id, channel: name })
      : deleteAssistantConversation(name);
    if (!removal) return;
    removal
      .unwrap()
      .then(() => forgetChannel(name))
      .catch(() => {});
  };

  const inlineToggle =
    isComments && target?.type === "source" ? (
      <Tooltip title={inline ? "Detach the panel" : "Display in the page"}>
        <IconButton
          size="small"
          onClick={toggleInline}
          data-testid="toggle-inline-chat"
        >
          {inline ? (
            <PictureInPictureAltIcon fontSize="small" />
          ) : (
            <VerticalSplitIcon fontSize="small" />
          )}
        </IconButton>
      </Tooltip>
    ) : null;

  const targetLabel = !target
    ? null
    : target.type === "source"
      ? target.id
      : dayjs(target.dateobs).format("YYMMDD HH:mm:ss");

  const showHeading =
    isComments && targetLabel !== null && target?.type !== "source";
  const heading = (
    <Typography variant="h6" className={classes.targetName} noWrap>
      {targetLabel}
    </Typography>
  );

  if (spaces.length === 0) return null;

  const panel = (
    <Paper
      className={inline ? classes.inlinePanel : classes.panel}
      elevation={inline ? 1 : 8}
      data-testid={isComments ? "source-chat" : undefined}
    >
      {!inline && (
        <>
          <div
            className={cx(
              classes.header,
              spaces.length > 1 && classes.headerFlush,
            )}
          >
            {spaces.length > 1 ? (
              <Tabs
                value={activeSpace}
                onChange={(_, value) => setSpace(value)}
                className={classes.spaceTabs}
              >
                <Tab
                  value="comments"
                  icon={<ChatIcon fontSize="small" />}
                  iconPosition="start"
                  label="Comments"
                />
                <Tab
                  value="assistant"
                  icon={<SmartToyIcon fontSize="small" />}
                  iconPosition="start"
                  label="Assistant"
                />
              </Tabs>
            ) : (
              showHeading && heading
            )}
            <div className={classes.headerActions}>
              {inlineToggle}
              <IconButton size="small" onClick={() => setOpen(false)}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </div>
          </div>
          {spaces.length > 1 && showHeading && (
            <div className={classes.title}>{heading}</div>
          )}
        </>
      )}
      {(!isComments || target?.type === "source") && (
        <div className={classes.tabs}>
          <Tabs
            value={activeChannel ?? false}
            onChange={(_, value) => selectChannel(value)}
            variant="scrollable"
            scrollButtons="auto"
          >
            {channels.map((name) => {
              const label =
                isComments && name === MAIN_CHANNEL && targetLabel
                  ? targetLabel
                  : name;
              return (
                <Tab
                  key={name}
                  value={name}
                  disableRipple={renaming?.from === name}
                  onMouseEnter={() => setHoveredChannel(name)}
                  onMouseLeave={() => setHoveredChannel(null)}
                  label={
                    renaming?.from === name ? (
                      <TextField
                        autoFocus
                        size="small"
                        variant="standard"
                        value={renaming.to}
                        onChange={(event) =>
                          setRenaming({ from: name, to: event.target.value })
                        }
                        onKeyDown={onRenameKeyDown}
                        onBlur={commitRename}
                        onMouseDown={(event) => event.stopPropagation()}
                        onClick={(event) => event.stopPropagation()}
                      />
                    ) : (
                      <span
                        className={classes.tabLabel}
                        onDoubleClick={
                          isComments
                            ? undefined
                            : () => setRenaming({ from: name, to: name })
                        }
                      >
                        <span className={classes.tabName} title={label}>
                          {label}
                        </span>
                        {closable(name) && (
                          <CloseIcon
                            fontSize="inherit"
                            className={classes.tabClose}
                            style={{
                              visibility:
                                hoveredChannel === name ? "visible" : "hidden",
                            }}
                            onClick={(event) => {
                              event.stopPropagation();
                              removeChannel(name);
                            }}
                            data-testid={`delete-channel-${name}`}
                          />
                        )}
                      </span>
                    )
                  }
                />
              );
            })}
          </Tabs>
          {newChannel === null ? (
            <Tooltip title={isComments ? "New conversation" : "New chat"}>
              <IconButton
                size="small"
                onClick={addConversation}
                data-testid="new-channel-button"
              >
                <AddIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          ) : (
            <TextField
              autoFocus
              size="small"
              variant="standard"
              placeholder="Conversation name"
              value={newChannel}
              onChange={(event) => setNewChannel(event.target.value)}
              onKeyDown={onNewChannelKeyDown}
              onBlur={createChannel}
            />
          )}
          {inline && <div className={classes.detach}>{inlineToggle}</div>}
        </div>
      )}
      <div className={classes.body}>
        <Suspense
          fallback={
            <div className={classes.loader}>
              <CircularProgress />
            </div>
          }
        >
          {!isComments ? (
            activeChannel ? (
              <AssistantThread
                key={activeChannel}
                channel={activeChannel}
                target={target}
              />
            ) : (
              <div className={classes.empty}>
                No chat yet. Start one with the + above.
              </div>
            )
          ) : target?.type === "source" ? (
            <CommentThread
              key={channel}
              objID={target.id}
              channel={channel === MAIN_CHANNEL ? undefined : channel}
              pinned={channel === INTERESTED_CHANNEL}
            />
          ) : (
            target && (
              <CommentThread
                resourceType="gcn_event"
                gcnEventID={target.id}
                gcnEventDateobs={target.dateobs}
              />
            )
          )}
        </Suspense>
      </div>
      <ConfirmDeletionDialog
        dialogOpen={channelToDelete !== null}
        closeDialog={() => setChannelToDelete(null)}
        deleteFunction={confirmRemoveChannel}
        resourceName={`conversation "${channelToDelete}" and everything in it`}
      />
    </Paper>
  );

  if (inline) return panel;

  const bothSpaces = spaces.length > 1;
  const assistantOnly = !bothSpaces && spaces[0] === "assistant";

  return (
    <>
      {!(downSm && open) && (
        <Tooltip
          title={
            bothSpaces
              ? "Comments and assistant"
              : assistantOnly
                ? "Assistant"
                : "Comments"
          }
          placement="left"
        >
          <Fab
            color="primary"
            size="medium"
            className={classes.fab}
            onClick={() => setOpen(!open)}
            data-testid="source-chat-button"
          >
            {open ? (
              <CloseIcon />
            ) : bothSpaces ? (
              <span className={classes.splitIcon}>
                <ChatIcon
                  sx={{ position: "absolute", top: -3, left: -3 }}
                  style={{ clipPath: "polygon(0 0, 0 110%, 110% 0)" }}
                />
                <SmartToyIcon
                  sx={{ position: "absolute", top: 3, left: 3 }}
                  style={{
                    clipPath: "polygon(100% 100%, -10% 100%, 100% -10%)",
                  }}
                />
                <span className={classes.splitBar} />
              </span>
            ) : assistantOnly ? (
              <SmartToyIcon />
            ) : (
              <ChatIcon />
            )}
          </Fab>
        </Tooltip>
      )}
      {open && panel}
    </>
  );
};

export default CommentPanel;
