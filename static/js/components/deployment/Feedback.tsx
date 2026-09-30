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

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import NotificationToggle from "./NotificationToggle";
import { useAppDispatch } from "../../types/hooks";
import {
  useAddFeedbackMutation,
  useGetFeedbackQuery,
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

const FeedbackForm = ({ title }: { title: string }) => {
  const [category, setCategory] = useState<FeedbackCategory>("bug");
  const [text, setText] = useState("");
  const [addFeedback, { isLoading }] = useAddFeedbackMutation();
  const dispatch = useAppDispatch();

  const send = async () => {
    await addFeedback({ category, text }).unwrap();
    setText("");
    dispatch(showNotification("Thanks, your message was sent to the admins"));
  };

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
      <TextField
        label="Message"
        placeholder="What happened, or what would you like to change?"
        multiline
        minRows={4}
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <Box>
        <Button
          async
          loading={isLoading}
          disabled={!text.trim()}
          onClick={send}
          endIcon={<SendIcon />}
        >
          Send
        </Button>
      </Box>
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
  const [updateFeedback] = useUpdateFeedbackMutation();
  const { label, icon } = CATEGORIES[message.category];
  const created = dayjs.utc(message.created_at);

  return (
    <Box sx={{ py: 1.5, opacity: message.resolved ? 0.6 : 1 }}>
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
        <Tooltip title={created.local().format("MMM D, YYYY HH:mm")}>
          <Typography variant="caption" color="text.secondary">
            {created.fromNow()}
          </Typography>
        </Tooltip>
        <Box sx={{ flexGrow: 1 }} />
        {isAdmin ? (
          <Button
            size="small"
            onClick={() =>
              updateFeedback({ id: message.id, resolved: !message.resolved })
            }
          >
            {message.resolved ? "Reopen" : "Mark as resolved"}
          </Button>
        ) : (
          <Chip
            size="small"
            variant="outlined"
            label={message.resolved ? "Resolved" : "Open"}
            color={message.resolved ? "success" : "default"}
          />
        )}
      </Stack>
      <Typography variant="body2" sx={{ mt: 1, whiteSpace: "pre-wrap" }}>
        {message.text}
      </Typography>
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
      {isAdmin && (
        <Box>
          <NotificationToggle type="feedback" label="Also by email or Slack">
            As an admin, you get an in-app notification for every new message.
          </NotificationToggle>
        </Box>
      )}
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
