import React, { useState, useMemo } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Slide from "@mui/material/Slide";
import CloseIcon from "@mui/icons-material/Close";
import DownloadIcon from "@mui/icons-material/Download";
import IconButton from "@mui/material/IconButton";
import CheckIcon from "@mui/icons-material/Check";
import ClearIcon from "@mui/icons-material/Clear";
import DeleteIcon from "@mui/icons-material/Delete";
import QuestionMarkIcon from "@mui/icons-material/QuestionMark";
import PriorityHigh from "@mui/icons-material/PriorityHigh";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";

import StyledDataGrid from "../StyledDataGrid";
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

const DEFAULT_HIDDEN_COLUMNS = [
  "instrument_id",
  "ra",
  "dec",
  "ra_unc",
  "dec_unc",
  "created_at",
  "flux_corr",
];

const useStyles = makeStyles()(() => ({
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
  },
  manage: {
    display: "flex",
    flexDirection: "row",
    gap: "0.2rem",
    marginRight: "0.4rem",
  },
}));

const Transition = React.forwardRef(function Transition(props: any, ref: any) {
  return <Slide direction="up" ref={ref} {...props} />;
});

const isFloat = (x: any) =>
  typeof x === "number" && Number.isFinite(x) && Math.floor(x) !== x;

// Format a raw cell value for display, preserving the old table's behavior:
// floats are fixed to 6 (or 8 for *jd* columns) decimals, and altdata objects
// are stringified. Used as a DataGrid valueFormatter so sorting still operates
// on the underlying numeric/object value.
const formatCell = (key: string) => (value: any) => {
  if (isFloat(value)) {
    return value.toFixed(key.includes("jd") ? 8 : 6);
  }
  if (key === "altdata" && typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }
  return value;
};

interface PhotometryTableProps {
  obj_id: string;
  open: boolean;
  onClose: (...a: any[]) => void;
  magsys?: string | null;
  setMagsys?: ((...a: any[]) => void) | null;
  t0?: number | null;
}

const PhotometryTable = ({
  obj_id,
  open,
  onClose,
  magsys = null,
  setMagsys = null,
  t0 = null,
}: PhotometryTableProps) => {
  const { usePhotometryValidation } = (useGetConfigQuery().data as any) ?? {};

  const { classes } = useStyles();
  const [deletePhotometry] = useDeletePhotometryMutation();

  const [deleteDialogOpen, setDeleteDialogOpen] = useState<any>(false);
  const [downloadOptionsOpen, setDownloadOptionsOpen] = useState(false);
  const [showExtinction, setShowExtinction] = useState(false);

  const queryParams = useMemo<any>(() => {
    const params: any = {};
    if (showExtinction) {
      params.includeExtinction = true;
    }
    if (magsys) {
      params.magsys = magsys;
    }
    return params;
  }, [showExtinction, magsys]);

  const { data: photometryData } = useFetchSourcePhotometryQuery(
    { id: obj_id, params: queryParams },
    { skip: !obj_id || !open },
  );
  const data = useMemo(() => photometryData ?? [], [photometryData]);

  // DataGrid persists column visibility itself; seed it with the columns that
  // were hidden by default in the old table.
  const [columnVisibilityModel, setColumnVisibilityModel] = useState<any>(() =>
    DEFAULT_HIDDEN_COLUMNS.reduce((acc: any, curr) => {
      acc[curr] = false;
      return acc;
    }, {}),
  );

  const handleDelete = async () => {
    if (!deleteDialogOpen) {
      return;
    }
    try {
      await deletePhotometry(deleteDialogOpen).unwrap();
    } catch {
      // error notification handled by the baseQuery
    }
    setDeleteDialogOpen(false);
  };
  const closeDeleteDialog = () => {
    setDeleteDialogOpen(false);
  };

  const handleDownloadClose = () => {
    setDownloadOptionsOpen(false);
  };

  const columns = useMemo<any[]>(() => {
    if (data.length === 0) {
      return [];
    }

    // Column order, mirroring the previous table.
    const keys = [
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

    if (showExtinction) {
      keys.splice(
        keys.indexOf("magerr") + 1,
        0,
        "extinction",
        "mag_corr",
        "flux_corr",
      );
    }

    // Pick up any extra keys present in the data that we did not enumerate.
    Object.keys(data[0]).forEach((key) => {
      const extinctionColumns = ["extinction", "mag_corr", "flux_corr"];
      const excludedKeys = [
        "groups",
        "owner",
        "obj_id",
        "id",
        "streams",
        "validations",
      ];

      if (extinctionColumns.includes(key) && !showExtinction) {
        return;
      }

      if (!keys.includes(key) && !excludedKeys.includes(key)) {
        keys.push(key);
      }
    });

    const cols: any[] = keys.map((key) => ({
      field: key,
      headerName: key,
      flex: 1,
      minWidth: 90,
      valueFormatter: formatCell(key),
    }));

    // Computed UTC column, inserted right after mjd.
    const utcColumn = {
      field: "UTC",
      headerName: "UTC",
      flex: 1,
      minWidth: 160,
      valueGetter: (_value: any, row: any) =>
        mjd_to_utc(row.mjd).replace("T", " "),
    };
    const mjdIndex = cols.findIndex((col) => col.field === "mjd");
    cols.splice(mjdIndex + 1, 0, utcColumn);

    // Computed t-t0 column, inserted right after UTC, only when t0 is known.
    if (t0 != null) {
      const tMinusT0Column = {
        field: "t-t0",
        headerName: "t-t0",
        flex: 1,
        minWidth: 90,
        valueGetter: (_value: any, row: any) => row.mjd - t0,
        valueFormatter: (value: any) =>
          isFloat(value) ? value.toFixed(6) : value,
      };
      const utcIndex = cols.findIndex((col) => col.field === "UTC");
      cols.splice(utcIndex + 1, 0, tMinusT0Column);
    }

    cols.push({
      field: "owner",
      headerName: "owner",
      flex: 1,
      minWidth: 100,
      valueGetter: (_value: any, row: any) => row.owner?.username || "",
    });

    cols.push({
      field: "streams",
      headerName: "streams",
      flex: 1,
      minWidth: 120,
      valueGetter: (_value: any, row: any) =>
        (row.streams || []).map((stream: any) => stream.name).join(", "),
    });

    if (usePhotometryValidation) {
      cols.push({
        field: "validation_status",
        headerName: "Validation",
        flex: 1,
        minWidth: 110,
        sortable: false,
        renderCell: (params: any) => {
          const phot = params.row;
          const validation = phot?.validations?.[0];
          let statusIcon = <QuestionMarkIcon color="primary" />;
          if (!validation) {
            statusIcon = <PriorityHigh color="primary" />;
          } else if (validation.validated === true) {
            statusIcon = <CheckIcon {...({ color: "green" } as any)} />;
          } else if (validation.validated === false) {
            statusIcon = <ClearIcon color="secondary" />;
          }
          return (
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                justifyContent: "center",
              }}
              {...({ name: `${phot.id}_validation_status` } as any)}
            >
              {statusIcon}
              <PhotometryValidation phot={phot} magsys={magsys ?? undefined} />
            </div>
          );
        },
      });

      cols.push({
        field: "validation_explanation",
        headerName: "Explanation",
        flex: 1,
        minWidth: 120,
        valueGetter: (_value: any, row: any) =>
          row?.validations?.[0]?.explanation || "",
      });

      cols.push({
        field: "validation_notes",
        headerName: "Notes",
        flex: 1,
        minWidth: 120,
        valueGetter: (_value: any, row: any) =>
          row?.validations?.[0]?.notes || "",
      });
    }

    cols.push({
      field: "manage",
      headerName: "Manage",
      flex: 1,
      minWidth: 110,
      sortable: false,
      filterable: false,
      renderCell: (params: any) => {
        const phot = params.row;
        return (
          <div className={classes.manage}>
            <div>
              <UpdatePhotometry phot={phot} magsys={magsys!} />
            </div>
            {deleteDialogOpen === phot.id ? (
              <div>
                <CircularProgress />
              </div>
            ) : (
              <div>
                <IconButton
                  onClick={() => setDeleteDialogOpen(phot.id)}
                  size="small"
                  type="submit"
                  data-testid={`deleteRequest_${phot.id}`}
                  {...({ primary: true } as any)}
                >
                  <DeleteIcon />
                </IconButton>
              </div>
            )}
          </div>
        );
      },
    });

    return cols;
  }, [
    data,
    t0,
    showExtinction,
    usePhotometryValidation,
    magsys,
    deleteDialogOpen,
    classes.manage,
  ]);

  const CustomToolbar = useMemo(
    () =>
      function PhotometryTableToolbar() {
        return (
          <GridToolbarContainer>
            <GridToolbarColumnsButton />
            <Button
              size="small"
              startIcon={<DownloadIcon />}
              onClick={() => setDownloadOptionsOpen(true)}
              data-testid="open-photometry-download-button"
            >
              Download
            </Button>
            <Box sx={{ flexGrow: 1 }} />
            <Tooltip title="Close Table">
              <IconButton
                onClick={onClose}
                data-testid="close-photometry-table-button"
                size="small"
              >
                <CloseIcon />
              </IconButton>
            </Tooltip>
          </GridToolbarContainer>
        );
      },
    [onClose],
  );

  let bodyContent = null;
  if (photometryData == null) {
    bodyContent = (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  } else if (data.length === 0) {
    bodyContent = <p>Source has no photometry.</p>;
  } else {
    bodyContent = (
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            flexDirection: "row",
            gap: "1rem",
            marginBottom: "0.5rem",
          }}
        >
          <Typography variant="h6" noWrap>
            {`Photometry of ${obj_id}`}
          </Typography>
          {magsys && typeof setMagsys === "function" && (
            <PhotometryMagsys magsys={magsys} setMagsys={setMagsys} />
          )}
          <PhotometryExtinction
            showExtinction={showExtinction}
            setShowExtinction={setShowExtinction}
          />
        </div>
        <Box sx={{ height: "calc(100vh - 8rem)", width: "100%" }}>
          <StyledDataGrid
            rows={data}
            columns={columns}
            columnVisibilityModel={columnVisibilityModel}
            onColumnVisibilityModelChange={setColumnVisibilityModel}
            initialState={{
              pagination: { paginationModel: { pageSize: 100 } },
            }}
            pageSizeOptions={[50, 100, 250, 500]}
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
        <ConfirmDeletionDialog
          deleteFunction={handleDelete}
          dialogOpen={deleteDialogOpen}
          closeDialog={closeDeleteDialog}
          resourceName="Photometry Point"
        />
        <PhotometryDownload
          open={downloadOptionsOpen}
          onClose={handleDownloadClose}
          data={data}
          objId={obj_id}
          usePhotometryValidation={usePhotometryValidation}
          onDownload={handleDownloadClose}
        />
      </div>
    );
  }

  return (
    <Dialog
      fullScreen
      open={open}
      onClose={onClose}
      TransitionComponent={Transition}
    >
      <DialogContent>{bodyContent}</DialogContent>
    </Dialog>
  );
};

export default PhotometryTable;
