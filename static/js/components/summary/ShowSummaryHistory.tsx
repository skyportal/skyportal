import { useState } from "react";
import HistoryIcon from "@mui/icons-material/History";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import { Link } from "react-router-dom";
import Tooltip from "@mui/material/Tooltip";
import dayjs from "dayjs";

import Button from "../Button";
import { useGetUsersQuery } from "../../ducks/users";
import StyledDataGrid from "../StyledDataGrid";

interface SummaryHistoryItem {
  summary?: string;
  set_at_utc?: string;
  set_by_user_id?: number;
  is_bot?: boolean;
  analysis_id?: number;
}

interface ShowSummaryHistoryProps {
  obj_id?: string | null;
  // Names the resource in the dialog title when it is not an obj.
  label?: string | null;
  summaries?: SummaryHistoryItem[] | null;
  button?: boolean;
}

const ShowSummaryHistory = ({
  obj_id = null,
  label = null,
  summaries = null,
  button = false,
}: ShowSummaryHistoryProps) => {
  const allUsers = useGetUsersQuery().data?.users ?? [];

  const [dialogOpen, setDialogOpen] = useState(false);

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
              fontSize="small"
              sx={{ height: "1rem", cursor: "pointer" }}
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
        <DialogTitle>Summary History for {label ?? obj_id}</DialogTitle>
        <DialogContent>
          <StyledDataGrid
            autoHeight
            getRowHeight={() => "auto"}
            sx={{ "& .MuiDataGrid-cell": { whiteSpace: "normal" } }}
            rows={(summaries ?? []).map((row, id) => ({ ...row, id }))}
            columns={[
              { field: "summary", headerName: "Summary", flex: 3 },
              {
                field: "set_by_user_id",
                headerName: "Set By",
                flex: 1,
                valueGetter: (value?: number) =>
                  allUsers.find((user: any) => user.id === value)?.username,
                renderCell: ({ row, value }: any) => (
                  <Box>
                    {row.is_bot && typeof row.analysis_id === "number" ? (
                      <Box sx={{ pr: "0.5rem" }}>
                        <Tooltip title="Link to analysis page" placement="top">
                          <Link
                            to={`/source/${obj_id}/analysis/${row.analysis_id}`}
                            role="link"
                          >
                            <Button primary size="small">
                              <SmartToyIcon fontSize="small" />
                            </Button>
                          </Link>
                        </Tooltip>
                      </Box>
                    ) : null}
                    {value && (
                      <Chip
                        size="small"
                        label={value}
                        component={Link}
                        to={`/user/${row.set_by_user_id}`}
                        clickable
                      />
                    )}
                  </Box>
                ),
              },
              {
                field: "set_at_utc",
                headerName: "Time (UTC)",
                width: 180,
                valueFormatter: (value: string) =>
                  dayjs(value).format("YYYY-MM-DD HH:mm:ss"),
              },
            ]}
            initialState={{
              sorting: { sortModel: [{ field: "set_at_utc", sort: "desc" }] },
              pagination: { paginationModel: { pageSize: 100 } },
            }}
          />
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ShowSummaryHistory;
