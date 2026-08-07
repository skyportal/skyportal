import { KeyboardEvent, Suspense, lazy, useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import ChatIcon from "@mui/icons-material/Chat";
import CloseIcon from "@mui/icons-material/Close";
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

import {
  useDeleteConversationMutation,
  useGetConversationsQuery,
} from "../../ducks/source";

const CommentList = lazy(() => import("../comment/CommentList"));

const MAIN_CHANNEL = "Comments";

const useStyles = makeStyles()((theme) => ({
  fab: {
    position: "fixed",
    right: "1.5rem",
    bottom: "1.5rem",
    zIndex: theme.zIndex.drawer,
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

interface SourceChatProps {
  sourceID: string;
}

const SourceChat = ({ sourceID }: SourceChatProps) => {
  const { classes } = useStyles();
  const [channel, setChannel] = useState<string | null>(null);
  const [newChannel, setNewChannel] = useState<string | null>(null);
  const [addedChannels, setAddedChannels] = useState<string[]>([]);
  const [hoveredChannel, setHoveredChannel] = useState<string | null>(null);
  const downSm = useMediaQuery((theme: any) => theme.breakpoints.down("sm"));
  const { data: openedChannels = [] } = useGetConversationsQuery(sourceID, {
    skip: channel === null,
  });
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
    if (openedChannels.includes(name)) {
      await deleteConversation({ obj_id: sourceID, channel: name });
    }
    setAddedChannels(addedChannels.filter((added) => added !== name));
    if (channel === name) setChannel(MAIN_CHANNEL);
  };

  return (
    <>
      {!(downSm && channel !== null) && (
        <Tooltip title="Comments and discussions" placement="left">
          <Fab
            color="primary"
            size="medium"
            className={classes.fab}
            onClick={() => setChannel(channel === null ? MAIN_CHANNEL : null)}
            data-testid="source-chat-button"
          >
            {channel === null ? <ChatIcon /> : <CloseIcon />}
          </Fab>
        </Tooltip>
      )}
      {channel !== null && (
        <Paper
          className={classes.panel}
          elevation={8}
          data-testid="source-chat"
        >
          <div className={classes.header}>
            <Typography variant="h6" className={classes.sourceName}>
              {sourceID}
            </Typography>
            <IconButton size="small" onClick={() => setChannel(null)}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </div>
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
          </div>
          <div className={classes.comments}>
            <Suspense
              fallback={
                <div className={classes.loader}>
                  <CircularProgress />
                </div>
              }
            >
              <CommentList
                key={channel}
                objID={sourceID}
                compact
                channel={channel === MAIN_CHANNEL ? undefined : channel}
              />
            </Suspense>
          </div>
        </Paper>
      )}
    </>
  );
};

export default SourceChat;
