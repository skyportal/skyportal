import { Fragment, ReactElement, useState } from "react";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
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

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
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

const status = (message: Feedback) => {
  if (message.resolved)
    return {
      label: "Resolved",
      color: "success" as const,
      icon: <CheckCircleIcon />,
    };
  if (message.replies?.length)
    return {
      label: "Answered",
      color: "primary" as const,
      icon: <QuestionAnswerIcon />,
    };
  return { label: "Open", color: "warning" as const, icon: <ScheduleIcon /> };
};

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
  const replies = message.replies ?? [];

  return (
    <Box sx={{ py: 1.5 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
      >
        <Chip size="small" variant="outlined" icon={icon} label={label} />
        {isAdmin && (
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {message.author.username}
          </Typography>
        )}
        <Posted at={message.created_at} />
        <Box sx={{ flexGrow: 1 }} />
        <Chip size="small" {...status(message)} />
        {isAdmin && (
          <>
            <Button size="small" onClick={() => setReplying(!replying)}>
              Reply
            </Button>
            <Button
              size="small"
              onClick={() =>
                updateFeedback({ id: message.id, resolved: !message.resolved })
              }
            >
              {message.resolved ? "Reopen" : "Mark as resolved"}
            </Button>
          </>
        )}
      </Stack>
      <Typography variant="body2" sx={{ mt: 1, whiteSpace: "pre-wrap" }}>
        {message.text}
      </Typography>
      {(replies.length > 0 || replying) && (
        <Stack
          spacing={1.5}
          sx={{ mt: 1.5, ml: 1, pl: 2, borderLeft: 2, borderColor: "divider" }}
        >
          {replies.map((reply) => (
            <Box key={reply.id}>
              <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {reply.author.username}
                </Typography>
                <Posted at={reply.created_at} />
              </Stack>
              <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                {reply.text}
              </Typography>
            </Box>
          ))}
          {replying && (
            <Stack spacing={1}>
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
        </Stack>
      )}
    </Box>
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
  const sorted = [...messages].sort(
    (a, b) => Number(a.resolved) - Number(b.resolved),
  );

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
      <Box>
        <Typography sx={{ fontWeight: 600 }}>
          {isAdmin ? "Messages from users" : "Your messages"}
        </Typography>
        {sorted.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            No message yet.
          </Typography>
        ) : (
          sorted.map((message, index) => (
            <Fragment key={message.id}>
              {index > 0 && <Divider />}
              <Message message={message} isAdmin={isAdmin} />
            </Fragment>
          ))
        )}
      </Box>
    </Stack>
  );
};

export default FeedbackTab;
