import { useState } from "react";
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

import { useGetUsersQuery } from "../../ducks/users";

const useStyles = makeStyles()(() => ({
  saveButton: {
    textAlign: "center",
    margin: "1rem",
  },
  historyIcon: {
    height: "0.75rem",
    cursor: "pointer",
  },
}));

interface RedshiftHistoryItem {
  set_at_utc: string;
  set_by_user_id: number;
  value?: number | null;
  uncertainty?: number | null;
  origin?: string | null;
}

interface SourceRedshiftHistoryProps {
  redshiftHistory?: RedshiftHistoryItem[] | null;
}

const SourceRedshiftHistory = ({
  redshiftHistory = null,
}: SourceRedshiftHistoryProps) => {
  const { classes } = useStyles();
  const allUsers = useGetUsersQuery().data?.users ?? [];
  const userIdToUsername: Record<number, string> = {};

  const [dialogOpen, setDialogOpen] = useState(false);

  // Sort history from newest to oldest.
  // `redshiftHistory` is frozen RTK Query data, so copy before sorting in place.
  const sortedHistory = [...(redshiftHistory ?? [])].sort((a, b) => {
    const dateA = new Date(a.set_at_utc);
    const dateB = new Date(b.set_at_utc);
    return dateB.getTime() - dateA.getTime();
  });

  if (allUsers.length) {
    allUsers?.forEach((user: any) => {
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
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Redshift History</DialogTitle>
        <DialogContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Set By</TableCell>
                <TableCell>Time (UTC)</TableCell>
                <TableCell>Value</TableCell>
                <TableCell>Uncertainty</TableCell>
                <TableCell>Origin</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedHistory &&
                allUsers.length &&
                redshiftHistory?.map((historyItem) => (
                  <TableRow key={historyItem.set_at_utc}>
                    <TableCell>
                      {userIdToUsername[historyItem.set_by_user_id]}
                    </TableCell>
                    <TableCell>{historyItem.set_at_utc}</TableCell>
                    <TableCell>{historyItem.value}</TableCell>
                    <TableCell>{historyItem.uncertainty}</TableCell>
                    <TableCell>{historyItem?.origin || ""}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default SourceRedshiftHistory;
