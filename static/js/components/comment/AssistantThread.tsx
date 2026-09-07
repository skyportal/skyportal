import { Fragment, KeyboardEvent, useEffect, useRef, useState } from "react";

import SendIcon from "@mui/icons-material/Send";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import { alpha, useTheme } from "@mui/material/styles";

import ReactMarkdown from "react-markdown";

import type { CommentTarget } from "../../contexts/CommentPanelContext";
import {
  useAskAssistantMutation,
  useGetAssistantConversationQuery,
} from "../../ducks/assistant";

const messageSx = {
  fontSize: "90%",
  borderRadius: "1rem",
  padding: "0.3125rem 0.75rem",
  marginBottom: "0.5rem",
  wordWrap: "break-word",
  "& > p": { margin: 0 },
  "& p + p": { marginTop: "0.4em" },
} as const;

const asideSx = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "0.4rem",
  padding: "0.5rem",
  textAlign: "center",
  fontSize: "0.75rem",
  fontStyle: "italic",
  color: "text.secondary",
} as const;

interface AssistantThreadProps {
  channel: string | null;
  target: CommentTarget | null;
}

const AssistantThread = ({ channel, target }: AssistantThreadProps) => {
  const theme = useTheme();
  const { data: messages = [] } = useGetAssistantConversationQuery(channel);
  const [askAssistant] = useAskAssistantMutation();
  const [question, setQuestion] = useState("");
  const listRef = useRef<HTMLDivElement | null>(null);

  const answered = messages[messages.length - 1]?.system ?? true;

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [channel, messages.length]);

  const ask = () => {
    const text = question.trim();
    if (!text) return;
    setQuestion("");
    askAssistant({
      text,
      channel,
      ...(target
        ? { context_type: target.type, context_id: String(target.id) }
        : {}),
    });
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      ask();
    }
  };

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
        ref={listRef}
        sx={{
          flexGrow: 1,
          minHeight: 0,
          overflowY: "auto",
          padding: "0.5rem 0.5rem 0",
        }}
      >
        {messages.length === 0 && (
          <Box sx={asideSx}>
            {target
              ? `Ask anything. The assistant knows you are on ${
                  target.type === "source" ? target.id : "this GCN event"
                }.`
              : "Ask anything."}
          </Box>
        )}
        {messages.map((message) => (
          <Fragment key={message.id}>
            {message.system && (
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem",
                  fontSize: "0.7rem",
                  marginLeft: "0.75rem",
                  color: alpha(theme.palette.text.primary, 0.3),
                }}
              >
                <SmartToyIcon sx={{ fontSize: "0.9rem" }} />
                Assistant
              </Box>
            )}
            <Box
              sx={{
                ...messageSx,
                ...(message.system
                  ? { marginRight: "1rem" }
                  : {
                      width: "fit-content",
                      maxWidth: "85%",
                      marginLeft: "auto",
                      backgroundColor: alpha(theme.palette.text.primary, 0.05),
                    }),
              }}
            >
              <ReactMarkdown>{message.text}</ReactMarkdown>
            </Box>
          </Fragment>
        ))}
        {!answered && (
          <Box sx={asideSx}>
            <Box
              component="img"
              src={`/static/images/skyportal_logo${
                theme.palette.mode === "dark" ? "_dark" : ""
              }.png`}
              alt=""
              sx={{
                width: "0.9rem",
                height: "0.9rem",
                animation: "assistant-spin 1.2s linear infinite",
                "@keyframes assistant-spin": {
                  to: { transform: "rotate(360deg)" },
                },
              }}
            />
            Thinking...
          </Box>
        )}
      </Box>
      <Box
        sx={{
          display: "flex",
          alignItems: "flex-end",
          gap: "0.25rem",
          padding: theme.spacing(1, 1, 1.5),
        }}
      >
        <TextField
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask the assistant"
          name="question"
          size="small"
          fullWidth
          multiline
          maxRows={4}
        />
        <IconButton
          color="primary"
          size="small"
          disabled={!question.trim()}
          onClick={ask}
        >
          <SendIcon fontSize="small" />
        </IconButton>
      </Box>
    </Box>
  );
};

export default AssistantThread;
