import { useState } from "react";
import HistoryIcon from "@mui/icons-material/History";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

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
              { field: "name", headerName: "Group Name", flex: 1 },
              {
                field: "saved_by",
                headerName: "Saved By",
                flex: 1,
                valueGetter: (_value: any, row: Group) =>
                  row.saved_by?.username,
              },
              { field: "saved_at", headerName: "Time (UTC)", flex: 1 },
            ]}
            initialState={{
              sorting: { sortModel: [{ field: "saved_at", sort: "desc" }] },
            }}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default SourceSaveHistory;
