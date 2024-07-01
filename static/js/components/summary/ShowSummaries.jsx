import React from "react";
import ReactMarkdown from "react-markdown";

import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import emoji from "emoji-dictionary";
import Tooltip from "@mui/material/Tooltip";

dayjs.extend(relativeTime);
dayjs.extend(utc);

export const useStyles = makeStyles((theme) => ({
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

const ShowSummaries = ({ summaries = [], showAISummaries = true }) => {
  const styles = useStyles();
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

  const emojiSupport = (textComment) =>
    textComment.value.replace(/:\w+:/gi, (name) =>
      emoji.getUnicode(name) ? emoji.getUnicode(name) : name,
    );

  return (
    <div className={styles.compactContainer}>
      <Tooltip title="Latest Summary" placement="right-start">
        <div className={styles.compactWrap}>
          <ReactMarkdown
            components={{ text: emojiSupport }}
            className={styles.compactText}
          >
            {renderCommentText()}
          </ReactMarkdown>
        </div>
      </Tooltip>
    </div>
  );
};

ShowSummaries.propTypes = {
  summaries: PropTypes.arrayOf(
    PropTypes.shape({
      summary: PropTypes.string,
      is_bot: PropTypes.bool,
    }),
  ),
  showAISummaries: PropTypes.bool,
};

ShowSummaries.defaultProps = {
  summaries: [],
  showAISummaries: true,
};

export default ShowSummaries;
