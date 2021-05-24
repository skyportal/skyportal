import React, { useState } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import HistoryIcon from "@material-ui/icons/History";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import { makeStyles } from "@material-ui/core/styles";
import Table from "@material-ui/core/Table";
import TableBody from "@material-ui/core/TableBody";
import TableCell from "@material-ui/core/TableCell";
import TableHead from "@material-ui/core/TableHead";
import TableRow from "@material-ui/core/TableRow";

const useStyles = makeStyles(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  historyIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
}));

const SourceRedshiftHistory = ({ redshiftHistory }) => {
  const classes = useStyles();
  const { users: allUsers } = useSelector((state) => state.users);
  const userIdToUsername = {};

  const [dialogOpen, setDialogOpen] = useState(false);

  // Sort history from newest to oldest
  const sortedHistory = redshiftHistory?.sort((a, b) => {
    const dateA = new Date(a.set_at_utc);
    const dateB = new Date(b.set_at_utc);
    return dateB - dateA;
  });

  if (allUsers.length) {
    allUsers.forEach((user) => {
      userIdToUsername[user.id] = user.username;
    });
  }

  return (
    <>
      <HistoryIcon
        data-testid="redshiftHistoryIconButton"
        fontSize="small"
        className={classes.historyIcon}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Redshift History</DialogTitle>
        <DialogContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Set By</TableCell>
                <TableCell>Time (UTC)</TableCell>
                <TableCell>Value</TableCell>
                <TableCell>Uncertainty</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedHistory &&
                allUsers.length &&
                redshiftHistory.map((historyItem) => (
                  <TableRow key={historyItem.set_at_utc}>
                    <TableCell>
                      {userIdToUsername[historyItem.set_by_user_id]}
                    </TableCell>
                    <TableCell>{historyItem.set_at_utc}</TableCell>
                    <TableCell>{historyItem.value}</TableCell>
                    <TableCell>{historyItem.uncertainty}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </DialogContent>
      </Dialog>
    </>
  );
};

SourceRedshiftHistory.propTypes = {
  redshiftHistory: PropTypes.arrayOf(PropTypes.shape({})),
};
SourceRedshiftHistory.defaultProps = {
  redshiftHistory: null,
};

export default SourceRedshiftHistory;
