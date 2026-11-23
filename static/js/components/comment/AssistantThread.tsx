import { KeyboardEvent, useEffect, useRef, useState } from "react";

import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import InputBase from "@mui/material/InputBase";
import Popover from "@mui/material/Popover";
import Tooltip from "@mui/material/Tooltip";
import { alpha, useTheme } from "@mui/material/styles";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { CommentTarget } from "../../contexts/CommentPanelContext";
import {
  AssistantUsage,
  useAskAssistantMutation,
  useGetAssistantConversationQuery,
  useGetAssistantUsageQuery,
} from "../../ducks/assistant";
import AssistantFilterProposal from "./AssistantFilterProposal";
import AssistantToolTrace from "./AssistantToolTrace";
import { markdownSx } from "./assistantStyles";

const MAIN_COLOR = "#6f58b8";
const FALLBACK_COLOR = "#ab873f";

const pillSx = {
  fontSize: "0.7rem",
  fontWeight: 600,
  lineHeight: 1.7,
  borderRadius: "999px",
  padding: "0 0.5rem",
  whiteSpace: "nowrap",
} as const;

const labelSx = {
  display: "flex",
  alignItems: "center",
  gap: "0.35rem",
  marginBottom: "0.3rem",
  fontSize: "0.75rem",
  fontWeight: 600,
  color: "text.secondary",
} as const;

const SUGGESTIONS: Record<CommentTarget["type"] | "none", string[]> = {
  source: ["Summarize this source", "Describe its light curve"],
  filter: ["Explain this filter", "How many alerts pass it?"],
  gcn_event: ["Summarize this event", "Best candidates so far"],
  none: ["What can you do?", "My latest saved sources"],
};

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
  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.4rem",
        paddingTop: "0.5rem",
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
            anchorOrigin={{ vertical: "top", horizontal: "center" }}
            transformOrigin={{ vertical: "bottom", horizontal: "center" }}
            slotProps={{ paper: { sx: { borderRadius: "10px" } } }}
          >
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: "0.4rem",
                padding: "0.6rem 0.8rem",
                fontSize: "0.75rem",
              }}
            >
              <span>{100 - left}% of this month’s budget used.</span>
              {usage.fallback && (
                <Box
                  component="span"
                  sx={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.3rem",
                  }}
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
          </Popover>
        </>
      ) : null}
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

  const ask = (prompt?: string) => {
    const text = (prompt ?? question).trim();
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

  const targetLabel = !target
    ? null
    : target.type === "source"
      ? target.id
      : target.type === "filter"
        ? "this filter"
        : "this GCN event";

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
          display: "flex",
          flexDirection: "column",
          gap: "1.25rem",
          flexGrow: 1,
          minHeight: 0,
          overflowY: "auto",
          padding: "1rem 1rem 0.5rem",
        }}
      >
        {messages.length === 0 && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.5rem",
              flexGrow: 1,
              textAlign: "center",
            }}
          >
            <Box sx={{ fontSize: "1.15rem", fontWeight: 600 }}>
              How can I help?
            </Box>
            {targetLabel && (
              <Box sx={{ fontSize: "0.8rem", color: "text.secondary" }}>
                I can see you are on {targetLabel}.
              </Box>
            )}
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "center",
                gap: "0.4rem",
                marginTop: "0.75rem",
              }}
            >
              {SUGGESTIONS[target?.type ?? "none"].map((suggestion) => (
                <Box
                  key={suggestion}
                  component="button"
                  type="button"
                  onClick={() => ask(suggestion)}
                  sx={{
                    padding: "0.35rem 0.8rem",
                    borderRadius: "999px",
                    border: 1,
                    borderColor: "divider",
                    backgroundColor: "transparent",
                    font: "inherit",
                    fontSize: "0.8rem",
                    color: "text.primary",
                    cursor: "pointer",
                    transition: "background-color 150ms",
                    "&:hover": {
                      backgroundColor: alpha(theme.palette.text.primary, 0.05),
                    },
                  }}
                >
                  {suggestion}
                </Box>
              ))}
            </Box>
          </Box>
        )}
        {messages.map((message) =>
          message.system ? (
            <Box key={message.id}>
              <Box sx={labelSx}>
                Assistant
                {message.model && (
                  <ModelDot model={message.model} main={usage?.model} />
                )}
              </Box>
              <AssistantToolTrace calls={message.tool_calls ?? []} />
              <Box sx={markdownSx}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.text}
                </ReactMarkdown>
              </Box>
              {message.proposal && (
                <AssistantFilterProposal proposal={message.proposal} />
              )}
            </Box>
          ) : (
            <Box
              key={message.id}
              sx={(t) => ({
                ...markdownSx(t),
                alignSelf: "flex-end",
                maxWidth: "85%",
                padding: "0.5rem 0.875rem",
                borderRadius: "18px 18px 4px 18px",
                backgroundColor: alpha(
                  t.palette.primary.main,
                  t.palette.mode === "dark" ? 0.3 : 0.12,
                ),
              })}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.text}
              </ReactMarkdown>
            </Box>
          ),
        )}
        {!answered && (
          <Box>
            <Box sx={labelSx}>Assistant</Box>
            <Box
              sx={{
                width: "fit-content",
                fontSize: "0.875rem",
                color: "transparent",
                backgroundImage: `linear-gradient(90deg, ${theme.palette.text.secondary} 35%, ${theme.palette.text.primary} 50%, ${theme.palette.text.secondary} 65%)`,
                backgroundSize: "300% 100%",
                backgroundClip: "text",
                animation: "assistant-shimmer 1.8s linear infinite",
                "@keyframes assistant-shimmer": {
                  from: { backgroundPosition: "100% 0" },
                  to: { backgroundPosition: "0 0" },
                },
              }}
            >
              Thinking…
            </Box>
          </Box>
        )}
      </Box>
      <Box sx={{ padding: "0.5rem 0.75rem 0.75rem" }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "flex-end",
            gap: "0.5rem",
            padding: "0.375rem 0.375rem 0.375rem 0.875rem",
            borderRadius: "1.25rem",
            border: 1,
            borderColor: "divider",
            backgroundColor: "background.paper",
            transition: "border-color 150ms, box-shadow 150ms",
            "&:focus-within": {
              borderColor: "primary.main",
              boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.15)}`,
            },
          }}
        >
          <InputBase
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask anything"
            name="question"
            fullWidth
            multiline
            maxRows={6}
            sx={{ fontSize: "0.875rem", paddingY: "0.3rem" }}
          />
          <IconButton
            aria-label="Send"
            size="small"
            disabled={!question.trim()}
            onClick={() => ask()}
            sx={{
              flexShrink: 0,
              width: 32,
              height: 32,
              color: "primary.contrastText",
              backgroundColor: "primary.main",
              "&:hover": { backgroundColor: "primary.dark" },
              "&.Mui-disabled": {
                color: "text.disabled",
                backgroundColor: alpha(theme.palette.text.primary, 0.08),
              },
            }}
          >
            <ArrowUpwardIcon sx={{ fontSize: "1.1rem" }} />
          </IconButton>
        </Box>
        {usage?.model && <ModelBar usage={usage} />}
      </Box>
    </Box>
  );
};

export default AssistantThread;
