import { useState } from "react";
import HistoryIcon from "@mui/icons-material/History";
import Dialog from "@mui/material/Dialog";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { makeStyles } from "tss-react/mui";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";

import { Group } from "../../types/domain";

const useStyles = makeStyles()(() => ({
  historyIcon: {
    display: "inline-block",
  },
  iconButton: {
    display: "inline-block",
  },
}));

interface SourceSaveHistoryProps {
  groups: Group[];
}

const SourceSaveHistory = ({ groups }: SourceSaveHistoryProps) => {
  const { classes } = useStyles();

  const [dialogOpen, setDialogOpen] = useState(false);

  // Sort history from newest to oldest
  const sortedHistory = groups?.sort((a, b) => {
    const dateA = new Date(a.saved_at as string);
    const dateB = new Date(b.saved_at as string);
    return dateB.getTime() - dateA.getTime();
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
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
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

export default SourceSaveHistory;
