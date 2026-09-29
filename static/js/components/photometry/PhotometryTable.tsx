import React, { ReactNode, useState, useMemo } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Slide from "@mui/material/Slide";
import DownloadIcon from "@mui/icons-material/Download";
import IconButton from "@mui/material/IconButton";
import CheckIcon from "@mui/icons-material/Check";
import ClearIcon from "@mui/icons-material/Clear";
import DeleteIcon from "@mui/icons-material/Delete";
import QuestionMarkIcon from "@mui/icons-material/QuestionMark";
import PriorityHigh from "@mui/icons-material/PriorityHigh";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";

import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import UpdatePhotometry from "./UpdatePhotometry";
import PhotometryValidation from "./PhotometryValidation";
import PhotometryMagsys from "./PhotometryMagsys";
import PhotometryExtinction from "./PhotometryExtinction";
import PhotometryDownload from "./PhotometryDownload";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import {
  useFetchSourcePhotometryQuery,
  useDeletePhotometryMutation,
} from "../../ducks/photometry";
import { mjd_to_utc } from "../../units";
import { useGetConfigQuery } from "../../ducks/config";
import { useGetProfileQuery } from "../../ducks/profile";

const DEFAULT_HIDDEN_COLUMNS = [
  "id",
  "instrument_id",
  "ra",
  "dec",
  "ra_unc",
  "dec_unc",
  "created_at",
  "flux_corr",
];

const EXTINCTION_COLUMNS = ["extinction", "mag_corr", "flux_corr"];

const COLUMN_ORDER = [
  "id",
  "mjd",
  "mag",
  "magerr",
  "limiting_mag",
  "filter",
  "instrument_name",
  "instrument_id",
  "snr",
  "magsys",
  "origin",
  "altdata",
  "ra",
  "dec",
  "ra_unc",
  "dec_unc",
  "created_at",
];

const EXCLUDED_KEYS = [
  "groups",
  "owner",
  "obj_id",
  "streams",
  "validations",
  ...EXTINCTION_COLUMNS,
];

const Transition = React.forwardRef(function Transition(props: any, ref: any) {
  return <Slide direction="up" ref={ref} {...props} />;
});

const isFloat = (x: any) =>
  typeof x === "number" && Number.isFinite(x) && Math.floor(x) !== x;

const COLUMN_PRECISION: Record<string, number> = {
  mjd: 3,
  mag: 4,
  magerr: 4,
  limiting_mag: 2,
  snr: 2,
};

const formatCell = (key: string) => (value: any) => {
  if (isFloat(value)) return value.toFixed(COLUMN_PRECISION[key] ?? 6);
  if (key === "altdata" && typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }
  return value;
};

const VALIDATION_STATUS: Record<string, { icon: ReactNode; label: string }> = {
  true: { icon: <CheckIcon sx={{ color: "green" }} />, label: "Validated" },
  false: { icon: <ClearIcon color="secondary" />, label: "Rejected" },
  null: { icon: <QuestionMarkIcon color="primary" />, label: "Ambiguous" },
};

const NOT_VETTED = {
  icon: <PriorityHigh color="primary" />,
  label: "Not vetted",
};

interface PhotometryTableProps {
  obj_id: string;
  open: boolean;
  onClose: (...a: any[]) => void;
  magsys?: string | null;
  setMagsys?: ((...a: any[]) => void) | null;
  t0?: number | null;
}

const PhotometryTableToolbar = ({
  title,
  controls,
  onDownload,
  onClose,
}: {
  title: string;
  controls: ReactNode;
  onDownload: () => void;
  onClose: () => void;
}) => (
  <DataGridToolbar
    title={title}
    showExport={false}
    onClose={onClose}
    closeTestId="close-photometry-table-button"
  >
    {controls}
    <Tooltip title="Download">
      <IconButton
        size="small"
        onClick={onDownload}
        data-testid="open-photometry-download-button"
      >
        <DownloadIcon />
      </IconButton>
    </Tooltip>
  </DataGridToolbar>
);

const PhotometryTable = ({
  obj_id,
  open,
  onClose,
  magsys = null,
  setMagsys = null,
  t0 = null,
}: PhotometryTableProps) => {
  const { usePhotometryValidation } = (useGetConfigQuery().data as any) ?? {};

  const { id: currentUserId, permissions = [] } =
    (useGetProfileQuery().data as any) ?? {};
  const isSaved = (phot: any) => phot?.id != null;
  const canManagePhotometry = (phot: any) =>
    isSaved(phot) &&
    (permissions.includes("System admin") ||
      permissions.includes("Manage photometry") ||
      (phot?.owner?.id != null && phot.owner.id === currentUserId));

  const [deletePhotometry] = useDeletePhotometryMutation();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState<any>(false);
  const [downloadOptionsOpen, setDownloadOptionsOpen] = useState(false);
  const [showExtinction, setShowExtinction] = useState(false);

  const { data: photometryData, isFetching } = useFetchSourcePhotometryQuery(
    {
      id: obj_id,
      params: {
        includeSuperObjsPhotometry: true,
        ...(showExtinction && { includeExtinction: true }),
        ...(magsys && { magsys }),
      },
    },
    { skip: !obj_id || !open },
  );
  const data = useMemo(() => photometryData ?? [], [photometryData]);

  const [columnVisibilityModel, setColumnVisibilityModel] = useState<any>(() =>
    Object.fromEntries(DEFAULT_HIDDEN_COLUMNS.map((key) => [key, false])),
  );

  const handleDelete = async () => {
    if (!deleteDialogOpen) return;
    try {
      await deletePhotometry(deleteDialogOpen).unwrap();
    } catch {
      // error notification handled by the baseQuery
    }
    setDeleteDialogOpen(false);
  };

  const columns = useMemo<any[]>(() => {
    if (data.length === 0) return [];

    const keys = [...COLUMN_ORDER];
    if (showExtinction) {
      keys.splice(keys.indexOf("magerr") + 1, 0, ...EXTINCTION_COLUMNS);
    }
    keys.push(
      ...Object.keys(data[0] ?? {}).filter(
        (key) => !keys.includes(key) && !EXCLUDED_KEYS.includes(key),
      ),
    );

    const cols: any[] = keys.flatMap((key) => {
      const column = {
        field: key,
        headerName: key,
        flex: 1,
        minWidth: key === "mjd" ? 110 : Math.max(90, key.length * 9 + 40),
        valueFormatter: formatCell(key),
      };
      if (key !== "mjd") return [column];
      return [
        column,
        {
          field: "UTC",
          headerName: "UTC",
          flex: 1,
          minWidth: 180,
          valueGetter: (_value: any, row: any) =>
            mjd_to_utc(row.mjd).replace("T", " "),
        },
        ...(t0 != null
          ? [
              {
                field: "t-t0",
                headerName: "t-t0",
                flex: 1,
                minWidth: 90,
                valueGetter: (_value: any, row: any) => row.mjd - t0,
                valueFormatter: (value: any) =>
                  isFloat(value) ? value.toFixed(6) : value,
              },
            ]
          : []),
      ];
    });

    cols.push(
      {
        field: "owner",
        headerName: "owner",
        flex: 1,
        minWidth: 150,
        valueGetter: (_value: any, row: any) => row.owner?.username || "",
      },
      {
        field: "streams",
        headerName: "streams",
        flex: 1,
        minWidth: 180,
        valueGetter: (_value: any, row: any) =>
          (row.streams || []).map((stream: any) => stream.name).join(", "),
      },
    );

    if (usePhotometryValidation) {
      cols.push(
        {
          field: "validation_status",
          headerName: "Validation",
          flex: 1,
          minWidth: 110,
          sortable: false,
          renderCell: ({ row }: any) => {
            const validation = row.validations?.[0];
            const { icon, label } =
              (validation &&
                VALIDATION_STATUS[`${validation.validated ?? null}`]) ||
              NOT_VETTED;
            return (
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Tooltip title={label}>{icon}</Tooltip>
                {isSaved(row) && (
                  <PhotometryValidation
                    phot={row}
                    magsys={magsys ?? undefined}
                  />
                )}
              </Box>
            );
          },
        },
        {
          field: "validation_explanation",
          headerName: "Explanation",
          flex: 1,
          minWidth: 120,
          valueGetter: (_value: any, row: any) =>
            row.validations?.[0]?.explanation || "",
        },
        {
          field: "validation_notes",
          headerName: "Notes",
          flex: 1,
          minWidth: 120,
          valueGetter: (_value: any, row: any) =>
            row.validations?.[0]?.notes || "",
        },
      );
    }

    cols.push({
      field: "manage",
      headerName: "Manage",
      flex: 1,
      minWidth: 110,
      sortable: false,
      filterable: false,
      renderCell: ({ row }: any) =>
        canManagePhotometry(row) && (
          <Box sx={{ display: "flex", gap: "0.2rem", mr: "0.4rem" }}>
            <UpdatePhotometry phot={row} magsys={magsys!} />
            {deleteDialogOpen === row.id ? (
              <CircularProgress />
            ) : (
              <IconButton
                onClick={() => setDeleteDialogOpen(row.id)}
                size="small"
              >
                <DeleteIcon />
              </IconButton>
            )}
          </Box>
        ),
    });

    return cols;
  }, [
    data,
    t0,
    showExtinction,
    usePhotometryValidation,
    magsys,
    deleteDialogOpen,
    currentUserId,
    permissions,
  ]);

  return (
    <Dialog
      fullScreen
      open={open}
      onClose={onClose}
      slots={{
        transition: Transition,
      }}
    >
      <DialogContent sx={{ display: "flex", flexDirection: "column" }}>
        <Box sx={{ flex: 1, minHeight: 0, width: "100%" }}>
          <StyledDataGrid
            rows={data}
            getRowId={(row: any) =>
              row.id ??
              `${row.obj_id}-${row.instrument_id}-${row.filter}-${row.mjd}`
            }
            columns={columns}
            loading={isFetching}
            localeText={{ noRowsLabel: "Source has no photometry." }}
            columnVisibilityModel={columnVisibilityModel}
            onColumnVisibilityModelChange={setColumnVisibilityModel}
            initialState={{
              pagination: { paginationModel: { pageSize: 100 } },
            }}
            pageSizeOptions={[50, 100, { value: -1, label: "All" }]}
            slots={{ toolbar: PhotometryTableToolbar }}
            slotProps={{
              toolbar: {
                title: `Photometry of ${obj_id}`,
                controls: (
                  <>
                    {magsys && typeof setMagsys === "function" && (
                      <PhotometryMagsys magsys={magsys} setMagsys={setMagsys} />
                    )}
                    <PhotometryExtinction
                      showExtinction={showExtinction}
                      setShowExtinction={setShowExtinction}
                    />
                  </>
                ),
                onDownload: () => setDownloadOptionsOpen(true),
                onClose,
              },
            }}
            showToolbar
          />
        </Box>
        <ConfirmDeletionDialog
          deleteFunction={handleDelete}
          dialogOpen={deleteDialogOpen}
          closeDialog={() => setDeleteDialogOpen(false)}
          resourceName="Photometry Point"
        />
        <PhotometryDownload
          open={downloadOptionsOpen}
          onClose={() => setDownloadOptionsOpen(false)}
          data={data}
          objId={obj_id}
          usePhotometryValidation={usePhotometryValidation}
          onDownload={() => setDownloadOptionsOpen(false)}
          t0={t0}
        />
      </DialogContent>
    </Dialog>
  );
};

export default PhotometryTable;
