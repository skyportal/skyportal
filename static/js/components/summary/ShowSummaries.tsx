import React from "react";
import ReactMarkdown from "react-markdown";

import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";
import Tooltip from "@mui/material/Tooltip";

dayjs.extend(relativeTime);
dayjs.extend(utc);

export const useStyles = makeStyles()((theme) => ({
  commentsContainer: {
    width: "100%",
  },
  chip: {
    margin: theme.spacing(0.5),
  },
  compactWrap: {
    fontSize: "75%",
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    width: "100%",
    padding: "0 5px",
  },
  compactText: {
    "& p": {
      padding: 0,
      margin: 0,
    },
  },
}));

interface Summary {
  summary?: string | null;
  is_bot?: boolean;
}

interface ShowSummariesProps {
  summaries?: Summary[];
  showAISummaries?: boolean;
}

const ShowSummaries = ({
  summaries = [],
  showAISummaries = true,
}: ShowSummariesProps) => {
  const { classes: styles } = useStyles();
  const renderCommentText = () => {
    let filteredSummaries = [...(summaries || [])].filter(
      (summary) =>
        summary?.summary &&
        summary?.summary !== null &&
        summary?.summary.trim() !== "",
    );
    if (showAISummaries === false) {
      filteredSummaries = filteredSummaries.filter(
        (summary) => summary?.is_bot === false,
      );
    }
    if (filteredSummaries?.length > 0) {
      return filteredSummaries[0].summary;
    }
    return null;
  };

  const emojiSupport = (textComment: any) =>
    textComment.value.replace(/:\w+:/gi, (name: string) =>
      emoji.getUnicode(name) ? emoji.getUnicode(name) : name,
    );

  return (
    <div className={(styles as any).compactContainer}>
      <Tooltip title="Latest Summary" placement="right-start">
        <div className={styles.compactWrap}>
          <ReactMarkdown
            components={{ text: emojiSupport } as any}
            className={styles.compactText}
          >
            {renderCommentText()}
          </ReactMarkdown>
        </div>
      </Tooltip>
    </div>
  );
};

export default ShowSummaries;
