import { Fragment, KeyboardEvent, useEffect, useRef, useState } from "react";

import { keyframes } from "@emotion/react";
import SendIcon from "@mui/icons-material/Send";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import { alpha } from "@mui/material/styles";
import { makeStyles } from "tss-react/mui";

import ReactMarkdown from "react-markdown";

import type { CommentTarget } from "../../contexts/CommentPanelContext";
import {
  useAskAssistantMutation,
  useGetAssistantConversationQuery,
} from "../../ducks/assistant";

const spin = keyframes({
  to: { transform: "rotate(360deg)" },
});

const useStyles = makeStyles()((theme) => ({
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    minHeight: 0,
  },
  list: {
    flexGrow: 1,
    minHeight: 0,
    overflowY: "auto",
    padding: "0.5rem 0.5rem 0",
  },
  message: {
    fontSize: "90%",
    borderRadius: "1rem",
    padding: "0.3125rem 0.75rem",
    marginBottom: "0.5rem",
    "& > p": {
      margin: 0,
    },
    "& p + p": {
      marginTop: "0.4em",
    },
    wordWrap: "break-word",
  },
  question: {
    width: "fit-content",
    maxWidth: "85%",
    marginLeft: "auto",
    backgroundColor: alpha(theme.palette.text.primary, 0.05),
  },
  answer: {
    marginRight: "1rem",
  },
  label: {
    fontSize: "0.7rem",
    marginLeft: "0.75rem",
    color: alpha(theme.palette.text.primary, 0.3),
  },
  aside: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "0.4rem",
    padding: "0.5rem",
    textAlign: "center",
    fontSize: "0.75rem",
    fontStyle: "italic",
    color: theme.palette.text.secondary,
  },
  spinner: {
    width: "0.9rem",
    height: "0.9rem",
    animation: `${spin} 1.2s linear infinite`,
  },
  composer: {
    display: "flex",
    alignItems: "flex-end",
    gap: "0.25rem",
    padding: theme.spacing(1, 1, 1.5),
  },
}));

interface AssistantThreadProps {
  channel: string | null;
  target: CommentTarget | null;
}

const AssistantThread = ({ channel, target }: AssistantThreadProps) => {
  const { classes, cx, theme } = useStyles();
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
    <div className={classes.container}>
      <div ref={listRef} className={classes.list}>
        {messages.length === 0 && (
          <div className={classes.aside}>
            {target
              ? `Ask anything. The assistant knows you are on ${
                  target.type === "source" ? target.id : "this GCN event"
                }.`
              : "Ask anything."}
          </div>
        )}
        {messages.map((message) => (
          <Fragment key={message.id}>
            {message.system && <div className={classes.label}>Assistant</div>}
            <ReactMarkdown
              className={cx(
                classes.message,
                message.system ? classes.answer : classes.question,
              )}
            >
              {message.text}
            </ReactMarkdown>
          </Fragment>
        ))}
        {!answered && (
          <div className={classes.aside}>
            <img
              className={classes.spinner}
              src={`/static/images/skyportal_logo${
                theme.palette.mode === "dark" ? "_dark" : ""
              }.png`}
              alt=""
            />
            Thinking...
          </div>
        )}
      </div>
      <div className={classes.composer}>
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
      </div>
    </div>
  );
};

export default AssistantThread;
