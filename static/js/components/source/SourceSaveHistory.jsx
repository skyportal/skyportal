import React, { useState } from "react";
import PropTypes from "prop-types";
import HistoryIcon from "@mui/icons-material/History";
import Dialog from "@mui/material/Dialog";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import makeStyles from "@mui/styles/makeStyles";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";

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
    <div className={classes.historyIcon}>
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
            <HistoryIcon style={{ fontSize: "1rem" }} />
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
                    <TableCell>{historyItem.saved_by?.username}</TableCell>
                    <TableCell>{historyItem.saved_at}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </DialogContent>
      </Dialog>
    </div>
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
    }),
  ).isRequired,
};

export default SourceSaveHistory;
