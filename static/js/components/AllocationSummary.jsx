import React, { useEffect, useState, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

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

import MUIDataTable from "mui-datatables";
import { showNotification } from "baselayer/components/Notifications";
import ThumbnailList from "./ThumbnailList";
import { allocationTitle } from "./AllocationPage";
import withRouter from "./withRouter";

import * as SourceAction from "../ducks/source";
import * as Action from "../ducks/allocation";
import { ra_to_hours, dec_to_dms } from "../units";

import VegaPhotometry from "./VegaPhotometry";
import Button from "./Button";
import FormValidationError from "./FormValidationError";

const AirmassPlot = React.lazy(() => import("./AirmassPlot"));

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
        {(request.status === "submitted" ||
          request.status === "not observed" ||
          request.status === "pending") && (
          <MenuItem
            onClick={() => updateRequestStatus("complete")}
            variant="contained"
            key={`${request.id}_done`}
          >
            Mark Observed
          </MenuItem>
        )}
        {(request.status === "submitted" ||
          request.status === "complete" ||
          request.status === "pending") && (
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
  const styles = useStyles();
  const { allocation, totalMatches } = useSelector((state) => state.allocation);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [invalid, setInvalid] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [commentContent, setCommentContent] = useState("");

  useEffect(() => {
    setInvalid(false);
  }, [setInvalid]);

  const [fetchParams, setFetchParams] = useState({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
    sortBy: "created_at",
    sortOrder: "desc",
  });

  const handlePageChange = async (page, numPerPage) => {
    const params = {
      ...fetchParams,
      numPerPage,
      pageNumber: page + 1,
    };
    // Save state for future
    setFetchParams(params);
    await dispatch(Action.fetchAllocation(route.id, params));
  };

  const handleTableChange = async (action, tableState) => {
    if (action === "changePage" || action === "changeRowsPerPage") {
      return handlePageChange(tableState.page, tableState.rowsPerPage);
    }
    return null;
  };

  // Load the observing run and its assignments if needed
  useEffect(() => {
    dispatch(Action.fetchAllocation(route.id, fetchParams));
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

  const { requests } = allocation;

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

  const renderComments = (dataIndex) => {
    const request = requests[dataIndex];

    const handleOpenDialog = () => {
      setCommentContent(request.comments);
      setDialogOpen(true);
    };

    const handleChange = (e) => {
      setCommentContent(e.target.value);
      const value = String(e.target.value).trim();
      setInvalid(!value);
    };

    const handleSubmit = async () => {
      setIsSubmitting(true);
      const json = {
        comments: commentContent,
      };
      dispatch(SourceAction.editFollowupRequestComments(json, request.id));
      setDialogOpen(false);
      setIsSubmitting(false);
    };

    return (
      <div>
        {request.comments}
        <Tooltip title="Update comments">
          <span>
            <EditIcon
              data-testid="updateCommentsIconButton"
              fontSize="small"
              className={styles.editIcon}
              onClick={handleOpenDialog}
            />
          </span>
        </Tooltip>
        <Dialog
          open={dialogOpen}
          fullWidth
          maxWidth="lg"
          onClose={() => {
            setDialogOpen(false);
          }}
          style={{ position: "fixed" }}
        >
          <DialogTitle>Update comments</DialogTitle>
          <DialogContent>
            <div>
              {invalid && (
                <FormValidationError message="Please enter a valid comment" />
              )}
              <TextField
                data-testid="updateCommentsTextfield"
                size="small"
                label="comments"
                value={commentContent}
                name="comments"
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
                data-testid="updateCommentsSubmitButton"
                disabled={isSubmitting || invalid}
              >
                Save
              </Button>
            </div>
          </DialogContent>
        </Dialog>
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
      name: "Comments",
      options: {
        filter: true,
        customBodyRenderLite: renderComments,
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
    rowsPerPageOptions: [10, 25, 50, 100],
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
    request.comments,
    null,
    null,
  ]);

  return (
    <div className={styles.center}>
      <Typography variant="h4" gutterBottom color="textSecondary">
        Plan for:{" "}
        <b>
          {allocationTitle(allocation, instrumentList, telescopeList, groups)}
        </b>
      </Typography>
      <MUIDataTable
        title="Targets"
        columns={columns}
        data={data}
        options={options}
      />
    </div>
  );
};

AllocationSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(AllocationSummary);
