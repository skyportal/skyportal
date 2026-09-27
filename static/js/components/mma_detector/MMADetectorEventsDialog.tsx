import { useState } from "react";
import { Link } from "react-router-dom";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MuiLink from "@mui/material/Link";
import dayjs from "dayjs";

import StyledDataGrid from "../StyledDataGrid";
import { useGetConfigQuery } from "../../ducks/config";
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

  const tagColors = (useGetConfigQuery().data as any)?.gcnTagsClasses ?? {};
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
          getRowHeight={() => "auto"}
          sx={{
            "& .MuiDataGrid-cell": {
              whiteSpace: "normal",
              display: "flex",
              alignItems: "center",
            },
          }}
          columns={[
            {
              field: "dateobs",
              headerName: "Event (UTC)",
              width: 180,
              renderCell: ({ row }: any) => (
                <MuiLink component={Link} to={`/gcn_events/${row.dateobs}`}>
                  {dayjs(row.dateobs).format("YYYY-MM-DD HH:mm:ss")}
                </MuiLink>
              ),
            },
            {
              field: "aliases",
              headerName: "Aliases",
              width: 200,
              valueGetter: (value: any) => (value ?? []).join(", "),
            },
            {
              field: "tags",
              headerName: "Tags",
              flex: 1,
              minWidth: 120,
              valueGetter: (value: any) => (value ?? []).join(", "),
              renderCell: ({ row }: any) => (
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                  {[...new Set<string>(row.tags ?? [])].map((tag) => (
                    <Chip
                      key={tag}
                      size="small"
                      label={tag}
                      sx={{ backgroundColor: tagColors[tag] ?? "#999999" }}
                    />
                  ))}
                </Box>
              ),
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
