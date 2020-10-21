import React, { useState } from "react";
import PropTypes from "prop-types";
import HistoryIcon from "@material-ui/icons/History";
import Dialog from "@material-ui/core/Dialog";
import Tooltip from "@material-ui/core/Tooltip";
import IconButton from "@material-ui/core/IconButton";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import { makeStyles } from "@material-ui/core/styles";
import Table from "@material-ui/core/Table";
import TableBody from "@material-ui/core/TableBody";
import TableCell from "@material-ui/core/TableCell";
import TableHead from "@material-ui/core/TableHead";
import TableRow from "@material-ui/core/TableRow";

const useStyles = makeStyles(() => ({
  historyIcon: {
    display: "inline-block",
  },
  iconButton: {
    display: "inline-block",
  },
}));

const SourceSaveHistory = ({ groups }) => {
  const classes = useStyles();

  const [dialogOpen, setDialogOpen] = useState(false);

  // Sort history from newest to oldest
  const sortedHistory = groups?.sort((a, b) => {
    const dateA = new Date(a.saved_at);
    const dateB = new Date(b.saved_at);
    return dateB - dateA;
  });

  return (
    <>
      <Tooltip title="Source save history">
        <span>
          <IconButton
            aria-label="source-save-history"
            data-testid="save_history"
            onClick={() => {
              setDialogOpen(true);
            }}
            size="small"
            className={classes.iconButton}
          >
            <HistoryIcon />
          </IconButton>
        </span>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Save History</DialogTitle>
        <DialogContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Group Name</TableCell>
                <TableCell>Saved By</TableCell>
                <TableCell>Time (UTC)</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedHistory &&
                sortedHistory.map((historyItem) => (
                  <TableRow key={historyItem.saved_at}>
                    <TableCell>{historyItem.name}</TableCell>
                    <TableCell>{historyItem.saved_by.username}</TableCell>
                    <TableCell>{historyItem.saved_at}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </DialogContent>
      </Dialog>
    </>
  );
};

SourceSaveHistory.propTypes = {
  groups: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      saved_at: PropTypes.string,
      saved_by: PropTypes.shape({
        username: PropTypes.string,
      }),
    })
  ).isRequired,
};

export default SourceSaveHistory;
