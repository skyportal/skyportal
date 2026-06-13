import { useMemo, useState } from "react";
import CircularProgress from "@mui/material/CircularProgress";

import { makeStyles } from "tss-react/mui";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Typography from "@mui/material/Typography";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import StyledDataGridBase, { DataGridToolbar } from "../StyledDataGrid";
import { getAnnotationValueString } from "../candidate/ScanningPageCandidateAnnotations";

import { useDeleteAnnotationMutation as useDeleteSourceAnnotationMutation } from "../../ducks/source";
import { useDeleteAnnotationMutation } from "../../ducks/spectra";

dayjs.extend(relativeTime);
dayjs.extend(utc);

// StyledDataGrid is a .jsx component whose propTypes make `sx` look required to
// tsc; cast to any so call sites don't need to pass it.
const StyledDataGrid: any = StyledDataGridBase;

const useStyles = makeStyles()(() => ({
  container: {
    width: "100%",
    margin: "auto",
    height: "100%",
  },
  dialogContent: {
    padding: 0,
  },
}));

const renderTime = (created_at: any) => dayjs().to(dayjs.utc(`${created_at}Z`));
const renderSpectrumDate = (observed_at: any) => {
  if (observed_at) {
    const dayFraction = (parseFloat(observed_at.substring(11, 13)) / 24) * 10;
    return `${observed_at.substring(0, 10)}.${dayFraction.toFixed(0)}`;
  }
  return "";
};

interface AnnotationsTableProps {
  annotations: any[];
  spectrumAnnotations?: any[];
  canExpand?: boolean;
}

// Table for displaying annotations
const AnnotationsTable = ({
  annotations,
  spectrumAnnotations = [],
  canExpand = true,
}: AnnotationsTableProps) => {
  const { classes } = useStyles();
  const [deleteSourceAnnotation] = useDeleteSourceAnnotationMutation();
  const [deleteSpectrumAnnotation] = useDeleteAnnotationMutation();

  const [openAnnotations, setOpenAnnotations] = useState(false);
  const [isRemoving, setIsRemoving] = useState<any>(null);
  const handleDelete = async (
    id: any,
    spectrum_id: any,
    annotation_id: any,
    type: any,
  ) => {
    setIsRemoving(annotation_id);
    if (type === "source") {
      try {
        await deleteSourceAnnotation({
          sourceID: id,
          annotationID: annotation_id,
        }).unwrap();
      } catch {
        // error notification handled by the baseQuery
      }
    } else if (type === "spectrum") {
      try {
        await deleteSpectrumAnnotation({
          id: spectrum_id,
          annotationID: annotation_id,
        }).unwrap();
      } catch {
        // error notification handled by the baseQuery
      }
    }
    setIsRemoving(null);
  };

  const handleClose = () => {
    setOpenAnnotations(false);
  };

  // Memoize the toolbar so it keeps a stable component identity across the
  // re-renders triggered as the source page loads its annotations/spectra
  // asynchronously. Without this, the inline function identity changes every
  // render, forcing MUI to unmount/remount the toolbar (and its QuickFilter
  // input) and invalidating any element reference a test is mid-interaction
  // with (StaleElementReferenceException on .clear()).
  const CustomToolbar = useMemo(
    () =>
      function AnnotationsTableToolbar() {
        return (
          <DataGridToolbar
            showExport
            quickFilterTestId="annotations-quick-filter"
          >
            {canExpand && (
              <IconButton
                name="expand_annotations"
                onClick={() => setOpenAnnotations(true)}
              >
                <OpenInFullIcon />
              </IconButton>
            )}
          </DataGridToolbar>
        );
      },
    [canExpand],
  );

  // Curate data. Combine source + spectrum annotations into a NEW array — the
  // `annotations` prop is now frozen RTK Query cache data, so mutating it with
  // `.push(...)` throws `TypeError: "length" is read-only`.
  const allAnnotations = [...(annotations ?? []), ...spectrumAnnotations];
  const tableData: any[] = [];
  allAnnotations.forEach((annotation: any) => {
    const {
      id,
      obj_id,
      origin,
      data,
      author,
      created_at,
      type,
      spectrum_id = null,
      spectrum_observed_at: observed_at = null,
    } = annotation;
    Object.entries(data).forEach(([key, value]) => {
      tableData.push({
        __rowid: tableData.length,
        id,
        obj_id,
        origin,
        key,
        value,
        author,
        created_at,
        type,
        spectrum_id,
        observed_at,
      });
    });
  });

  const renderDelete = (params: any) => {
    const annotation = params.row;
    return (
      <div>
        {isRemoving === annotation.id ? (
          <div>
            <CircularProgress />
          </div>
        ) : (
          <div>
            <IconButton
              onClick={() => {
                handleDelete(
                  annotation.obj_id,
                  annotation.spectrum_id,
                  annotation.id,
                  annotation.type,
                );
              }}
              size="small"
              type="submit"
            >
              <DeleteIcon />
            </IconButton>
          </div>
        )}
      </div>
    );
  };

  const columns: any[] = [
    { field: "origin", headerName: "Origin", flex: 1, minWidth: 120 },
    { field: "key", headerName: "Key", flex: 1, minWidth: 120 },
    {
      field: "value",
      headerName: "Value",
      flex: 1,
      minWidth: 120,
      valueFormatter: (value: any) => getAnnotationValueString(value),
    },
    {
      field: "author_username",
      headerName: "Author",
      flex: 1,
      minWidth: 120,
      valueGetter: (_value: any, row: any) => row.author?.username,
    },
    {
      field: "created_at",
      headerName: "Created",
      flex: 1,
      minWidth: 120,
      valueFormatter: (value: any) => renderTime(value),
    },
    {
      field: "delete",
      headerName: " ",
      width: 70,
      sortable: false,
      filterable: false,
      renderCell: renderDelete,
    },
  ];

  if (spectrumAnnotations?.length) {
    // add another column to show the spectrum observed at property
    columns.splice(1, 0, {
      field: "observed_at",
      headerName: "Spectrum Obs. at",
      flex: 1,
      minWidth: 140,
      // valueGetter (not valueFormatter) so the displayed "YYYY-MM-DD.f" string
      // is also the value the toolbar quick filter matches against.
      valueGetter: (value: any) => renderSpectrumDate(value),
    });
  }

  // Meta-object provenance: when the annotations span more than one underlying
  // Obj (i.e. aggregated across a SuperObj), surface which source each came from.
  const aggregatedAcrossObjs =
    new Set(tableData.map((row: any) => row.obj_id)).size > 1;
  if (aggregatedAcrossObjs) {
    columns.splice(1, 0, {
      field: "obj_id",
      headerName: "Source",
      flex: 1,
      minWidth: 120,
      renderCell: (params: any) => (
        <a
          href={`/source/${params.value}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          {params.value}
        </a>
      ),
    });
  }

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <div className={classes.container}>
        <Box sx={{ width: "100%", height: canExpand ? "22rem" : "78vh" }}>
          <StyledDataGrid
            columns={columns}
            rows={tableData}
            getRowId={(row: any) => row.__rowid}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
            }}
            pageSizeOptions={[10, 15, 50]}
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
      </div>
      <div>
        {openAnnotations && (
          <Dialog
            open={openAnnotations}
            onClose={handleClose}
            style={{ height: "100vh" }}
            fullScreen
          >
            <DialogTitle>
              <Typography variant="h6">Annotations</Typography>
              <IconButton
                aria-label="close"
                onClick={handleClose}
                sx={{
                  position: "absolute",
                  right: 8,
                  top: 8,
                  color: (colorTheme: any) => colorTheme.palette.grey[500],
                }}
              >
                <CloseIcon />
              </IconButton>
            </DialogTitle>
            <DialogContent dividers className={classes.dialogContent}>
              <AnnotationsTable
                annotations={annotations}
                spectrumAnnotations={spectrumAnnotations}
                canExpand={false}
              />
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  );
};

export default AnnotationsTable;
