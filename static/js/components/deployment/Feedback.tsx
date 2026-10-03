import { ReactElement, useState } from "react";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import { alpha } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
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

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import UserAvatar, { getUserRealName } from "../user/UserAvatar";
import NotificationToggle from "./NotificationToggle";
import { useAppDispatch } from "../../types/hooks";
import {
  useAddFeedbackMutation,
  useGetFeedbackQuery,
  useReplyToFeedbackMutation,
  useUpdateFeedbackMutation,
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

const statusOf = (message: Feedback): Status =>
  message.resolved ? "resolved" : message.replies?.length ? "answered" : "open";

const Author = ({
  author,
  size,
}: {
  author: Feedback["author"];
  size: number;
}) => (
  <UserAvatar
    size={size}
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
      {getUserRealName(author.first_name, author.last_name) || author.username}
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
}: {
  label: string;
  placeholder: string;
  minRows: number;
  loading: boolean;
  onSend: (text: string) => Promise<unknown>;
}) => {
  const [text, setText] = useState("");
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

const FeedbackForm = ({ title }: { title: string }) => {
  const [category, setCategory] = useState<FeedbackCategory>("bug");
  const [addFeedback, { isLoading }] = useAddFeedbackMutation();
  const dispatch = useAppDispatch();

  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        Found a bug, or want something to change? Leave a message to the admins
        of {title}.
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
        onSend={async (text) => {
          await addFeedback({ category, text }).unwrap();
          dispatch(
            showNotification("Thanks, your message was sent to the admins"),
          );
        }}
      />
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
  const [updateFeedback] = useUpdateFeedbackMutation();
  const [replyToFeedback, { isLoading }] = useReplyToFeedbackMutation();
  const { label, icon } = CATEGORIES[message.category];
  const status = STATUSES[statusOf(message)];

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
            <Chip size="small" {...status} />
          </Stack>
          <Typography variant="body2" sx={{ mt: 0.75, whiteSpace: "pre-wrap" }}>
            {message.text}
          </Typography>
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
                  alpha(
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
                placeholder={`Reply to ${message.author.username}`}
                minRows={2}
                loading={isLoading}
                onSend={async (text) => {
                  await replyToFeedback({ id: message.id, text }).unwrap();
                  setReplying(false);
                }}
              />
            </Stack>
          )}
          {isAdmin && (
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

const FeedbackTab = ({
  title,
  isAdmin,
}: {
  title: string;
  isAdmin: boolean;
}) => {
  const { data: messages = [] } = useGetFeedbackQuery();

  return (
    <Stack spacing={3}>
      <FeedbackForm title={title} />
      <Box>
        <NotificationToggle type="feedback" label="Also by email or Slack">
          {isAdmin
            ? "As an admin, you get an in-app notification for every new message."
            : "You get an in-app notification when an admin replies to one of your messages."}
        </NotificationToggle>
      </Box>
      <MessageList messages={messages} isAdmin={isAdmin} />
    </Stack>
  );
};

export default FeedbackTab;
