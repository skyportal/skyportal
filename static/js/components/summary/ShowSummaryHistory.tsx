import React, { useState } from "react";
import HistoryIcon from "@mui/icons-material/History";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { makeStyles } from "tss-react/mui";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import { Link } from "react-router-dom";
import Tooltip from "@mui/material/Tooltip";
import { useAppSelector } from "../../types/hooks";
import Button from "../Button";

const useStyles = makeStyles()(() => ({
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

interface SummaryHistoryItem {
  summary?: string;
  set_at_utc?: string;
  set_by_user_id?: number;
  is_bot?: boolean;
  analysis_id?: number;
}

interface ShowSummaryHistoryProps {
  obj_id?: string | null;
  summaries?: SummaryHistoryItem[] | null;
  button?: boolean;
}

const ShowSummaryHistory = ({
  obj_id = null,
  summaries = null,
  button = false,
}: ShowSummaryHistoryProps) => {
  const { classes } = useStyles();
  const { users: allUsers } = useAppSelector((state) => state.users);
  const userIdToUsername: Record<number, string> = {};

  const [dialogOpen, setDialogOpen] = useState(false);

  // Sort history from newest to oldest
  const sortedHistory = summaries?.sort((a, b) => {
    const dateA = new Date(a.set_at_utc as string);
    const dateB = new Date(b.set_at_utc as string);
    return dateB.getTime() - dateA.getTime();
  });

  if (allUsers.length) {
    allUsers?.forEach((user: any) => {
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
        onClose={() => setDialogOpen(false)}
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
                summaries?.map((historyItem) => (
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
                      {historyItem.set_by_user_id !== undefined &&
                        userIdToUsername[historyItem.set_by_user_id]}
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

export default ShowSummaryHistory;
