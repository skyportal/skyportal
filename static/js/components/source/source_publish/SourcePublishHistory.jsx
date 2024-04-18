import React from "react";
import makeStyles from "@mui/styles/makeStyles";

const useStyles = makeStyles(() => ({
  versionHistory: {
    width: "100%",
  },
  versionHistoryLine: {
    border: "1px solid #e0e0e0",
    display: "flex",
    padding: "0.25rem 0.5rem",
    justifyContent: "space-between",
    borderRadius: "0.5rem",
    marginBottom: "0.5rem",
  },
}));

const SourcePublishHistory = () => {
  const styles = useStyles();
  // TODO: Add real data
  const publicSourceHistory = [1, 2, 3];
  return (
    <div className={styles.versionHistory}>
      {publicSourceHistory.map((history) => (
        // TODO add key
        <div
          className={styles.versionHistoryLine}
          key={`version_history_${history}`}
        >
          <div>09/10/20</div>
          <div>Lists</div>
          <div>link</div>
        </div>
      ))}
    </div>
  );
};

export default SourcePublishHistory;
