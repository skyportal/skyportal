import { useState } from "react";
import { Link } from "react-router-dom";
import Chip from "@mui/material/Chip";
import MuiLink from "@mui/material/Link";
import HistoryIcon from "@mui/icons-material/History";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Search from "@mui/icons-material/Search";
import dayjs from "dayjs";

import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetStreamsQuery } from "../../ducks/streams";
import StyledDataGrid from "../StyledDataGrid";

interface CandidateHistoryItem {
  id?: number;
  passing_alert_id?: number;
  passed_at?: string;
  passed_at_utc?: string;
  filter?: {
    id?: number;
    broker_id?: number | null;
    name?: string;
    group_id?: number;
    stream_id?: number;
  };
}

interface SourceCandidatesHistoryProps {
  candidates?: CandidateHistoryItem[];
}

const SourceCandidatesHistory = ({
  candidates = [],
}: SourceCandidatesHistoryProps) => {
  const { data: streams = [] } = useGetStreamsQuery();
  const userAccessible = useGetGroupsQuery().data?.userAccessible ?? [];

  const [search, setSearch] = useState("");

  const [dialogOpen, setDialogOpen] = useState(false);

  if (!candidates?.length) {
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
          sx={{ height: "1.4rem", cursor: "pointer", color: "gray" }}
          onClick={() => {
            setDialogOpen(true);
          }}
        />
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Typography variant="h6">Candidates History</Typography>
          <TextField
            label="Search by Filter"
            size="small"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            slotProps={{
              input: {
                endAdornment: <Search />,
              },
            }}
          />
        </DialogTitle>
        <DialogContent>
          <StyledDataGrid
            autoHeight
            rows={filteredCandidates}
            columns={[
              {
                field: "passing_alert_id",
                headerName: "Candidate ID",
                flex: 1,
              },
              {
                field: "passed_at",
                headerName: "Passed at (UTC)",
                width: 180,
                valueFormatter: (value: string) =>
                  dayjs(value).format("YYYY-MM-DD HH:mm:ss"),
              },
              {
                field: "filter",
                headerName: "Filter",
                flex: 1,
                valueGetter: (_value: any, row: CandidateHistoryItem) =>
                  row.filter?.name,
                renderCell: ({ value, row }: any) =>
                  row.filter && (
                    <MuiLink component={Link} to={`/filter/${row.filter.id}`}>
                      {value}
                    </MuiLink>
                  ),
              },
              {
                field: "group",
                headerName: "Group",
                flex: 1,
                valueGetter: (_value: any, row: CandidateHistoryItem) =>
                  userAccessible.find(
                    (group: any) => group.id === row.filter?.group_id,
                  )?.name || "N/A",
                renderCell: ({ value, row }: any) =>
                  row.filter?.group_id ? (
                    <Chip
                      size="small"
                      label={value}
                      component={Link}
                      to={`/group/${row.filter.group_id}`}
                      clickable
                    />
                  ) : (
                    value
                  ),
              },
              {
                field: "stream",
                headerName: "Stream",
                flex: 1,
                valueGetter: (_value: any, row: CandidateHistoryItem) =>
                  streams.find(
                    (stream: any) => stream.id === row.filter?.stream_id,
                  )?.name || "N/A",
              },
            ]}
            initialState={{
              pagination: { paginationModel: { pageSize: 100 } },
            }}
          />
        </DialogContent>
      </Dialog>
    </>
  );
};

export default SourceCandidatesHistory;
