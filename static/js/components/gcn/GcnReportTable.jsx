import React from "react";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";

import MUIDataTable from "mui-datatables";

import Button from "../Button";

const useStyles = makeStyles(() => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    overrides: {
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

const GcnReportTable = ({
  reports,
  setSelectedGcnReportId,
  deleteGcnReport,
  pageNumber = 1,
  numPerPage = 10,
  serverSide = false,
  hideTitle = false,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!reports || reports?.length === 0) {
    return <p>No entries available...</p>;
  }

  const renderName = (dataIndex) => {
    const report = reports[dataIndex];
    // return a link to the report that opens in a new tab
    return (
      <a
        href={`/public/reports/gcn/${report?.id}`}
        target="_blank"
        rel="noreferrer"
      >
        {report?.report_name}
      </a>
    );
  };

  const renderSentBy = (dataIndex) => {
    const report = reports[dataIndex];
    return <div>{report?.sent_by?.username}</div>;
  };

  const renderGroup = (dataIndex) => {
    const report = reports[dataIndex];
    return <div>{report?.group?.name}</div>;
  };

  const renderRetrieveDeleteReport = (dataIndex) => {
    const report = reports[dataIndex];
    return (
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <Button
          primary
          onClick={() => {
            setSelectedGcnReportId(report?.id);
          }}
          size="small"
          type="submit"
          data-testid={`retrieveReport_${report?.id}`}
        >
          Retrieve
        </Button>
        <Button
          primary
          onClick={() => {
            deleteGcnReport(report?.id);
          }}
          size="small"
          type="submit"
          data-testid={`deleteReport_${report?.id}`}
        >
          Delete
        </Button>
      </div>
    );
  };

  const columns = [
    {
      name: "report_name",
      label: "Name",
      options: {
        customBodyRenderLite: renderName,
        download: false,
      },
    },
    {
      name: "created_at",
      label: "Time Created",
    },
    {
      name: "User",
      label: "User",
      options: {
        customBodyRenderLite: renderSentBy,
        download: false,
      },
    },
    {
      name: "Group",
      label: "Group",
      options: {
        customBodyRenderLite: renderGroup,
        download: false,
      },
    },
    {
      name: "manage_summary",
      label: "Manage",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderRetrieveDeleteReport,
        download: false,
      },
    },
  ];

  const options = {
    search: true,
    selectableRows: "none",
    elevation: 0,
    page: pageNumber - 1,
    rowsPerPage: numPerPage,
    rowsPerPageOptions: [2, 10, 25, 50, 100],
    jumpToPage: true,
    serverSide,
    pagination: true,
  };

  return (
    <div>
      {reports ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title={!hideTitle ? "GCN Reports" : ""}
                data={reports}
                options={options}
                columns={columns}
              />
            </ThemeProvider>
          </StyledEngineProvider>
        </Paper>
      ) : (
        <CircularProgress />
      )}
    </div>
  );
};

GcnReportTable.propTypes = {
  reports: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      report_name: PropTypes.string,
      created_at: PropTypes.string,
      sent_by: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      group: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
    }),
  ),
  setSelectedGcnReportId: PropTypes.func.isRequired,
  deleteGcnReport: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  numPerPage: PropTypes.number,
  hideTitle: PropTypes.bool,
  serverSide: PropTypes.bool,
};

GcnReportTable.defaultProps = {
  reports: null,
  pageNumber: 1,
  numPerPage: 10,
  hideTitle: false,
  serverSide: false,
};

export default GcnReportTable;
