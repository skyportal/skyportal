import React, { useState } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import HistoryIcon from "@mui/icons-material/History";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import { Link } from "react-router-dom";
import Tooltip from "@mui/material/Tooltip";
import Button from "../Button";

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  historyIcon: {
    height: "1rem",
    cursor: "pointer",
  },
  infoButton: {
    paddingRight: "0.5rem",
  },
}));

const ShowSummaryHistory = ({ obj_id, summaries = [], button = false }) => {
  const classes = useStyles();
  const { users: allUsers } = useSelector((state) => state.users);
  const userIdToUsername = {};

  const [dialogOpen, setDialogOpen] = useState(false);

  // Sort history from newest to oldest
  const sortedHistory = summaries?.sort((a, b) => {
    const dateA = new Date(a.set_at_utc);
    const dateB = new Date(b.set_at_utc);
    return dateB - dateA;
  });

  if (allUsers.length) {
    allUsers?.forEach((user) => {
      userIdToUsername[user.id] = user.username;
    });
  }

  return (
    <>
      {button ? (
        <Tooltip title="Show history of object summaries">
          <Button
            secondary
            size="small"
            onClick={() => {
              setDialogOpen(true);
            }}
          >
            Summaries
          </Button>
        </Tooltip>
      ) : (
        <Tooltip title="Show history of object summaries">
          <span>
            <HistoryIcon
              data-testid="summaryHistoryIconButton"
              fontSize="small"
              className={classes.historyIcon}
              onClick={() => {
                setDialogOpen(true);
              }}
            />
          </span>
        </Tooltip>
      )}
      <Dialog
        open={dialogOpen}
        fullWidth
        maxWidth="lg"
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Summary History for {obj_id}</DialogTitle>
        <DialogContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Summary</TableCell>
                <TableCell>Set By</TableCell>
                <TableCell>Time (UTC)</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedHistory &&
                allUsers.length &&
                summaries.map((historyItem) => (
                  <TableRow key={historyItem.set_at_utc}>
                    <TableCell>{historyItem.summary}</TableCell>
                    <TableCell>
                      {historyItem.is_bot &&
                      typeof historyItem.analysis_id === "number" ? (
                        <div className={classes.infoButton}>
                          <Tooltip
                            title="Link to analysis page"
                            placement="top"
                          >
                            <Link
                              to={`/source/${obj_id}/analysis/${historyItem.analysis_id}`}
                              role="link"
                            >
                              <Button primary size="small">
                                <SmartToyIcon fontSize="small" />
                              </Button>
                            </Link>
                          </Tooltip>
                        </div>
                      ) : null}
                      {userIdToUsername[historyItem.set_by_user_id]}
                    </TableCell>
                    <TableCell>{historyItem.set_at_utc}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </DialogContent>
      </Dialog>
    </>
  );
};

ShowSummaryHistory.propTypes = {
  obj_id: PropTypes.string,
  summaries: PropTypes.arrayOf(PropTypes.shape({})),
  button: PropTypes.bool,
};
ShowSummaryHistory.defaultProps = {
  obj_id: null,
  summaries: null,
  button: false,
};

export default ShowSummaryHistory;
