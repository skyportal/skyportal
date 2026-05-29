import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import BuildIcon from "@mui/icons-material/Build";
import EditIcon from "@mui/icons-material/Edit";
import TextField from "@mui/material/TextField";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";

import Link from "@mui/material/Link";
import SaveIcon from "@mui/icons-material/Save";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ImageAspectRatioIcon from "@mui/icons-material/ImageAspectRatio";
import CircularProgress from "@mui/material/CircularProgress";

import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";

import { makeStyles } from "tss-react/mui";
import { JSONTree } from "react-json-tree";

import { showNotification } from "baselayer/components/Notifications";
import StyledDataGrid from "../StyledDataGrid";
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

const useStyles = makeStyles()((theme) => ({
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
  const { classes } = useStyles();
  const { classes: styles } = useStyles();

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

  const handlePaginationModelChange = (model) => {
    handlePageChange(model.page, model.pageSize);
  };

  const columns = [
    {
      field: "dateobs",
      headerName: "GCN Event",
      flex: 1,
      minWidth: 130,
      valueGetter: (value, row) => row.localization?.dateobs,
    },
    {
      field: "localization_name",
      headerName: "Localization",
      flex: 1,
      minWidth: 130,
      valueGetter: (value, row) => row.localization?.localization_name,
    },
    { field: "created_at", headerName: "Created at", flex: 1, minWidth: 150 },
    { field: "status", headerName: "Status", flex: 1, minWidth: 110 },
    {
      field: "payload",
      headerName: "Payload",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params) => (
        <div style={{ whiteSpace: "nowrap" }}>
          {params.row ? <JSONTree data={params.row.payload} hideRoot /> : ""}
        </div>
      ),
    },
    {
      field: "summarystatistics",
      headerName: "Summary Statistics",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params) => {
        const observationplanRequest = params.row;
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
      },
    },
    {
      field: "skymap",
      headerName: "Skymap",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params) => (
        <div className={classes.localization}>
          <ObservationPlanGlobe
            observationplanRequest={params.row}
            retrieveLocalization
          />
        </div>
      ),
    },
  ];

  return (
    <div className={styles.center}>
      <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
        Observation Plans
      </Typography>
      <Box sx={{ width: "100%" }}>
        <StyledDataGrid
          autoHeight
          rows={observation_plan_requests}
          columns={columns}
          getRowId={(row) => row.id}
          paginationMode="server"
          rowCount={totalMatches}
          paginationModel={{
            page: fetchParams.pageNumber - 1,
            pageSize: fetchParams.numPerPage,
          }}
          onPaginationModelChange={handlePaginationModelChange}
          pageSizeOptions={[1, 10, 25, 50, 100]}
        />
      </Box>
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
  const { classes: styles } = useStyles();
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

  const handlePaginationModelChange = (model) => {
    handlePageChange(model.page, model.pageSize);
  };

  const [openedRows, setOpenedRows] = useState([]);
  const toggleExpand = (id) => {
    setOpenedRows((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
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

  const columns = [
    {
      field: "__expand",
      headerName: "",
      width: 56,
      sortable: false,
      filterable: false,
      hideable: false,
      disableColumnMenu: true,
      colSpan: (value, row) => (row.__detail ? 100 : 1),
      renderCell: (params) => {
        if (params.row.__detail) {
          const request = params.row.__source;
          return (
            <div style={{ width: "100%" }}>
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
                <Grid>
                  <Suspense fallback={<div>Loading plot...</div>}>
                    <AirmassPlot
                      dataUrl={`/api/internal/plot/airmass/objtel/${request.obj.id}/${allocation.telescope.id}`}
                      ephemeris={allocation.ephemeris}
                    />
                  </Suspense>
                </Grid>
                <Grid>
                  <Suspense fallback={<div>Loading plot...</div>}>
                    <VegaPhotometry sourceId={request.obj.id} />
                  </Suspense>
                </Grid>
              </Grid>
            </div>
          );
        }
        const expanded = openedRows.includes(params.row.id);
        return (
          <IconButton
            id="expandable-button"
            size="small"
            aria-label="expand row"
            onClick={() => toggleExpand(params.row.id)}
          >
            {expanded ? <KeyboardArrowDownIcon /> : <KeyboardArrowRightIcon />}
          </IconButton>
        );
      },
    },
    {
      field: "target_name",
      headerName: "Target Name",
      flex: 1,
      minWidth: 120,
      renderCell: (params) => {
        const objid = params.row.obj?.id;
        return (
          <a href={`/source/${objid}`} key={`${objid}_objid`}>
            {objid}
          </a>
        );
      },
    },
    {
      field: "created_at",
      headerName: "Request Date",
      flex: 1,
      minWidth: 150,
    },
    {
      field: "start_date",
      headerName: "Start Date",
      flex: 1,
      minWidth: 150,
      valueGetter: (value, row) => row.payload?.start_date,
    },
    {
      field: "end_date",
      headerName: "End Date",
      flex: 1,
      minWidth: 150,
      valueGetter: (value, row) => row.payload?.end_date,
    },
    {
      field: "status",
      headerName: "Status",
      flex: 1,
      minWidth: 110,
    },
    {
      field: "ra",
      headerName: "RA",
      flex: 1,
      minWidth: 100,
      sortable: false,
      valueGetter: (value, row) => row.obj?.ra,
      renderCell: (params) => (
        <div key={`${params.row.id}_ra`}>
          {params.row.obj?.ra}
          <br />
          {params.row.obj?.ra != null && ra_to_hours(params.row.obj.ra)}
        </div>
      ),
    },
    {
      field: "dec",
      headerName: "Dec",
      flex: 1,
      minWidth: 100,
      sortable: false,
      valueGetter: (value, row) => row.obj?.dec,
      renderCell: (params) => (
        <div key={`${params.row.id}_dec`}>
          {params.row.obj?.dec}
          <br />
          {params.row.obj?.dec != null && dec_to_dms(params.row.obj.dec)}
        </div>
      ),
    },
    {
      field: "redshift",
      headerName: "Redshift",
      flex: 1,
      minWidth: 90,
      valueGetter: (value, row) => row.obj?.redshift,
    },
    {
      field: "requester",
      headerName: "Requester",
      flex: 1,
      minWidth: 120,
      valueGetter: (value, row) => row.requester?.username,
    },
    {
      field: "priority",
      headerName: "Priority",
      flex: 1,
      minWidth: 90,
      valueGetter: (value, row) => row.payload?.priority,
    },
    {
      field: "rise_time_utc",
      headerName: "Rises at (>30deg alt, UT)",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params) =>
        params.row.rise_time_utc != null
          ? new Date(params.row.rise_time_utc).toLocaleTimeString()
          : null,
    },
    {
      field: "set_time_utc",
      headerName: "Sets at (<30deg alt, UT)",
      flex: 1,
      minWidth: 150,
      sortable: false,
      renderCell: (params) =>
        params.row.set_time_utc != null
          ? new Date(params.row.set_time_utc).toLocaleTimeString()
          : null,
    },
    {
      field: "comment",
      headerName: "Comment",
      flex: 1,
      minWidth: 150,
      renderCell: (params) => {
        const request = params.row;
        return (
          <div>
            {request.comment}
            <Tooltip title="Update comment">
              <span aria-label="Update comment">
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
      },
    },
    {
      field: "finder",
      headerName: "Finder",
      flex: 1,
      minWidth: 100,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const request = params.row;
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
      },
    },
    {
      field: "actions",
      headerName: "Actions",
      flex: 1,
      minWidth: 90,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <SimpleMenu request={params.row} key={`${params.row.id}_menu`} />
      ),
    },
  ];

  const displayRows = [];
  (requests || []).forEach((request) => {
    displayRows.push(request);
    if (openedRows.includes(request.id)) {
      displayRows.push({
        id: `${request.id}__detail`,
        __detail: true,
        __source: request,
      });
    }
  });

  return (
    <div className={styles.center}>
      <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
        Targets
      </Typography>
      <Box sx={{ width: "100%" }}>
        <StyledDataGrid
          autoHeight
          rows={displayRows}
          columns={columns}
          getRowId={(row) => row.id}
          getRowHeight={(params) => (params.model.__detail ? "auto" : null)}
          columnBufferPx={3000}
          paginationMode="server"
          rowCount={totalMatches}
          paginationModel={{
            page: fetchParams.pageNumber - 1,
            pageSize: fetchParams.numPerPage,
          }}
          onPaginationModelChange={handlePaginationModelChange}
          pageSizeOptions={[1, 10, 25, 50, 100]}
        />
      </Box>
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
