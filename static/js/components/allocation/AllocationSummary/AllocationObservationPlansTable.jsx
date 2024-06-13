import { useDispatch } from "react-redux";
import { JSONTree } from "react-json-tree";
import CircularProgress from "@mui/material/CircularProgress";
import MUIDataTable from "mui-datatables";
import React from "react";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import ObservationPlanGlobe from "../../ObservationPlanGlobe";
import * as ObservationPlansAction from "../../../ducks/observationPlans";
import ObservationPlanSummaryStatistics from "../../ObservationPlanSummaryStatistics";

const useStyles = makeStyles({
  // chip: {
  //   margin: theme.spacing(0.5),
  // },
  // displayInlineBlock: {
  //   display: "inline-block",
  // },
  center: {
    margin: "auto",
    padding: "0.625rem",
  },
  // editIcon: {
  //   cursor: "pointer",
  //   marginLeft: "0.2rem",
  // },
});

const AllocationObservationPlansTable = ({
  observation_plan_requests,
  totalMatches,
  fetchParams,
  setFetchParams,
}) => {
  const dispatch = useDispatch();
  const styles = useStyles();

  const handlePageChange = async (page, numPerPage) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future
    setFetchParams(params);
    await dispatch(
      ObservationPlansAction.fetchAllocationObservationPlans(
        observation_plan_requests[0].allocation_id,
        params,
      ),
    );
  };

  const handleTableChange = async (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      return handlePageChange(tableState.page, tableState.rowsPerPage);
    }
    return null;
  };

  const columns = [
    { name: "localization.dateobs", label: "GCN Event" },
    { name: "localization.localization_name", label: "Localization" },
    { name: "created_at", label: "Created at" },
    { name: "status", label: "Status" },
  ];

  const renderPayload = (dataIndex) => {
    const observationplanRequest = observation_plan_requests[dataIndex];

    const cellStyle = {
      whiteSpace: "nowrap",
    };

    return (
      <div style={cellStyle}>
        {observationplanRequest ? (
          <JSONTree data={observationplanRequest.payload} hideRoot />
        ) : (
          ""
        )}
      </div>
    );
  };
  columns.push({
    name: "payload",
    label: "Payload",
    options: {
      customBodyRenderLite: renderPayload,
    },
  });

  const renderSummaryStatistics = (dataIndex) => {
    const observationplanRequest = observation_plan_requests[dataIndex];

    return (
      <div>
        {observationplanRequest.status === "running" ? (
          <div>
            <CircularProgress />
          </div>
        ) : (
          <div>
            <ObservationPlanSummaryStatistics
              observationplanRequest={observationplanRequest}
            />
          </div>
        )}
      </div>
    );
  };
  columns.push({
    name: "summarystatistics",
    label: "Summary Statistics",
    options: {
      customBodyRenderLite: renderSummaryStatistics,
    },
  });

  const renderLocalization = (dataIndex) => {
    const observationplanRequest = observation_plan_requests[dataIndex];

    return (
      <div className={styles.localization}>
        <ObservationPlanGlobe
          observationplanRequest={observationplanRequest}
          retrieveLocalization
        />
      </div>
    );
  };
  columns.push({
    name: "skymap",
    label: "Skymap",
    options: {
      customBodyRenderLite: renderLocalization,
    },
  });

  const options = {
    draggableColumns: { enabled: true },
    selectableRows: "none",
    onTableChange: handleTableChange,
    count: totalMatches,
    page: fetchParams.pageNumber - 1,
    rowsPerPage: fetchParams.numPerPage,
    rowsPerPageOptions: [1, 10, 25, 50, 100],
    enableNestedDataAccess: ".",
    jumpToPage: true,
    serverSide: true,
    pagination: true,
  };

  return (
    <div className={styles.center}>
      <MUIDataTable
        title="Observation Plans"
        columns={columns}
        data={observation_plan_requests}
        options={options}
      />
    </div>
  );
};

AllocationObservationPlansTable.propTypes = {
  observation_plan_requests: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      requester: PropTypes.shape({
        id: PropTypes.number,
        username: PropTypes.string,
      }),
      instrument: PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
      status: PropTypes.string,
      allocation: PropTypes.shape({
        group: PropTypes.shape({
          name: PropTypes.string,
        }),
      }),
      allocation_id: PropTypes.number,
      // eslint-disable-next-line react/forbid-prop-types
      payload: PropTypes.arrayOf(PropTypes.any),
    }),
  ).isRequired,
  totalMatches: PropTypes.number.isRequired,
  fetchParams: PropTypes.shape({
    pageNumber: PropTypes.number,
    numPerPage: PropTypes.number,
    sortBy: PropTypes.string,
    sortOrder: PropTypes.string,
  }).isRequired,
  setFetchParams: PropTypes.func.isRequired,
};

export default AllocationObservationPlansTable;
