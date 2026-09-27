import { useState } from "react";
import HistoryIcon from "@mui/icons-material/History";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import { useGetUsersQuery } from "../../ducks/users";
import StyledDataGrid from "../StyledDataGrid";

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
  // Only names, to label who set each redshift.
  const allUsers = useGetUsersQuery({ slim: true }).data?.users ?? [];

  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <>
      <HistoryIcon
        data-testid="redshiftHistoryIconButton"
        fontSize="small"
        sx={{ height: "0.75rem", cursor: "pointer" }}
        onClick={() => {
          setDialogOpen(true);
        }}
      />
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>Redshift History</DialogTitle>
        <DialogContent>
          <StyledDataGrid
            autoHeight
            rows={(redshiftHistory ?? []).map((row, id) => ({ ...row, id }))}
            columns={[
              {
                field: "set_by_user_id",
                headerName: "Set By",
                flex: 1,
                valueGetter: (value: number) =>
                  allUsers.find((user: any) => user.id === value)?.username,
              },
              { field: "set_at_utc", headerName: "Time (UTC)", flex: 1 },
              { field: "value", headerName: "Value", flex: 1 },
              { field: "uncertainty", headerName: "Uncertainty", flex: 1 },
              { field: "origin", headerName: "Origin", flex: 1 },
            ]}
            initialState={{
              sorting: { sortModel: [{ field: "set_at_utc", sort: "desc" }] },
            }}
          />
        </DialogContent>
      </Dialog>
    </>
  );
};

export default SourceRedshiftHistory;
