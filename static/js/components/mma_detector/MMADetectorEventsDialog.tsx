import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Dialog from "@mui/material/Dialog";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import dayjs from "dayjs";

import { useGetGcnEventsQuery } from "../../ducks/gcnEvents";
import { useGetConfigQuery } from "../../ducks/config";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import ExpandableCell from "../ExpandableCell";

const numPerPage = 10;

interface MMADetectorEventsDialogProps {
  mmadetector: any;
  onClose: () => void;
}

const MMADetectorEventsDialog = ({
  mmadetector,
  onClose,
}: MMADetectorEventsDialogProps) => {
  const [page, setPage] = useState(0);
  const { data, isFetching } = useGetGcnEventsQuery({
    mmadetectorIds: `${mmadetector.id}`,
    numPerPage,
    pageNumber: page + 1,
  });
  const tagColors = useGetConfigQuery().data?.["gcnTagsClasses"] as
    Record<string, string> | undefined;

  const columns = [
    {
      field: "dateobs",
      headerName: "Event",
      flex: 1,
      minWidth: 180,
      renderCell: ({ value }: any) => (
        <Link
          component={RouterLink}
          to={`/gcn_events/${value}`}
          underline="hover"
        >
          {dayjs(value).format("YYYY-MM-DD HH:mm:ss")}
        </Link>
      ),
    },
    {
      field: "aliases",
      headerName: "Aliases",
      flex: 1,
      valueGetter: (value: string[] | undefined) => value?.join(", "),
    },
    {
      field: "tags",
      headerName: "Tags",
      flex: 2,
      renderCell: ({ value }: any) => (
        <ExpandableCell
          maxVisible={6}
          items={[...new Set<string>(value ?? [])].map((tag) => (
            <Chip
              key={tag}
              size="small"
              label={tag}
              sx={{ bgcolor: tagColors?.[tag] ?? "#999999" }}
            />
          ))}
        />
      ),
    },
  ];

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <StyledDataGrid
        autoHeight
        rows={data?.events ?? []}
        columns={columns}
        getRowId={(row: any) => row.dateobs}
        getRowHeight={() => "auto"}
        loading={isFetching}
        paginationMode="server"
        rowCount={data?.totalMatches ?? 0}
        paginationModel={{ page, pageSize: numPerPage }}
        onPaginationModelChange={(model: any) => setPage(model.page)}
        pageSizeOptions={[numPerPage]}
        disableColumnMenu
        disableColumnSorting
        localeText={{
          noRowsLabel: "No GCN events are linked to this detector.",
        }}
        slots={{ toolbar: DataGridToolbar }}
        slotProps={{
          root: { "data-testid": "mmadetector-events-table" },
          toolbar: {
            title: `${mmadetector.name} (${mmadetector.nickname})`,
            showColumns: false,
            showQuickFilter: false,
            showExport: false,
          },
        }}
        showToolbar
      />
    </Dialog>
  );
};

export default MMADetectorEventsDialog;
