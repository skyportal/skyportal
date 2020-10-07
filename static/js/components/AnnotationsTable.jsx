import React from "react";
import PropTypes from "prop-types";

import {
  makeStyles,
  createMuiTheme,
  MuiThemeProvider,
  useTheme,
} from "@material-ui/core/styles";
import MUIDataTable from "mui-datatables";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { getAnnotationValueString } from "./CandidateAnnotationsList";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  container: {
    [theme.breakpoints.up("sm")]: {
      minWidth: 350,
    },
    width: "100%",
  },
}));

// Tweak responsive column widths
const getMuiTheme = (theme) =>
  createMuiTheme({
    overrides: {
      MUIDataTableBodyCell: {
        root: {
          padding: `${theme.spacing(0.5)}px 0 ${theme.spacing(
            0.5
          )}px ${theme.spacing(0.5)}px`,
        },
      },
      MuiIconButton: {
        root: {
          padding: "0.5rem",
        },
      },
    },
  });

const AnnotationsTable = ({ annotations }) => {
  const classes = useStyles();
  const theme = useTheme();
  const renderValue = (value) => getAnnotationValueString(value);
  const renderTime = (created_at) => dayjs().to(dayjs.utc(`${created_at}Z`));
  // Curate data
  const tableData = [];
  annotations.forEach((annotation) => {
    const { origin, data, author_info, created_at } = annotation;
    Object.entries(data).forEach(([key, value]) => {
      tableData.push({ origin, key, value, author_info, created_at });
    });
  });

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
      name: "author_info.username",
      label: "Author",
    },
    {
      name: "created_at",
      label: "Created",
      options: {
        customBodyRender: renderTime,
      },
    },
  ];

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
      <MuiThemeProvider theme={getMuiTheme(theme)}>
        <MUIDataTable columns={columns} data={tableData} options={options} />
      </MuiThemeProvider>
    </div>
  );
};

AnnotationsTable.propTypes = {
  annotations: PropTypes.arrayOf(
    PropTypes.shape({
      origin: PropTypes.string.isRequired,
      data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
      author_info: PropTypes.shape({
        username: PropTypes.string.isRequired,
      }).isRequired,
      created_at: PropTypes.string.isRequired,
    })
  ).isRequired,
};

export default AnnotationsTable;
