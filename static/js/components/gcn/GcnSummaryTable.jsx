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

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  eventTags: {
    marginLeft: "0.5rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
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

const GcnSummaryTable = ({
  summaries,
  setSelectedGcnSummaryId,
  deleteGcnEventSummary,
  pageNumber = 1,
  numPerPage = 10,
  serverSide = false,
  hideTitle = false,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!summaries || summaries.length === 0) {
    return <p>No entries available...</p>;
  }

  const renderSentBy = (dataIndex) => {
    const summary = summaries[dataIndex];
    return <div>{summary.sent_by.username}</div>;
  };

  const renderGroup = (dataIndex) => {
    const summary = summaries[dataIndex];
    return <div>{summary.group.name}</div>;
  };

  const renderRetrieveDeleteSummary = (dataIndex) => {
    const summary = summaries[dataIndex];
    return (
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <Button
          primary
          onClick={() => {
            setSelectedGcnSummaryId(summary.id);
          }}
          size="small"
          type="submit"
          data-testid={`retrieveSummary_${summary.id}`}
        >
          Retrieve
        </Button>
        <Button
          primary
          onClick={() => {
            deleteGcnEventSummary(summary.id);
          }}
          size="small"
          type="submit"
          data-testid={`deleteSummary_${summary.id}`}
        >
          Delete
        </Button>
      </div>
    );
  };

  const columns = [
    {
      name: "title",
      label: "Title",
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
        customBodyRenderLite: renderRetrieveDeleteSummary,
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
      {summaries ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title={!hideTitle ? "GCN Summaries" : ""}
                data={summaries}
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

GcnSummaryTable.propTypes = {
  summaries: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      created_at: PropTypes.string,
      sent_by: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      group: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
    }),
  ),
  setSelectedGcnSummaryId: PropTypes.func.isRequired,
  deleteGcnEventSummary: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  numPerPage: PropTypes.number,
  hideTitle: PropTypes.bool,
  serverSide: PropTypes.bool,
};

GcnSummaryTable.defaultProps = {
  summaries: null,
  pageNumber: 1,
  numPerPage: 10,
  hideTitle: false,
  serverSide: false,
};

export default GcnSummaryTable;
