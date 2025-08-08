import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";

import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Grid from "@mui/material/Grid";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import EditIcon from "@mui/icons-material/Edit";
import TextField from "@mui/material/TextField";

import SaveIcon from "@mui/icons-material/Save";
import CircularProgress from "@mui/material/CircularProgress";
import Box from "@mui/material/Box";

import { JSONTree } from "react-json-tree";

import MUIDataTable from "mui-datatables";
import { showNotification } from "baselayer/components/Notifications";

import * as SourceAction from "../../ducks/source";
import * as Action from "../../ducks/allocation";
import * as ObservationPlansAction from "../../ducks/observationPlans";

import ThumbnailList from "../thumbnail/ThumbnailList";
import withRouter from "../withRouter";
import ObservationPlanGlobe from "../observation_plan/ObservationPlanGlobe";
import ObservationPlanSummaryStatistics from "../observation_plan/ObservationPlanSummaryStatistics";
import VegaPhotometry from "../plot/VegaPhotometry";
import Button from "../Button";
import {
  renderTargetName,
  renderStatus,
  renderRA,
  renderDec,
  renderRise,
  renderSet,
  renderFinderButton,
  ActionsMenu,
} from "../../utils/displaySummary";
import Spinner from "../Spinner";

const AirmassPlot = React.lazy(() => import("../plot/AirmassPlot"));

const DEFAULT_NUM_PER_PAGE = 10;

function allocationTitle(allocation, instrumentList, telescopeList) {
  const instrument = instrumentList?.filter(
    (i) => i.id === allocation?.instrument_id,
  )[0];
  const telescope = telescopeList?.filter(
    (t) => t.id === instrument?.telescope_id,
  )[0];

  return (
    <b>
      {instrument?.name || <CircularProgress size={25} />}/
      {telescope?.nickname || <CircularProgress size={25} />}
    </b>
  );
}

const AllocationSummary = ({ route }) => {
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);
  const { allocation, totalMatches: totalMatchesAllocations } = useSelector(
    (state) => state.allocation,
  );
  const {
    observation_plan_requests,
    totalMatches: totalMatchesObservationPlans,
  } = useSelector((state) => state.observation_plans);

  const [fetchAllocationParams, setFetchAllocationParams] = useState({
    pageNumber: 1,
    numPerPage: DEFAULT_NUM_PER_PAGE,
    sortBy: "created_at",
    sortOrder: "desc",
  });

  const [fetchObservationPlansParams, setFetchObservationPlansParams] =
    useState({
      pageNumber: 1,
      numPerPage: DEFAULT_NUM_PER_PAGE,
      sortBy: "created_at",
      sortOrder: "desc",
    });

  // Load the allocation and its follow-up requests if needed
  useEffect(() => {
    dispatch(Action.fetchAllocation(route.id, fetchAllocationParams));
  }, [route.id, dispatch]);

  // Load the allocation and its observation plans if needed
  useEffect(() => {
    dispatch(
      ObservationPlansAction.fetchAllocationObservationPlans(
        route.id,
        fetchObservationPlansParams,
      ),
    );
  }, [route.id, dispatch]);

  if (allocation?.id !== parseInt(route.id, 10)) return <Spinner />;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Typography variant="h1" gutterBottom color="secondary.contrastText">
        Plan for:{" "}
        {allocationTitle(allocation, instrumentList, telescopeList, groups)}
      </Typography>
      <AllocationSummaryTable
        allocation={allocation}
        totalMatches={totalMatchesAllocations}
        fetchParams={fetchAllocationParams}
        setFetchParams={setFetchAllocationParams}
      />
      {observation_plan_requests && (
        <AllocationObservationPlansTable
          observation_plan_requests={observation_plan_requests}
          totalMatches={totalMatchesObservationPlans}
          fetchParams={fetchObservationPlansParams}
          setFetchParams={setFetchObservationPlansParams}
        />
      )}
    </Box>
  );
};

AllocationSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

const AllocationObservationPlansTable = ({
  observation_plan_requests,
  totalMatches,
  fetchParams,
  setFetchParams,
}) => {
  const dispatch = useDispatch();
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

  const renderPayload = (dataIndex) => {
    const request = observation_plan_requests[dataIndex];
    if (!request?.payload) return null;

    return (
      <Box sx={{ whiteSpace: "nowrap" }}>
        <JSONTree data={request.payload} hideRoot />
      </Box>
    );
  };

  const renderSummaryStatistics = (dataIndex) => {
    const request = observation_plan_requests[dataIndex];
    if (request.status === "running") return <CircularProgress />;

    return (
      <ObservationPlanSummaryStatistics observationPlanRequest={request} />
    );
  };

  const columns = [
    { name: "localization.dateobs", label: "GCN Event" },
    { name: "localization.localization_name", label: "Localization" },
    { name: "created_at", label: "Created at" },
    { name: "status", label: "Status" },
    {
      name: "payload",
      label: "Payload",
      options: { customBodyRenderLite: renderPayload },
    },
    {
      name: "statistics",
      label: "Summary Statistics",
      options: { customBodyRenderLite: renderSummaryStatistics },
    },
    {
      name: "skymap",
      label: "Skymap",
      options: {
        customBodyRenderLite: (dataIndex) => (
          <ObservationPlanGlobe
            observationplanRequest={observation_plan_requests[dataIndex]}
            retrieveLocalization
          />
        ),
      },
    },
  ];

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
    <MUIDataTable
      title="Observation Plans"
      columns={columns}
      data={observation_plan_requests}
      options={options}
    />
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
      payload: PropTypes.arrayOf(PropTypes.shape({})),
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

const AllocationSummaryTable = ({
  allocation,
  totalMatches,
  fetchParams,
  setFetchParams,
}) => {
  const dispatch = useDispatch();
  const { requests } = allocation;

  const [dialogOpen, setDialogOpen] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [commentContent, setCommentContent] = useState("");

  const handlePageChange = async (page, numPerPage) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future
    setFetchParams(params);
    await dispatch(Action.fetchAllocation(allocation.id, params));
  };

  const handleTableChange = async (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      return handlePageChange(tableState.page, tableState.rowsPerPage);
    }
    return null;
  };

  const renderPullOutRow = (rowData, rowMeta) => {
    if (!allocation) return <CircularProgress />;

    const colSpan = rowData.length + 1;
    const request = requests[rowMeta.dataIndex];
    return (
      <TableRow>
        <TableCell
          style={{ paddingBottom: 0, paddingTop: 0 }}
          colSpan={colSpan}
        >
          <Grid container direction="row" spacing={3} alignItems="center">
            <ThumbnailList
              thumbnails={request.obj.thumbnails}
              ra={request.obj.ra}
              dec={request.obj.dec}
              useGrid={false}
            />
            <Grid item>
              <Suspense fallback={<div>Loading plot...</div>}>
                <AirmassPlot
                  dataUrl={`/api/internal/plot/airmass/objtel/${request.obj.id}/${allocation.telescope.id}`}
                  ephemeris={allocation.ephemeris}
                />
              </Suspense>
            </Grid>
            <Grid item>
              <Suspense fallback={<div>Loading plot...</div>}>
                <VegaPhotometry sourceId={request.obj.id} />
              </Suspense>
            </Grid>
          </Grid>
        </TableCell>
      </TableRow>
    );
  };

  const handleOpenDialog = (id, comment) => {
    setCommentContent(comment);
    setDialogOpen(id);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    const json = {
      comment: commentContent,
    };
    dispatch(Action.editFollowupRequestComment(json, dialogOpen));
    setDialogOpen(null);
    setIsSubmitting(false);
  };

  const renderComment = (dataIndex) => {
    const request = requests[dataIndex];
    return (
      <div>
        {request.comment}
        <Tooltip title="Update comment">
          <IconButton
            size="small"
            color="primary"
            onClick={() => handleOpenDialog(request.id, request.comment)}
          >
            <EditIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </div>
    );
  };

  const updateRequestStatus = async (request, status) => {
    const result = await dispatch(
      SourceAction.editFollowupRequest({ status }, request.id),
    );
    if (result.status === "success") {
      dispatch(
        showNotification("Follow-up request status updated successfully"),
      );
    }
  };

  const columns = [
    {
      name: "Target Name",
      options: {
        filter: true,
        customBodyRenderLite: (dataIndex) =>
          renderTargetName(requests[dataIndex]),
      },
    },
    {
      name: "Request Date",
      options: {
        filter: true,
      },
    },
    {
      name: "Start Date",
      options: {
        filter: true,
      },
    },
    {
      name: "End Date",
      options: {
        filter: true,
      },
    },
    {
      name: "Status",
      options: {
        filter: true,
        setCellProps: () => ({
          style: {
            minWidth: "250px",
          },
        }),
        customBodyRenderLite: (dataIndex) => renderStatus(requests[dataIndex]),
      },
    },
    {
      name: "RA",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) => renderRA(requests[dataIndex]),
      },
    },
    {
      name: "Dec",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) => renderDec(requests[dataIndex]),
      },
    },
    {
      name: "Redshift",
      options: {
        filter: false,
      },
    },
    {
      name: "Requester",
      options: {
        filter: true,
      },
    },
    {
      name: "Priority",
      options: {
        filter: true,
      },
    },
    {
      name: "Rises at (>30deg alt, UT)",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) => renderRise(requests[dataIndex]),
      },
    },
    {
      name: "Sets at (<30deg alt, UT)",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) => renderSet(requests[dataIndex]),
      },
    },
    {
      name: "Comment",
      options: {
        filter: true,
        customBodyRenderLite: renderComment,
      },
    },
    {
      name: "Finder",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) =>
          renderFinderButton(requests[dataIndex]),
      },
    },
    {
      name: "Actions",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) => (
          <ActionsMenu
            item={requests[dataIndex]}
            updateFunction={updateRequestStatus}
          />
        ),
      },
    },
  ];

  const options = {
    draggableColumns: { enabled: true },
    expandableRows: true,
    renderExpandableRow: renderPullOutRow,
    selectableRows: "none",
    onTableChange: handleTableChange,
    count: totalMatches,
    page: fetchParams.pageNumber - 1,
    rowsPerPage: fetchParams.numPerPage,
    rowsPerPageOptions: [1, 10, 25, 50, 100],
    jumpToPage: true,
    serverSide: true,
    pagination: true,
  };

  const data = requests?.map((request) => [
    request.obj.id,
    request.created_at,
    request.payload?.start_date,
    request.payload?.end_date,
    request.status,
    request.obj.ra,
    request.obj.dec,
    request.obj.redshift,
    request.requester?.username,
    request.payload.priority,
    request.rise_time_utc,
    request.set_time_utc,
    request.comment,
    null,
    null,
  ]);

  return (
    <>
      <MUIDataTable
        title="Targets"
        columns={columns}
        data={data}
        options={options}
      />
      <Dialog
        open={dialogOpen != null}
        fullWidth
        maxWidth="lg"
        onClose={() => setDialogOpen(null)}
      >
        <DialogTitle>Update comment</DialogTitle>
        <DialogContent>
          <TextField
            data-testid="updateCommentTextfield"
            size="small"
            label="comment"
            value={commentContent || ""}
            name="comment"
            minRows={2}
            fullWidth
            multiline
            onChange={(e) => setCommentContent(e.target.value)}
            variant="outlined"
            sx={{ mt: 1, mb: 2 }}
          />
          <Button
            secondary
            onClick={handleSubmit}
            endIcon={<SaveIcon />}
            size="large"
            data-testid="updateCommentSubmitButton"
            disabled={isSubmitting}
          >
            Save
          </Button>
        </DialogContent>
      </Dialog>
    </>
  );
};

AllocationSummaryTable.propTypes = {
  allocation: PropTypes.shape({
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
    telescope: PropTypes.shape({
      id: PropTypes.number,
    }),
    ephemeris: PropTypes.shape({}),
    requests: PropTypes.arrayOf(
      PropTypes.shape({
        obj: PropTypes.shape({
          id: PropTypes.string,
          ra: PropTypes.number,
          dec: PropTypes.number,
          redshift: PropTypes.number,
        }),
        status: PropTypes.string,
        created_at: PropTypes.string,
        id: PropTypes.number,
        comment: PropTypes.string,
        payload: PropTypes.shape({
          start_date: PropTypes.string,
          end_date: PropTypes.string,
          priority: PropTypes.number,
        }),
        rise_time_utc: PropTypes.string,
        set_time_utc: PropTypes.string,
        requester: PropTypes.shape({
          username: PropTypes.string,
        }),
      }),
    ),
  }).isRequired,
  totalMatches: PropTypes.number.isRequired,
  fetchParams: PropTypes.shape({
    pageNumber: PropTypes.number,
    numPerPage: PropTypes.number,
    sortBy: PropTypes.string,
    sortOrder: PropTypes.string,
  }).isRequired,
  setFetchParams: PropTypes.func.isRequired,
};

export default withRouter(AllocationSummary);
