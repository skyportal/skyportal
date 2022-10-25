import React, { useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";

import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { getAnnotationValueString } from "./ScanningPageCandidateAnnotations";
import Button from "./Button";

import * as sourceActions from "../ducks/source";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  container: {
    width: "100%",
    margin: "auto",
  },
}));

// Tweak responsive column widths
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    overrides: {
      MUIDataTableBodyCell: {
        root: {
          padding: `${theme.spacing(0.5)} 0 ${theme.spacing(
            0.5
          )} ${theme.spacing(0.5)}`,
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
const AnnotationsTable = ({ annotations, spectrumAnnotations = [] }) => {
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

  const [isRemoving, setIsRemoving] = useState(null);
  const handleDelete = async (obj_id, id) => {
    setIsRemoving(id);
    await dispatch(sourceActions.deleteAnnotation(obj_id, id));
    setIsRemoving(null);
  };

  // Curate data
  const tableData = [];
  annotations?.push(...spectrumAnnotations);
  annotations?.forEach((annotation) => {
    const {
      id,
      obj_id,
      origin,
      data,
      author,
      created_at,
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
        observed_at,
      });
    });
  });

  const renderDelete = (tmp, row) => {
    const annotation = tableData[row.rowIndex];

    return (
      <div className={classes.actionButtons}>
        {isRemoving === annotation.id ? (
          <div>
            <CircularProgress />
          </div>
        ) : (
          <div>
            <Button
              secondary
              onClick={() => {
                handleDelete(annotation.obj_id, annotation.id);
              }}
              size="small"
              type="submit"
              data-testid={`deleteAllocation_${annotation.id}`}
            >
              Delete
            </Button>
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
      label: "Delete",
      options: {
        customBodyRender: renderDelete,
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
    elevation: 2,
    rowsPerPage: 10,
    rowsPerPageOptions: [10, 15, 50],
    jumpToPage: false,
    pagination: true,
    tableBodyMaxHeight: "20rem",
  };

  return (
    <div className={classes.container}>
      <StyledEngineProvider injectFirst>
        <ThemeProvider theme={getMuiTheme(theme)}>
          <MUIDataTable columns={columns} data={tableData} options={options} />
        </ThemeProvider>
      </StyledEngineProvider>
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
    })
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
    })
  ),
};
AnnotationsTable.defaultProps = {
  spectrumAnnotations: [],
};

export default AnnotationsTable;
