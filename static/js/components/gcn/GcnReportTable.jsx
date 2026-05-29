import React from "react";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";
import CircularProgress from "@mui/material/CircularProgress";

import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

const useStyles = makeStyles()(() => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
}));

const GcnReportTable = ({
  reports,
  setSelectedGcnReportId,
  deleteGcnReport,
}) => {
  const { classes } = useStyles();

  if (!reports || reports?.length === 0) {
    return <p>No entries available...</p>;
  }

  const renderName = (params) => {
    const report = params.row;
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

  const renderSentBy = (params) => {
    const report = params.row;
    return <div>{report?.sent_by?.username}</div>;
  };

  const renderGroup = (params) => {
    const report = params.row;
    return <div>{report?.group?.name}</div>;
  };

  const renderRetrieveDeleteReport = (params) => {
    const report = params.row;
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
      field: "report_name",
      headerName: "Name",
      flex: 1,
      minWidth: 140,
      renderCell: renderName,
    },
    {
      field: "created_at",
      headerName: "Time Created",
      flex: 1,
      minWidth: 160,
    },
    {
      field: "User",
      headerName: "User",
      flex: 1,
      minWidth: 120,
      renderCell: renderSentBy,
    },
    {
      field: "Group",
      headerName: "Group",
      flex: 1,
      minWidth: 120,
      renderCell: renderGroup,
    },
    {
      field: "manage_summary",
      headerName: "Manage",
      flex: 1,
      minWidth: 180,
      filterable: false,
      renderCell: renderRetrieveDeleteReport,
    },
  ];

  return (
    <div>
      {reports ? (
        <Paper className={classes.container}>
          <Typography variant="h6">GCN Reports</Typography>
          <StyledDataGrid
            autoHeight
            rows={reports}
            columns={columns}
            getRowId={(row) => row.id}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
            }}
            pageSizeOptions={[2, 10, 25, 50, 100]}
            showToolbar
          />
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
};

GcnReportTable.defaultProps = {
  reports: null,
};

export default GcnReportTable;
