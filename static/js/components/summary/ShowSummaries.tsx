import ReactMarkdown from "react-markdown";

import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import Tooltip from "@mui/material/Tooltip";

import { rehypeEmoji } from "../comment/rehypeEmoji";

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

export const latestSummary = (
  summaries: Summary[] | null | undefined,
  showAISummaries = true,
) => {
  const latest = (summaries ?? []).find(
    (summary) => showAISummaries || summary?.is_bot === false,
  )?.summary;
  return latest?.trim() ? latest : null;
};

interface ShowSummariesProps {
  summaries?: Summary[];
  showAISummaries?: boolean;
}

const ShowSummaries = ({
  summaries = [],
  showAISummaries = true,
}: ShowSummariesProps) => {
  const { classes: styles } = useStyles();
  return (
    <div className={(styles as any).compactContainer}>
      <Tooltip title="Latest Summary" placement="right-start">
        <div className={styles.compactWrap}>
          <ReactMarkdown
            rehypePlugins={[rehypeEmoji]}
            className={styles.compactText}
          >
            {latestSummary(summaries, showAISummaries)}
          </ReactMarkdown>
        </div>
      </Tooltip>
    </div>
  );
};

export default ShowSummaries;
