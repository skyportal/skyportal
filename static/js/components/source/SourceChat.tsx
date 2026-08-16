import { KeyboardEvent, Suspense, lazy, useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import ChatIcon from "@mui/icons-material/Chat";
import CloseIcon from "@mui/icons-material/Close";
import PictureInPictureAltIcon from "@mui/icons-material/PictureInPictureAlt";
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

import {
  useDeleteConversationMutation,
  useGetConversationsQuery,
} from "../../ducks/source";

const CommentList = lazy(() => import("../comment/CommentList"));

const MAIN_CHANNEL = "Comments";
const INLINE_KEY = "sourceChatInline";

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
    justifyContent: "space-between",
    padding: theme.spacing(1, 1, 0, 2),
  },
  sourceName: {
    lineHeight: "1em",
    fontWeight: 900,
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
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
  detach: {
    marginLeft: "auto",
    paddingRight: "0.25rem",
  },
  tabClose: {
    "&:hover": { color: theme.palette.error.main },
  },
  comments: {
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

// Inline mode is the default, kept as a user preference across all source pages.
export const useSourceChat = () => {
  const [inline, setInline] = useState(
    () => window.localStorage.getItem(INLINE_KEY) !== "false",
  );
  const [open, setOpen] = useState(false);

  const toggleInline = () => {
    window.localStorage.setItem(INLINE_KEY, String(!inline));
    setInline(!inline);
    setOpen(true);
  };

  return { inline, open, setOpen, toggleInline };
};

export type ChatTarget =
  | { type: "source"; id: string }
  | { type: "gcn_event"; id: number; dateobs: string };

interface SourceChatProps {
  target: ChatTarget;
  inline: boolean;
  open: boolean;
  setOpen: (open: boolean) => void;
  toggleInline?: () => void;
}

const SourceChat = ({
  target,
  inline,
  open,
  setOpen,
  toggleInline,
}: SourceChatProps) => {
  const { classes } = useStyles();
  const [channel, setChannel] = useState<string>(MAIN_CHANNEL);
  const [newChannel, setNewChannel] = useState<string | null>(null);
  const [addedChannels, setAddedChannels] = useState<string[]>([]);
  const [hoveredChannel, setHoveredChannel] = useState<string | null>(null);
  const downSm = useMediaQuery((theme: any) => theme.breakpoints.down("sm"));
  const { data: openedChannels = [] } = useGetConversationsQuery(
    target.type === "source" && (inline || open) ? target.id : skipToken,
  );
  const [deleteConversation] = useDeleteConversationMutation();

  const channels = [
    MAIN_CHANNEL,
    ...new Set(
      [...openedChannels, ...addedChannels].filter(
        (name) => name !== MAIN_CHANNEL,
      ),
    ),
  ];

  const createChannel = () => {
    const name = newChannel?.trim();
    if (name) {
      setAddedChannels([...addedChannels, name]);
      setChannel(name);
    }
    setNewChannel(null);
  };

  const onNewChannelKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter") createChannel();
    if (event.key === "Escape") setNewChannel(null);
  };

  const removeChannel = async (name: string) => {
    if (target.type === "source" && openedChannels.includes(name)) {
      await deleteConversation({ obj_id: target.id, channel: name });
    }
    setAddedChannels(addedChannels.filter((added) => added !== name));
    if (channel === name) setChannel(MAIN_CHANNEL);
  };

  const inlineToggle = toggleInline ? (
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

  const panel = (
    <Paper
      className={inline ? classes.inlinePanel : classes.panel}
      elevation={inline ? 1 : 8}
      data-testid="source-chat"
    >
      {!inline && (
        <div className={classes.header}>
          <Typography variant="h6" className={classes.sourceName}>
            {target.type === "source"
              ? target.id
              : dayjs(target.dateobs).format("YYMMDD HH:mm:ss")}
          </Typography>
          <div>
            {inlineToggle}
            <IconButton size="small" onClick={() => setOpen(false)}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </div>
        </div>
      )}
      {target.type === "source" && (
        <div className={classes.tabs}>
          <Tabs
            value={channel}
            onChange={(_, value) => setChannel(value)}
            variant="scrollable"
            scrollButtons="auto"
          >
            {channels.map((name) => (
              <Tab
                key={name}
                value={name}
                onMouseEnter={() => setHoveredChannel(name)}
                onMouseLeave={() => setHoveredChannel(null)}
                label={
                  <span className={classes.tabLabel}>
                    {name}
                    {name !== MAIN_CHANNEL && (
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
                }
              />
            ))}
          </Tabs>
          {newChannel === null ? (
            <Tooltip title="New conversation">
              <IconButton
                size="small"
                onClick={() => setNewChannel("")}
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
      <div className={classes.comments}>
        <Suspense
          fallback={
            <div className={classes.loader}>
              <CircularProgress />
            </div>
          }
        >
          {target.type === "source" ? (
            <CommentList
              key={channel}
              objID={target.id}
              compact
              channel={channel === MAIN_CHANNEL ? undefined : channel}
            />
          ) : (
            <CommentList
              associatedResourceType="gcn_event"
              gcnEventID={target.id}
              gcnEventDateobs={target.dateobs}
              compact
            />
          )}
        </Suspense>
      </div>
    </Paper>
  );

  if (inline) return panel;

  return (
    <>
      {!(downSm && open) && (
        <Tooltip title="Comments and discussions" placement="left">
          <Fab
            color="primary"
            size="medium"
            className={classes.fab}
            onClick={() => setOpen(!open)}
            data-testid="source-chat-button"
          >
            {open ? <CloseIcon /> : <ChatIcon />}
          </Fab>
        </Tooltip>
      )}
      {open && panel}
    </>
  );
};

export default SourceChat;
