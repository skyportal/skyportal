import { useState } from "react";
import { Link } from "react-router-dom";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import dayjs from "dayjs";

import StyledDataGrid from "../StyledDataGrid";
import { useGetGcnEventsQuery } from "../../ducks/gcnEvents";

interface MMADetectorEventsDialogProps {
  mmadetector: any;
  onClose: () => void;
}

const MMADetectorEventsDialog = ({
  mmadetector,
  onClose,
}: MMADetectorEventsDialogProps) => {
  const [paginationModel, setPaginationModel] = useState({
    page: 0,
    pageSize: 25,
  });

  const { data, isFetching } = useGetGcnEventsQuery({
    mmadetectorIds: `${mmadetector.id}`,
    numPerPage: paginationModel.pageSize,
    pageNumber: paginationModel.page + 1,
  });

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {mmadetector.name} ({mmadetector.nickname})
      </DialogTitle>
      <DialogContent dividers>
        <StyledDataGrid
          data-testid="mmadetector-events-table"
          autoHeight
          rows={(data as any)?.events ?? []}
          getRowId={(row: any) => row.dateobs}
          columns={[
            {
              field: "dateobs",
              headerName: "Event",
              flex: 1,
              minWidth: 170,
              renderCell: ({ row }: any) => (
                <Link to={`/gcn_events/${row.dateobs}`}>
                  {dayjs(row.dateobs).format("YYYY-MM-DD HH:mm:ss")}
                </Link>
              ),
            },
            {
              field: "aliases",
              headerName: "Aliases",
              flex: 1,
              minWidth: 120,
              valueGetter: (value: any) => (value ?? []).join(", "),
            },
            {
              field: "tags",
              headerName: "Tags",
              flex: 1,
              minWidth: 120,
              valueGetter: (value: any) => (value ?? []).join(", "),
            },
          ]}
          loading={isFetching}
          paginationMode="server"
          rowCount={(data as any)?.totalMatches ?? 0}
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          localeText={{
            noRowsLabel: "No GCN events are linked to this detector.",
          }}
        />
      </DialogContent>
    </Dialog>
  );
};

export default MMADetectorEventsDialog;
