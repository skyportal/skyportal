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
import BuildIcon from "@mui/icons-material/Build";
import EditIcon from "@mui/icons-material/Edit";
import TextField from "@mui/material/TextField";

import Link from "@mui/material/Link";
import SaveIcon from "@mui/icons-material/Save";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ImageAspectRatioIcon from "@mui/icons-material/ImageAspectRatio";
import CircularProgress from "@mui/material/CircularProgress";

import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

import makeStyles from "@mui/styles/makeStyles";
import { JSONTree } from "react-json-tree";

import MUIDataTable from "mui-datatables";
import { showNotification } from "baselayer/components/Notifications";
import ThumbnailList from "../thumbnail/ThumbnailList";
import { allocationTitle } from "./AllocationPage";
import withRouter from "../withRouter";

import * as SourceAction from "../../ducks/source";
import * as Action from "../../ducks/allocation";
import * as ObservationPlansAction from "../../ducks/observationPlans";
import { dec_to_dms, ra_to_hours } from "../../units";

import ObservationPlanGlobe from "../observation_plan/ObservationPlanGlobe";
import ObservationPlanSummaryStatistics from "../observation_plan/ObservationPlanSummaryStatistics";
import VegaPhotometry from "../plot/VegaPhotometry";
import Button from "../Button";

const AirmassPlot = React.lazy(() => import("../plot/AirmassPlot"));

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  displayInlineBlock: {
    display: "inline-block",
  },
  center: {
    margin: "auto",
    padding: "0.625rem",
  },
  editIcon: {
    cursor: "pointer",
    marginLeft: "0.2rem",
  },
}));

const SimpleMenu = ({ request }) => {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const dispatch = useDispatch();

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const updateRequestStatus = async (status) => {
    handleClose();
    const result = await dispatch(
      SourceAction.editFollowupRequest({ status }, request.id),
    );
    if (result.status === "success") {
      dispatch(
        showNotification("Follow-up request status successfully updated"),
      );
    }
  };

  return (
    <div>
      <IconButton
        aria-controls="simple-menu"
        aria-haspopup="true"
        onClick={handleClick}
        variant="contained"
        size="large"
      >
        <BuildIcon />
      </IconButton>
      <Menu
        id="simple-menu"
        anchorEl={anchorEl}
        keepMounted
        open={Boolean(anchorEl)}
        onClose={handleClose}
      >
        {(request.status.startsWith("submitted") ||
          request.status.startsWith("not observed") ||
          request.status.startsWith("pending")) && (
          <MenuItem
            onClick={() => updateRequestStatus("complete")}
            variant="contained"
            key={`${request.id}_done`}
          >
            Mark Observed
          </MenuItem>
        )}
        {(request.status.startsWith("submitted") ||
          request.status.startsWith("complete") ||
          request.status.startsWith("pending")) && (
          <MenuItem
            onClick={() => updateRequestStatus("not observed")}
            variant="contained"
            key={`${request.id}_notdone`}
          >
            Mark Not Observed
          </MenuItem>
        )}
        {(request.status === "complete" ||
          request.status === "not observed") && (
          <MenuItem
            onClick={() => updateRequestStatus("pending")}
            variant="contained"
            key={`${request.id}_pending`}
          >
            Mark Pending
          </MenuItem>
        )}
        {request.status === "complete" && (
          <MenuItem key={`${request.id}_upload_spec`} onClick={handleClose}>
            <Link
              href={`/upload_spectrum/${request.obj.id}`}
              underline="none"
              color="textPrimary"
            >
              Upload Spectrum
            </Link>
          </MenuItem>
        )}
        {request.status === "complete" && (
          <MenuItem
            key={`${request.id}_upload_phot`}
            variant="contained"
            onClick={handleClose}
          >
            <Link
              href={`/upload_photometry/${request.obj.id}`}
              underline="none"
              color="textPrimary"
            >
              Upload Photometry
            </Link>
          </MenuItem>
        )}
      </Menu>
    </div>
  );
};

SimpleMenu.propTypes = {
  request: PropTypes.shape({
    status: PropTypes.string,
    id: PropTypes.number,
    obj: PropTypes.shape({
      id: PropTypes.string,
    }).isRequired,
  }).isRequired,
};

const defaultNumPerPage = 10;

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
    numPerPage: defaultNumPerPage,
    sortBy: "created_at",
    sortOrder: "desc",
  });

  const [fetchObservationPlansParams, setFetchObservationPlansParams] =
    useState({
      pageNumber: 1,
      numPerPage: defaultNumPerPage,
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

  if (
    !(
      allocation &&
      "id" in allocation &&
      allocation.id === parseInt(route.id, 10)
    )
  ) {
    // Don't need to do this for assignments -- we can just let the page be blank for a short time
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  return (
    <div>
      <div>
        <Typography variant="h4" gutterBottom color="textSecondary">
          Plan for:{" "}
          <b>
            {allocationTitle(allocation, instrumentList, telescopeList, groups)}
          </b>
        </Typography>
      </div>
      <div>
        <AllocationSummaryTable
          allocation={allocation}
          totalMatches={totalMatchesAllocations}
          fetchParams={fetchAllocationParams}
          setFetchParams={setFetchAllocationParams}
        />
      </div>
      <div>
        <AllocationObservationPlansTable
          observation_plan_requests={observation_plan_requests}
          totalMatches={totalMatchesObservationPlans}
          fetchParams={fetchObservationPlansParams}
          setFetchParams={setFetchObservationPlansParams}
        />
      </div>
    </div>
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
  const classes = useStyles();
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
      <div className={classes.localization}>
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

const AllocationSummaryTable = ({
  allocation,
  totalMatches,
  fetchParams,
  setFetchParams,
}) => {
  const dispatch = useDispatch();
  const styles = useStyles();
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

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderPullOutRow = (rowData, rowMeta) => {
    if (allocation === undefined) {
      return (
        <div>
          <CircularProgress color="secondary" />
        </div>
      );
    }

    const colSpan = rowData.length + 1;
    const request = requests[rowMeta.dataIndex];

    return (
      <TableRow>
        <TableCell
          style={{ paddingBottom: 0, paddingTop: 0 }}
          colSpan={colSpan}
        >
          <Grid
            container
            direction="row"
            spacing={3}
            justifyContent="center"
            alignItems="center"
          >
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

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderObjId = (dataIndex) => {
    const objid = requests[dataIndex].obj.id;
    return (
      <a href={`/source/${objid}`} key={`${objid}_objid`}>
        {objid}
      </a>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderRA = (dataIndex) => {
    const request = requests[dataIndex];
    return (
      <div key={`${request.id}_ra`}>
        {request.obj.ra}
        <br />
        {ra_to_hours(request.obj.ra)}
      </div>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderDec = (dataIndex) => {
    const request = requests[dataIndex];
    return (
      <div key={`${request.id}_dec`}>
        {request.obj.dec}
        <br />
        {dec_to_dms(request.obj.dec)}
      </div>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderFinderButton = (dataIndex) => {
    const request = requests[dataIndex];
    return (
      <>
        <IconButton size="small" key={`${request.id}_actions`}>
          <Link href={`/api/sources/${request.obj.id}/finder`}>
            <PictureAsPdfIcon />
          </Link>
        </IconButton>
        <IconButton size="small" key={`${request.id}_actions_int`}>
          <Link
            href={`/source/${request.obj.id}/finder`}
            rel="noopener noreferrer"
            target="_blank"
          >
            <ImageAspectRatioIcon />
          </Link>
        </IconButton>
      </>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderActionsButton = (dataIndex) => {
    const request = requests[dataIndex];
    return <SimpleMenu request={request} key={`${request.id}_menu`} />;
  };

  const handleOpenDialog = (id, comment) => {
    setCommentContent(comment);
    setDialogOpen(id);
  };

  const handleChange = (e) => {
    setCommentContent(e.target.value);
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
          <span>
            <EditIcon
              data-testid="updateCommentIconButton"
              fontSize="small"
              className={styles.editIcon}
              onClick={() => {
                handleOpenDialog(request.id, request.comment);
              }}
            />
          </span>
        </Tooltip>
      </div>
    );
  };

  const columns = [
    {
      name: "Target Name",
      options: {
        filter: true,
        customBodyRenderLite: renderObjId,
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
      },
    },
    {
      name: "RA",
      options: {
        filter: false,
        customBodyRenderLite: renderRA,
      },
    },
    {
      name: "Dec",
      options: {
        filter: false,
        customBodyRenderLite: renderDec,
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
        customBodyRenderLite: (dataIndex) =>
          new Date(requests[dataIndex].rise_time_utc).toLocaleTimeString(),
      },
    },
    {
      name: "Sets at (<30deg alt, UT)",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) =>
          new Date(requests[dataIndex].set_time_utc).toLocaleTimeString(),
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
        customBodyRenderLite: renderFinderButton,
      },
    },
    {
      name: "Actions",
      options: {
        filter: false,
        customBodyRenderLite: renderActionsButton,
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
    <div className={styles.center}>
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
          <div>
            <TextField
              data-testid="updateCommentTextfield"
              size="small"
              label="comment"
              value={commentContent || ""}
              name="comment"
              minRows={2}
              fullWidth
              multiline
              onChange={(e) => handleChange(e)}
              variant="outlined"
            />
          </div>
          <p />
          <div className={styles.saveButton}>
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
          </div>
        </DialogContent>
      </Dialog>
    </div>
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
    ephemeris: PropTypes.string,
    requests: PropTypes.arrayOf(
      PropTypes.shape({
        obj: PropTypes.shape({
          id: PropTypes.string,
          ra: PropTypes.number,
          dec: PropTypes.number,
          redshift: PropTypes.number,
        }),
        status: PropTypes.bool,
        created_at: PropTypes.string,
        id: PropTypes.number,
        comment: PropTypes.string,
        payload: PropTypes.shape({
          start_date: PropTypes.string,
          end_date: PropTypes.number,
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
