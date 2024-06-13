import { useDispatch } from "react-redux";
import React, { Suspense, useState } from "react";
import CircularProgress from "@mui/material/CircularProgress";
import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ImageAspectRatioIcon from "@mui/icons-material/ImageAspectRatio";
import Tooltip from "@mui/material/Tooltip";
import EditIcon from "@mui/icons-material/Edit";
import MUIDataTable from "mui-datatables";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import TextField from "@mui/material/TextField";
import SaveIcon from "@mui/icons-material/Save";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";
import Button from "../../Button";
import { dec_to_dms, ra_to_hours } from "../../../units";
import VegaPhotometry from "../../vega/VegaPhotometry";
import ThumbnailList from "../../thumbnail/ThumbnailList";
import SimpleMenu from "./SimpleMenu";
import * as Action from "../../../ducks/allocation";

const AirmassPlot = React.lazy(() => import("../../AirmassPlot"));

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
  editIcon: {
    cursor: "pointer",
    marginLeft: "0.2rem",
  },
});

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
        onClose={() => {
          setDialogOpen(null);
        }}
        style={{ position: "fixed" }}
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


export default AllocationSummaryTable;
