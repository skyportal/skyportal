import { ReactElement, useState } from "react";
import { useSearchParams } from "react-router-dom";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import { alpha } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import BugReportIcon from "@mui/icons-material/BugReportOutlined";
import LightbulbIcon from "@mui/icons-material/LightbulbOutlined";
import ChatIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import SendIcon from "@mui/icons-material/SendOutlined";
import ScheduleIcon from "@mui/icons-material/Schedule";
import QuestionAnswerIcon from "@mui/icons-material/QuestionAnswerOutlined";
import CheckCircleIcon from "@mui/icons-material/CheckCircleOutlineOutlined";
import ReplyIcon from "@mui/icons-material/Reply";
import DoneIcon from "@mui/icons-material/Done";
import UndoIcon from "@mui/icons-material/Undo";
import AssignIcon from "@mui/icons-material/AssignmentIndOutlined";
import UnassignIcon from "@mui/icons-material/PersonRemoveOutlined";
import TakeOverIcon from "@mui/icons-material/SwapHoriz";
import AddLinkIcon from "@mui/icons-material/AddLink";
import CloseIcon from "@mui/icons-material/Close";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import UserAvatar, { getUserRealName } from "../user/UserAvatar";
import { useAppDispatch } from "../../types/hooks";
import { useGetProfileQuery, useHasPermission } from "../../ducks/profile";
import {
  useAddFeedbackMutation,
  useGetFeedbackQuery,
  useReplyToFeedbackMutation,
  useUpdateFeedbackMutation,
  statusOf,
  type Feedback,
  type FeedbackCategory,
} from "../../ducks/feedback";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const CATEGORIES: Record<
  FeedbackCategory,
  { label: string; icon: ReactElement }
> = {
  bug: { label: "Bug report", icon: <BugReportIcon /> },
  change: { label: "Change request", icon: <LightbulbIcon /> },
  other: { label: "Other", icon: <ChatIcon /> },
};

const TOGGLES_SX = {
  "& .MuiToggleButton-root": { color: "text.secondary" },
  "& .MuiToggleButton-root.Mui-selected": { color: "text.primary" },
};

const STATUSES = {
  open: { label: "Open", color: "warning", icon: <ScheduleIcon /> },
  answered: {
    label: "Answered",
    color: "primary",
    icon: <QuestionAnswerIcon />,
  },
  resolved: { label: "Resolved", color: "success", icon: <CheckCircleIcon /> },
} as const;

type Status = keyof typeof STATUSES;

const nameOf = (user: Feedback["author"]) =>
  getUserRealName(user.first_name, user.last_name) || user.username;

const Author = ({
  author,
  size,
  noTooltip = false,
}: {
  author: Feedback["author"];
  size: number;
  noTooltip?: boolean;
}) => (
  <UserAvatar
    size={size}
    noTooltip={noTooltip}
    username={author.username}
    firstName={author.first_name ?? null}
    lastName={author.last_name ?? null}
    gravatarUrl={author.gravatar_url ?? ""}
    userId={author.id}
  />
);

const Signature = ({
  author,
  at,
}: {
  author: Feedback["author"];
  at: string;
}) => (
  <>
    <Typography variant="body2" sx={{ fontWeight: 600 }}>
      {nameOf(author)}
    </Typography>
    <Posted at={at} />
  </>
);

const Posted = ({ at }: { at: string }) => {
  const date = dayjs.utc(at);
  return (
    <Tooltip title={date.local().format("MMM D, YYYY HH:mm")}>
      <Typography variant="caption" color="text.secondary">
        {date.fromNow()}
      </Typography>
    </Tooltip>
  );
};

const TextSend = ({
  label,
  placeholder,
  minRows,
  loading,
  onSend,
  initialText = "",
}: {
  label: string;
  placeholder: string;
  minRows: number;
  loading: boolean;
  onSend: (text: string) => Promise<unknown>;
  initialText?: string;
}) => {
  const [text, setText] = useState(initialText);
  return (
    <>
      <TextField
        label={label}
        placeholder={placeholder}
        multiline
        minRows={minRows}
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <Box>
        <Button
          async
          loading={loading}
          disabled={!text.trim()}
          onClick={async () => {
            await onSend(text);
            setText("");
          }}
          endIcon={<SendIcon />}
        >
          Send
        </Button>
      </Box>
    </>
  );
};

const FeedbackForm = () => {
  const [category, setCategory] = useState<FeedbackCategory>("bug");
  const [addFeedback, { isLoading }] = useAddFeedbackMutation();
  const [searchParams, setSearchParams] = useSearchParams();
  const dispatch = useAppDispatch();

  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        Found a bug, or want something to change? Leave a message to the admins.
      </Typography>
      <ToggleButtonGroup
        exclusive
        size="small"
        value={category}
        onChange={(_, value) => value && setCategory(value)}
        sx={TOGGLES_SX}
      >
        {Object.entries(CATEGORIES).map(([value, { label, icon }]) => (
          <ToggleButton key={value} value={value} sx={{ gap: 1, px: 2 }}>
            {icon}
            {label}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
      <TextSend
        label="Message"
        placeholder="What happened, or what would you like to change?"
        minRows={4}
        loading={isLoading}
        initialText={searchParams.get("text") ?? ""}
        onSend={async (text) => {
          await addFeedback({ category, text }).unwrap();
          searchParams.delete("text");
          setSearchParams(searchParams, { replace: true });
          dispatch(
            showNotification("Thanks, your message was sent to the admins"),
          );
        }}
      />
    </Stack>
  );
};

const AssignButton = ({ message }: { message: Feedback }) => {
  const [confirming, setConfirming] = useState(false);
  const { data: profile } = useGetProfileQuery();
  const [updateFeedback] = useUpdateFeedbackMutation();
  const { assignee } = message;
  const assign = (assigneeId: number | null) =>
    updateFeedback({ id: message.id, assignee_id: assigneeId });

  if (!profile) return null;
  if (assignee?.id === profile.id)
    return (
      <Button
        size="small"
        endIcon={<UnassignIcon />}
        onClick={() => assign(null)}
      >
        Unassign
      </Button>
    );
  if (!assignee)
    return (
      <Button
        size="small"
        endIcon={<AssignIcon />}
        onClick={() => assign(profile.id)}
      >
        Assign to me
      </Button>
    );
  return (
    <>
      <Button
        size="small"
        endIcon={<TakeOverIcon />}
        onClick={() => setConfirming(true)}
      >
        Take over
      </Button>
      <Dialog open={confirming} onClose={() => setConfirming(false)}>
        <DialogTitle>Take over this message?</DialogTitle>
        <DialogContent>
          {nameOf(assignee)} is working on it. It will be assigned to you
          instead.
        </DialogContent>
        <DialogActions>
          <Button secondary autoFocus onClick={() => setConfirming(false)}>
            Cancel
          </Button>
          <Button
            primary
            onClick={() => {
              setConfirming(false);
              assign(profile.id);
            }}
          >
            Take over
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

// "https://github.com/owner/repo/pull/12" -> "owner/repo#12"
const prLabel = (url: string) =>
  url.replace(/^https:\/\/github\.com\/([^/]+\/[^/]+)\/pull\/(\d+)$/, "$1#$2");

const PullRequests = ({
  message,
  isAdmin,
}: {
  message: Feedback;
  isAdmin: boolean;
}) => {
  const [updateFeedback] = useUpdateFeedbackMutation();
  const pullRequests = message.pull_requests ?? [];
  if (!pullRequests.length) return null;
  const urls = pullRequests.map(({ url }) => url);

  return (
    <Stack
      direction="row"
      sx={{ mt: 1, flexWrap: "wrap", columnGap: 1, alignItems: "center" }}
    >
      {pullRequests.map(({ url, deployed }) => (
        <Box
          key={url}
          sx={{
            display: "inline-flex",
            alignItems: "center",
            "& .unlink": { display: "none" },
            "&:hover .unlink, &:focus-within .unlink": {
              display: "inline-flex",
            },
            // no hover on touch screens
            "@media (hover: none)": { "& .unlink": { display: "inline-flex" } },
          }}
        >
          <Tooltip
            title={`${prLabel(url)}: ${deployed ? "deployed" : "not deployed yet"}`}
          >
            <Link
              variant="body2"
              href={url}
              target="_blank"
              rel="noreferrer"
              sx={{ fontWeight: "bold" }}
            >
              {`#${url.split("/").pop()}`}
            </Link>
          </Tooltip>
          {isAdmin && (
            <Tooltip title="Unlink">
              <IconButton
                className="unlink"
                size="small"
                aria-label={`Unlink ${prLabel(url)}`}
                onClick={() =>
                  updateFeedback({
                    id: message.id,
                    pr_urls: urls.filter((other) => other !== url),
                  })
                }
              >
                <CloseIcon sx={{ fontSize: "0.9rem" }} />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      ))}
      {message.deployed_at && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ alignSelf: "center" }}
        >
          Deployed <Posted at={message.deployed_at} />
        </Typography>
      )}
    </Stack>
  );
};

const LinkPullRequest = ({
  message,
  onDone,
}: {
  message: Feedback;
  onDone: () => void;
}) => {
  const [url, setUrl] = useState("");
  const [updateFeedback, { isLoading }] = useUpdateFeedbackMutation();
  const urls = (message.pull_requests ?? []).map((pr) => pr.url);

  return (
    <Stack direction="row" spacing={1} sx={{ mt: 1.5, alignItems: "center" }}>
      <TextField
        size="small"
        label="Pull request URL"
        placeholder="https://github.com/skyportal/skyportal/pull/1234"
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        sx={{ flexGrow: 1 }}
      />
      <Button
        async
        loading={isLoading}
        disabled={!url.trim()}
        onClick={async () => {
          await updateFeedback({
            id: message.id,
            pr_urls: [...urls, url.trim()],
          }).unwrap();
          setUrl("");
          onDone();
        }}
      >
        Link
      </Button>
    </Stack>
  );
};

const Message = ({
  message,
  isAdmin,
}: {
  message: Feedback;
  isAdmin: boolean;
}) => {
  const [replying, setReplying] = useState(false);
  const [linking, setLinking] = useState(false);
  const { data: profile } = useGetProfileQuery();
  const [updateFeedback] = useUpdateFeedbackMutation();
  const [replyToFeedback, { isLoading }] = useReplyToFeedbackMutation();
  const { label, icon } = CATEGORIES[message.category];
  const status = STATUSES[statusOf(message)];
  const isAuthor = profile?.id === message.author.id;

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        borderRadius: 2,
        borderLeft: 4,
        borderLeftColor: `${status.color}.main`,
      }}
    >
      <Stack direction="row" spacing={1.5}>
        <Author author={message.author} size={36} />
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Stack
            direction="row"
            spacing={1}
            sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}
          >
            <Signature author={message.author} at={message.created_at} />
            <Chip size="small" variant="outlined" icon={icon} label={label} />
            <Box sx={{ flexGrow: 1 }} />
            {message.assignee && (
              <Tooltip title={`Assigned to ${nameOf(message.assignee)}`}>
                <Box sx={{ display: "inline-flex" }}>
                  <Author author={message.assignee} size={24} noTooltip />
                </Box>
              </Tooltip>
            )}
            <Chip size="small" {...status} />
          </Stack>
          <Typography variant="body2" sx={{ mt: 0.75, whiteSpace: "pre-wrap" }}>
            {message.text}
          </Typography>
          <PullRequests message={message} isAdmin={isAdmin} />
          {(message.replies ?? []).map((reply) => (
            <Stack
              key={reply.id}
              direction="row"
              spacing={1.5}
              sx={{
                mt: 1.5,
                p: 1.5,
                borderRadius: 2,
                bgcolor: (theme) =>
                  reply.author.id === message.author.id
                    ? theme.palette.action.hover
                    : alpha(
                        theme.palette.primary.main,
                        theme.palette.mode === "dark" ? 0.12 : 0.06,
                      ),
              }}
            >
              <Author author={reply.author} size={28} />
              <Box sx={{ minWidth: 0 }}>
                <Stack
                  direction="row"
                  spacing={1}
                  sx={{ alignItems: "center" }}
                >
                  <Signature author={reply.author} at={reply.created_at} />
                </Stack>
                <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                  {reply.text}
                </Typography>
              </Box>
            </Stack>
          ))}
          {replying && (
            <Stack spacing={1} sx={{ mt: 1.5 }}>
              <TextSend
                label="Reply"
                placeholder={
                  isAuthor
                    ? "Reply to the admins"
                    : `Reply to ${message.author.username}`
                }
                minRows={2}
                loading={isLoading}
                onSend={async (text) => {
                  await replyToFeedback({ id: message.id, text }).unwrap();
                  setReplying(false);
                }}
              />
            </Stack>
          )}
          {linking && (
            <LinkPullRequest
              message={message}
              onDone={() => setLinking(false)}
            />
          )}
          {(isAdmin || isAuthor) && (
            <Stack
              direction="row"
              spacing={1}
              sx={{ mt: 1, justifyContent: "flex-end" }}
            >
              <Button
                size="small"
                endIcon={<ReplyIcon />}
                onClick={() => setReplying(!replying)}
              >
                {replying ? "Cancel" : "Reply"}
              </Button>
              {isAdmin && (
                <>
                  <Button
                    size="small"
                    endIcon={<AddLinkIcon />}
                    onClick={() => setLinking(!linking)}
                  >
                    {linking ? "Cancel" : "Link PR"}
                  </Button>
                  <AssignButton message={message} />
                  <Button
                    size="small"
                    endIcon={message.resolved ? <UndoIcon /> : <DoneIcon />}
                    onClick={() =>
                      updateFeedback({
                        id: message.id,
                        resolved: !message.resolved,
                      })
                    }
                  >
                    {message.resolved ? "Reopen" : "Mark as resolved"}
                  </Button>
                </>
              )}
            </Stack>
          )}
        </Box>
      </Stack>
    </Paper>
  );
};

const RANK: Record<Status, number> = { open: 0, answered: 1, resolved: 2 };

const MessageList = ({
  messages,
  isAdmin,
}: {
  messages: Feedback[];
  isAdmin: boolean;
}) => {
  const [filter, setFilter] = useState<Status | "all">("all");
  const count = (status: Status) =>
    messages.filter((message) => statusOf(message) === status).length;
  const shown = messages
    .filter((message) => filter === "all" || statusOf(message) === filter)
    .sort((a, b) => RANK[statusOf(a)] - RANK[statusOf(b)]);

  return (
    <Stack spacing={1.5}>
      <Stack
        direction="row"
        sx={{ alignItems: "center", flexWrap: "wrap", gap: 1 }}
      >
        <Typography sx={{ fontWeight: 600, flexGrow: 1 }}>
          {isAdmin ? "Messages from users" : "Your messages"}
        </Typography>
        {messages.length > 0 && (
          <ToggleButtonGroup
            exclusive
            size="small"
            value={filter}
            onChange={(_, value) => value && setFilter(value)}
            sx={TOGGLES_SX}
          >
            <ToggleButton value="all">All ({messages.length})</ToggleButton>
            {(Object.keys(STATUSES) as Status[]).map((status) => (
              <ToggleButton key={status} value={status}>
                {STATUSES[status].label} ({count(status)})
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        )}
      </Stack>
      {shown.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {messages.length ? "No message with this status." : "No message yet."}
        </Typography>
      ) : (
        shown.map((message) => (
          <Message key={message.id} message={message} isAdmin={isAdmin} />
        ))
      )}
    </Stack>
  );
};

const FeedbackPage = () => {
  const isAdmin = useHasPermission("System admin");
  const { data: messages = [] } = useGetFeedbackQuery();

  return (
    <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 }, borderRadius: 2 }}>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          Feedback
        </Typography>
        <FeedbackForm />
        <MessageList messages={messages} isAdmin={isAdmin} />
      </Stack>
    </Paper>
  );
};

export default FeedbackPage;
