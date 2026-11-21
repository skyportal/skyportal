import { Fragment, KeyboardEvent, useEffect, useRef, useState } from "react";

import SendIcon from "@mui/icons-material/Send";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import { alpha, useTheme } from "@mui/material/styles";

import ReactMarkdown from "react-markdown";

import type { CommentTarget } from "../../contexts/CommentPanelContext";
import {
  AssistantUsage,
  useAskAssistantMutation,
  useGetAssistantConversationQuery,
  useGetAssistantUsageQuery,
} from "../../ducks/assistant";
import AssistantFilterProposal from "./AssistantFilterProposal";
import AssistantToolTrace from "./AssistantToolTrace";

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

const MAIN_COLOR = "#6f58b8";
const FALLBACK_COLOR = "#ab873f";

const pillSx = {
  fontSize: "0.7rem",
  fontWeight: 600,
  lineHeight: 1.6,
  borderRadius: "4px",
  padding: "0 0.4rem",
  whiteSpace: "nowrap",
} as const;

interface ModelDotProps {
  model: string;
  main: string | null | undefined;
}

const ModelDot = ({ model, main }: ModelDotProps) => (
  <Tooltip
    title={model === main ? model : `${model} (fallback)`}
    placement="top"
    enterDelay={0}
    disableInteractive
  >
    <Box
      component="span"
      sx={{
        display: "inline-block",
        width: "0.4rem",
        height: "0.4rem",
        borderRadius: "50%",
        backgroundColor: model === main ? MAIN_COLOR : FALLBACK_COLOR,
      }}
    />
  </Tooltip>
);

const ModelBar = ({ usage }: { usage: AssistantUsage }) => {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const left = usage.left ?? 100;
  const level = left <= 10 ? "error" : left <= 25 ? "warning" : "success";
  const resets = usage.resets
    ? new Date(`${usage.resets}T00:00:00Z`).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      })
    : "";
  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "0.4rem",
        padding: "0 0.75rem 0.6rem",
        fontSize: "0.7rem",
        color: "text.secondary",
      }}
    >
      <Box
        component="span"
        sx={{
          ...pillSx,
          color: MAIN_COLOR,
          backgroundColor: alpha(MAIN_COLOR, 0.12),
        }}
      >
        {usage.model}
      </Box>
      {usage.limit ? (
        <>
          <Box
            component="button"
            type="button"
            onClick={(event) => setAnchor(event.currentTarget)}
            sx={{
              ...pillSx,
              border: 0,
              cursor: "pointer",
              color: `${level}.main`,
              backgroundColor: (theme) =>
                alpha(theme.palette[level].main, 0.12),
            }}
          >
            {left}% of this month’s budget left
          </Box>
          <Popover
            open={Boolean(anchor)}
            anchorEl={anchor}
            onClose={() => setAnchor(null)}
            anchorOrigin={{ vertical: "top", horizontal: "left" }}
            transformOrigin={{ vertical: "bottom", horizontal: "left" }}
          >
            <Box
              sx={{
                padding: "0.6rem 0.8rem",
                maxWidth: "17rem",
                fontSize: "0.75rem",
              }}
            >
              {usage.model} has ${usage.limit} a month shared by everyone, and $
              {usage.spent} of it is used ({100 - left}%), estimated from the
              tokens of each answer.{" "}
              {usage.fallback
                ? `When it runs out, the assistant answers with ${usage.fallback} until ${resets}.`
                : `When it runs out, the assistant stops answering until ${resets}.`}
            </Box>
          </Popover>
        </>
      ) : null}
      {usage.fallback && (
        <Box
          component="span"
          sx={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}
        >
          Next model if down or out of budget:
          <Box
            component="span"
            sx={{
              ...pillSx,
              color: FALLBACK_COLOR,
              backgroundColor: alpha(FALLBACK_COLOR, 0.12),
            }}
          >
            {usage.fallback}
          </Box>
        </Box>
      )}
    </Box>
  );
};

interface AssistantThreadProps {
  channel: string;
  target: CommentTarget | null;
}

const AssistantThread = ({ channel, target }: AssistantThreadProps) => {
  const theme = useTheme();
  const { data: messages = [] } = useGetAssistantConversationQuery(channel);
  const { data: usage } = useGetAssistantUsageQuery();
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
        ? {
            context_type: target.type,
            context_id:
              target.type === "filter"
                ? `${target.brokerId}/${target.id}`
                : String(target.id),
          }
        : {}),
    })
      .unwrap()
      .catch(() => setQuestion(text));
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
                  target.type === "source"
                    ? target.id
                    : target.type === "filter"
                      ? "this filter"
                      : "this GCN event"
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
                {message.model && (
                  <ModelDot model={message.model} main={usage?.model} />
                )}
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
            {message.system && (
              <AssistantToolTrace calls={message.tool_calls ?? []} />
            )}
            {message.system &&
              message.proposal &&
              target?.type === "filter" && (
                <AssistantFilterProposal proposal={message.proposal} />
              )}
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
      {usage?.model && <ModelBar usage={usage} />}
    </Box>
  );
};

export default AssistantThread;
