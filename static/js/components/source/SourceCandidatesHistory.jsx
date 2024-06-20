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
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Search from "@mui/icons-material/Search";

const useStyles = makeStyles(() => ({
  historyIcon: {
    height: "1.4rem",
    cursor: "pointer",
    color: "gray",
  },
  dialogTitle: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
}));

const SourceCandidatesHistory = ({ candidates }) => {
  const classes = useStyles();
  const streams = useSelector((state) => state.streams);
  const { userAccessible } = useSelector((state) => state.groups);

  const [search, setSearch] = useState("");

  const [dialogOpen, setDialogOpen] = useState(false);

  if (!(candidates?.length > 0)) {
    return null;
  }

  const filteredCandidates =
    search?.trim()?.length > 0
      ? candidates.filter((candidate) => {
          const filter = candidate?.filter?.name || "";
          return filter.toLowerCase().includes(search.toLowerCase());
        })
      : candidates;

  return (
    <>
      <Tooltip title="Candidates History" placement="top">
        <HistoryIcon
          data-testid="candidatesHistoryIconButton"
          className={classes.historyIcon}
          onClick={() => {
            setDialogOpen(true);
          }}
        />
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        style={{ position: "fixed" }}
        maxWidth="md"
      >
        <DialogTitle className={classes.dialogTitle}>
          <Typography variant="h6">Candidates History</Typography>
          <TextField
            label="Search by Filter"
            size="small"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            InputProps={{
              endAdornment: <Search />,
            }}
          />
        </DialogTitle>
        <DialogContent>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Candidate ID</TableCell>
                <TableCell>Passed at (UTC)</TableCell>
                <TableCell>Filter</TableCell>
                <TableCell>Group</TableCell>
                <TableCell>Stream</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(filteredCandidates || []).map((historyItem) => (
                <TableRow key={`candidate-history-${historyItem.id}`}>
                  <TableCell>{historyItem?.passing_alert_id}</TableCell>
                  <TableCell>{historyItem?.passed_at}</TableCell>
                  <TableCell>{historyItem?.filter?.name}</TableCell>
                  <TableCell>
                    {userAccessible?.find(
                      (group) => group.id === historyItem?.filter?.group_id,
                    )?.name || "N/A"}
                  </TableCell>
                  <TableCell>
                    {streams?.find(
                      (stream) => stream.id === historyItem?.filter?.stream_id,
                    )?.name || "N/A"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </DialogContent>
      </Dialog>
    </>
  );
};

SourceCandidatesHistory.propTypes = {
  candidates: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      passing_alert_id: PropTypes.number,
      passed_at_utc: PropTypes.string,
      filter: PropTypes.shape({
        name: PropTypes.string,
        group_id: PropTypes.number,
        stream_id: PropTypes.number,
      }),
    }),
  ),
};
SourceCandidatesHistory.defaultProps = {
  candidates: [],
};

export default SourceCandidatesHistory;
