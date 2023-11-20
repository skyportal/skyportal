import React from "react";
import ReactMarkdown from "react-markdown";

import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Paper from "@mui/material/Paper";
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
}));

const ShowSummaries = ({ summaries = [] }) => {
  const styles = useStyles();
  const renderCommentText = () => {
    if (summaries?.length > 0) {
      return summaries[0].summary;
    }
    return null;
  };

  const emojiSupport = (textComment) =>
    textComment.value.replace(/:\w+:/gi, (name) =>
      emoji.getUnicode(name) ? emoji.getUnicode(name) : name
    );

  return (
    <Paper elevation={1}>
      <div className={styles.compactContainer}>
        <Tooltip title="Latest Summary" placement="right-start">
          <div className={styles.compactWrap}>
            <ReactMarkdown components={{ text: emojiSupport }}>
              {renderCommentText()}
            </ReactMarkdown>
          </div>
        </Tooltip>
      </div>
    </Paper>
  );
};

ShowSummaries.propTypes = {
  summaries: PropTypes.arrayOf(PropTypes.string),
};

ShowSummaries.defaultProps = {
  summaries: [],
};

export default ShowSummaries;
