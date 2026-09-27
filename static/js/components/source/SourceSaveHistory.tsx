import { useState } from "react";
import { Link } from "react-router-dom";
import Chip from "@mui/material/Chip";
import HistoryIcon from "@mui/icons-material/History";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import dayjs from "dayjs";

import { Group } from "../../types/domain";
import StyledDataGrid from "../StyledDataGrid";

interface SourceSaveHistoryProps {
  groups: Group[];
}

const SourceSaveHistory = ({ groups }: SourceSaveHistoryProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <Box sx={{ display: "inline-block" }}>
      <Tooltip title="Source save history">
        <span>
          <IconButton
            aria-label="source-save-history"
            onClick={() => {
              setDialogOpen(true);
            }}
            size="small"
            sx={{ display: "inline-block" }}
          >
            <HistoryIcon sx={{ fontSize: "1rem" }} />
          </IconButton>
        </span>
      </Tooltip>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth>
        <DialogTitle>Save History</DialogTitle>
        <DialogContent>
          <StyledDataGrid
            autoHeight
            rows={groups ?? []}
            columns={[
              {
                field: "name",
                headerName: "Group Name",
                flex: 1,
                renderCell: ({ row }: { row: Group }) => (
                  <Chip
                    size="small"
                    label={row.name}
                    component={Link}
                    to={`/group/${row.id}`}
                    clickable
                  />
                ),
              },
              {
                field: "saved_by",
                headerName: "Saved By",
                flex: 1,
                valueGetter: (_value: any, row: Group) =>
                  row.saved_by?.username,
                renderCell: ({ value, row }: any) =>
                  value && (
                    <Chip
                      size="small"
                      label={value}
                      component={Link}
                      to={`/user/${row.saved_by.id}`}
                      clickable
                    />
                  ),
              },
              {
                field: "saved_at",
                headerName: "Time (UTC)",
                width: 180,
                valueFormatter: (value: string) =>
                  dayjs(value).format("YYYY-MM-DD HH:mm:ss"),
              },
            ]}
            initialState={{
              sorting: { sortModel: [{ field: "saved_at", sort: "desc" }] },
              pagination: { paginationModel: { pageSize: 100 } },
            }}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default SourceSaveHistory;
