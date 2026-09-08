import { KeyboardEvent, Suspense, lazy, useEffect, useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import ChatIcon from "@mui/icons-material/Chat";
import CloseIcon from "@mui/icons-material/Close";
import PictureInPictureAltIcon from "@mui/icons-material/PictureInPictureAlt";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import VerticalSplitIcon from "@mui/icons-material/VerticalSplit";
import Box from "@mui/material/Box";
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
import { INTERESTED_CHANNEL, MAIN_CHANNEL } from "./channels";

const CommentThread = lazy(() => import("./CommentThread"));
const AssistantThread = lazy(() => import("./AssistantThread"));

const centeredSx = {
  display: "flex",
  height: "100%",
  alignItems: "center",
  justifyContent: "center",
} as const;

interface CommentPanelProps {
  inline?: boolean;
}

const CommentPanel = ({ inline = false }: CommentPanelProps) => {
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
  const [channelToDelete, setChannelToDelete] = useState<string | null>(null);
  const downSm = useMediaQuery((theme: any) => theme.breakpoints.down("sm"));

  const hasComments = target?.type === "source" || target?.type === "gcn_event";
  const showComments =
    hasComments && (inline || !commentsInline || target.type !== "source");
  const showAssistant = !inline && assistantEnabled;
  const isComments = showComments && (space === "comments" || !showAssistant);
  const activeSpace: ChatSpace = isComments ? "comments" : "assistant";
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

  const commentChannels =
    target?.type === "source"
      ? [
          MAIN_CHANNEL,
          ...(hasInterested ? [INTERESTED_CHANNEL] : []),
          ...new Set(
            [...openedChannels, ...added.comments].filter(
              (name) => name !== MAIN_CHANNEL && name !== INTERESTED_CHANNEL,
            ),
          ),
        ]
      : [MAIN_CHANNEL];
  const chats = [...new Set([...assistantConversations, ...added.assistant])];

  // Opened once per user, so deleting the last chat stays final.
  const seeded =
    !inline &&
    chatsLoaded &&
    userId !== undefined &&
    assistantConversations.length === 0;
  useEffect(() => {
    if (!seeded) return;
    const key = `assistantChatSeeded:${userId}`;
    if (window.localStorage.getItem(key) === "true") return;
    window.localStorage.setItem(key, "true");
    setAdded((current) => ({
      ...current,
      assistant: [...current.assistant, "Chat 1"],
    }));
  }, [seeded, userId]);

  const channels = isComments ? commentChannels : chats;
  const activeChannel = isComments
    ? commentChannels.includes(channel)
      ? channel
      : MAIN_CHANNEL
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
        <IconButton size="small" onClick={toggleInline}>
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
      : target.type === "filter"
        ? `filter ${target.id}`
        : dayjs(target.dateobs).format("YYMMDD HH:mm:ss");

  if (!showComments && !showAssistant) return null;

  const bothSpaces = showComments && showAssistant;

  const panel = (
    <Paper
      elevation={inline ? 1 : 8}
      data-testid={isComments ? "source-chat" : undefined}
      sx={(theme) => ({
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        ...(inline
          ? { height: "60vh" }
          : {
              position: "fixed",
              right: "1.5rem",
              bottom: "5.5rem",
              zIndex: theme.zIndex.drawer,
              width: "26rem",
              maxWidth: "calc(100vw - 3rem)",
              height: "70vh",
              maxHeight: "calc(100vh - 10rem)",
              [theme.breakpoints.down("sm")]: {
                inset: 0,
                width: "100%",
                maxWidth: "100%",
                height: "100%",
                maxHeight: "100%",
                borderRadius: 0,
              },
            }),
      })}
    >
      {!inline && (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            padding: bothSpaces ? "0 0.5rem 0 0" : "0.5rem 0.5rem 0 1rem",
          }}
        >
          {bothSpaces ? (
            <Tabs
              value={activeSpace}
              onChange={(_, value) => setSpace(value)}
              sx={{
                minHeight: "auto",
                "& .MuiTab-root": {
                  minHeight: "auto",
                  minWidth: "auto",
                  padding: "0.375rem 0.5rem",
                  fontSize: "0.8rem",
                  textTransform: "none",
                },
              }}
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
            !isComments && (
              <Typography
                variant="h6"
                noWrap
                sx={{ lineHeight: "1em", fontWeight: 900 }}
              >
                Assistant
              </Typography>
            )
          )}
          <Box sx={{ marginLeft: "auto", flexShrink: 0 }}>
            {inlineToggle}
            <IconButton size="small" onClick={() => setOpen(false)}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        </Box>
      )}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
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
            const closable =
              !isComments ||
              (name !== MAIN_CHANNEL && name !== INTERESTED_CHANNEL);
            return (
              <Tab
                key={name}
                value={name}
                disableRipple={renaming?.from === name}
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
                    <Box
                      component="span"
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.25rem",
                      }}
                      onDoubleClick={
                        isComments
                          ? undefined
                          : () => setRenaming({ from: name, to: name })
                      }
                    >
                      <Box
                        component="span"
                        title={label}
                        sx={{
                          maxWidth: "8rem",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {label}
                      </Box>
                      {closable && (
                        <CloseIcon
                          fontSize="inherit"
                          sx={{
                            visibility: "hidden",
                            ".MuiTab-root:hover &": { visibility: "visible" },
                            "&:hover": { color: "error.main" },
                          }}
                          onClick={(event) => {
                            event.stopPropagation();
                            removeChannel(name);
                          }}
                        />
                      )}
                    </Box>
                  )
                }
              />
            );
          })}
        </Tabs>
        {(!isComments || target?.type === "source") &&
          (newChannel === null ? (
            <Tooltip title={isComments ? "New conversation" : "New chat"}>
              <IconButton size="small" onClick={addConversation}>
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
          ))}
        {inline && (
          <Box sx={{ marginLeft: "auto", paddingRight: "0.25rem" }}>
            {inlineToggle}
          </Box>
        )}
      </Box>
      <Box sx={{ flexGrow: 1, minHeight: 0 }}>
        <Suspense
          fallback={
            <Box sx={centeredSx}>
              <CircularProgress />
            </Box>
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
              <Box
                sx={{
                  ...centeredSx,
                  fontSize: "0.75rem",
                  fontStyle: "italic",
                  color: "text.secondary",
                }}
              >
                No chat yet. Start one with the + above.
              </Box>
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
      </Box>
      <ConfirmDeletionDialog
        dialogOpen={channelToDelete !== null}
        closeDialog={() => setChannelToDelete(null)}
        deleteFunction={confirmRemoveChannel}
        resourceName={`conversation "${channelToDelete}" and everything in it`}
      />
    </Paper>
  );

  if (inline) return panel;

  return (
    <>
      {!(downSm && open) && (
        <Tooltip
          title={
            bothSpaces
              ? "Comments and assistant"
              : showAssistant
                ? "Assistant"
                : "Comments"
          }
          placement="left"
        >
          <Fab
            color="primary"
            size="medium"
            onClick={() => setOpen(!open)}
            data-testid="source-chat-button"
            sx={{
              position: "fixed",
              right: "1.5rem",
              bottom: "1.5rem",
              zIndex: "drawer",
            }}
          >
            {open ? (
              <CloseIcon />
            ) : bothSpaces ? (
              <Box
                component="span"
                sx={{ position: "relative", width: "1.5rem", height: "1.5rem" }}
              >
                <ChatIcon
                  sx={{
                    position: "absolute",
                    top: -3,
                    left: -3,
                    clipPath: "polygon(0 0, 0 110%, 110% 0)",
                  }}
                />
                <SmartToyIcon
                  sx={{
                    position: "absolute",
                    top: 3,
                    left: 3,
                    clipPath: "polygon(100% 100%, -10% 100%, 100% -10%)",
                  }}
                />
                <Box
                  component="span"
                  sx={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    width: "141%",
                    height: "5%",
                    backgroundColor: "currentColor",
                    transform: "translate(-50%, -50%) rotate(-45deg)",
                  }}
                />
              </Box>
            ) : showAssistant ? (
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
