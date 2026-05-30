import React, { useMemo, useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
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
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarExport,
} from "@mui/x-data-grid";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import StyledDataGrid from "../StyledDataGrid";
import QuickFilter from "../QuickFilter";
import { getAnnotationValueString } from "../candidate/ScanningPageCandidateAnnotations";

import * as sourceActions from "../../ducks/source";
import * as spectraActions from "../../ducks/spectra";

dayjs.extend(relativeTime);
dayjs.extend(utc);

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

const renderTime = (created_at) => dayjs().to(dayjs.utc(`${created_at}Z`));
const renderSpectrumDate = (observed_at) => {
  if (observed_at) {
    const dayFraction = (parseFloat(observed_at.substring(11, 13)) / 24) * 10;
    return `${observed_at.substring(0, 10)}.${dayFraction.toFixed(0)}`;
  }
  return "";
};

// Table for displaying annotations
const AnnotationsTable = ({
  annotations,
  spectrumAnnotations = [],
  canExpand = true,
}) => {
  const { classes } = useStyles();
  const dispatch = useDispatch();

  const [openAnnotations, setOpenAnnotations] = useState(false);
  const [isRemoving, setIsRemoving] = useState(null);
  const handleDelete = async (id, spectrum_id, annotation_id, type) => {
    setIsRemoving(annotation_id);
    if (type === "source") {
      await dispatch(sourceActions.deleteAnnotation(id, annotation_id));
    } else if (type === "spectrum") {
      await dispatch(
        spectraActions.deleteAnnotation(spectrum_id, annotation_id),
      );
    }
    setIsRemoving(null);
  };

  const handleClose = () => {
    setOpenAnnotations(false);
  };

  // Curate data
  annotations?.push(...spectrumAnnotations);
  const tableData = [];
  annotations?.forEach((annotation) => {
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

  const renderDelete = (params) => {
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
              variant="contained"
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

  const columns = [
    { field: "origin", headerName: "Origin", flex: 1, minWidth: 120 },
    { field: "key", headerName: "Key", flex: 1, minWidth: 120 },
    {
      field: "value",
      headerName: "Value",
      flex: 1,
      minWidth: 120,
      valueFormatter: (value) => getAnnotationValueString(value),
    },
    {
      field: "author_username",
      headerName: "Author",
      flex: 1,
      minWidth: 120,
      valueGetter: (value, row) => row.author?.username,
    },
    {
      field: "created_at",
      headerName: "Created",
      flex: 1,
      minWidth: 120,
      valueFormatter: (value) => renderTime(value),
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
      valueGetter: (value) => renderSpectrumDate(value),
    });
  }

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
          <GridToolbarContainer>
            <GridToolbarColumnsButton />
            <GridToolbarExport />
            <div data-testid="annotations-quick-filter">
              <QuickFilter />
            </div>
            {canExpand && (
              <IconButton
                name="expand_annotations"
                onClick={() => setOpenAnnotations(true)}
              >
                <OpenInFullIcon />
              </IconButton>
            )}
          </GridToolbarContainer>
        );
      },
    [canExpand],
  );

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <div className={classes.container}>
        <Box sx={{ width: "100%", height: canExpand ? "22rem" : "78vh" }}>
          <StyledDataGrid
            columns={columns}
            rows={tableData}
            getRowId={(row) => row.__rowid}
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
                  color: (colorTheme) => colorTheme.palette.grey[500],
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

AnnotationsTable.propTypes = {
  annotations: PropTypes.arrayOf(
    PropTypes.shape({
      origin: PropTypes.string.isRequired,
      data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
      author: PropTypes.shape({
        username: PropTypes.string.isRequired,
      }).isRequired,
      created_at: PropTypes.string.isRequired,
    }),
  ).isRequired,
  spectrumAnnotations: PropTypes.arrayOf(
    PropTypes.shape({
      origin: PropTypes.string.isRequired,
      data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
      author: PropTypes.shape({
        username: PropTypes.string.isRequired,
      }).isRequired,
      created_at: PropTypes.string.isRequired,
      spectrum_observed_at: PropTypes.string.isRequired,
    }),
  ),
  canExpand: PropTypes.bool,
};
AnnotationsTable.defaultProps = {
  spectrumAnnotations: [],
  canExpand: true,
};

export default AnnotationsTable;
