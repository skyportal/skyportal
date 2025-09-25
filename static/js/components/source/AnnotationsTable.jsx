import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";

import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import { makeStyles } from "@mui/styles";
import MUIDataTable from "mui-datatables";
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

import { getAnnotationValueString } from "../candidate/ScanningPageCandidateAnnotations";

import * as sourceActions from "../../ducks/source";
import * as spectraActions from "../../ducks/spectra";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  container: {
    width: "100%",
    margin: "auto",
    height: "100%",
  },
  dialogContent: {
    padding: 0,
  },
}));

// Tweak responsive column widths
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTableBodyCell: {
        styleOverrides: {
          root: {
            padding: `${theme.spacing(0.5)} 0 ${theme.spacing(
              0.5,
            )} ${theme.spacing(0.5)}`,
          },
        },
      },
      MUIDataTableHeadCell: {
        styleOverrides: {
          root: {
            padding: `${theme.spacing(1)} 0 ${theme.spacing(1)} ${theme.spacing(
              1,
            )}`,
          },
        },
      },
      MUIDataTableToolbar: {
        styleOverrides: {
          root: {
            maxHeight: "2rem",
            padding: 0,
            margin: 0,
            paddingRight: "0.75rem",
          },
        },
      },
      MuiIconButton: {
        root: {
          padding: "0.5rem",
        },
      },
      MUIDataTablePagination: {
        toolbar: {
          flexFlow: "row wrap",
          justifyContent: "flex-end",
          padding: "0.5rem 1rem 0",
          [theme.breakpoints.up("sm")]: {
            // Cancel out small screen styling and replace
            padding: "0px",
            paddingRight: "2px",
            flexFlow: "row nowrap",
          },
        },
        tableCellContainer: {
          padding: "1rem",
        },
        selectRoot: {
          marginRight: "0.5rem",
          [theme.breakpoints.up("sm")]: {
            marginLeft: "0",
            marginRight: "2rem",
          },
        },
      },
    },
  });

// Table for displaying annotations
const AnnotationsTable = ({
  annotations,
  spectrumAnnotations = [],
  canExpand = true,
}) => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();
  const renderValue = (value) => getAnnotationValueString(value);
  const renderTime = (created_at) => dayjs().to(dayjs.utc(`${created_at}Z`));
  const renderSpectrumDate = (observed_at) => {
    if (observed_at) {
      const dayFraction = (parseFloat(observed_at.substring(11, 13)) / 24) * 10;
      return `${observed_at.substring(0, 10)}.${dayFraction.toFixed(0)}`;
    }
    return "";
  };

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

  const renderDelete = (tmp, row) => {
    const annotation = tableData[row.rowIndex];

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
              data-testid={`deleteAllocation_${annotation.id}`}
            >
              <DeleteIcon />
            </IconButton>
          </div>
        )}
      </div>
    );
  };

  const columns = [
    {
      name: "origin",
      label: "Origin",
    },
    {
      name: "key",
      label: "Key",
    },
    {
      name: "value",
      label: "Value",
      options: {
        customBodyRender: renderValue,
      },
    },
    {
      name: "author.username",
      label: "Author",
    },
    {
      name: "created_at",
      label: "Created",
      options: {
        customBodyRender: renderTime,
      },
    },
    {
      name: "delete",
      label: " ",
      options: {
        customBodyRender: renderDelete,
        sort: false,
        setCellProps: () => ({ style: { maxWidth: "4rem" } }),
      },
    },
  ];

  if (spectrumAnnotations?.length) {
    // add another column to show the spectrum observed at property
    columns.splice(1, 0, {
      name: "observed_at",
      label: "Spectrum Obs. at",
      options: { customBodyRender: renderSpectrumDate },
    });
  }

  const options = {
    responsive: "standard",
    print: true,
    download: true,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    elevation: 0,
    rowsPerPage: 10,
    rowsPerPageOptions: [10, 15, 50],
    jumpToPage: false,
    pagination: true,
    tableBodyMaxHeight: canExpand ? "20rem" : "75vh",
    customToolbar: () => {
      if (canExpand) {
        return (
          <IconButton
            name="expand_annotations"
            onClick={() => {
              setOpenAnnotations(true);
            }}
          >
            <OpenInFullIcon />
          </IconButton>
        );
      }
      return null;
    },
  };

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <div className={classes.container}>
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              columns={columns}
              data={tableData}
              options={options}
            />
          </ThemeProvider>
        </StyledEngineProvider>
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
