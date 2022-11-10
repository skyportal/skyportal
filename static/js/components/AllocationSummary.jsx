import React, { useEffect, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";

import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Grid from "@mui/material/Grid";
import BuildIcon from "@mui/icons-material/Build";

import Link from "@mui/material/Link";
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
      SourceAction.editFollowupRequest({ status }, request.id)
    );
    if (result.status === "success") {
      dispatch(
        showNotification("Follow-up request status successfully updated")
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

const AllocationSummary = ({ route }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const allocation = useSelector((state) => state.allocation);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  // Load the observing run and its assignments if needed
  useEffect(() => {
    dispatch(Action.fetchAllocation(route.id));
  }, [route.id, dispatch]);

  if (!("id" in allocation && allocation.id === parseInt(route.id, 10))) {
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

  const columns = [
    {
      name: "Target Name",
      options: {
        filter: true,
        customBodyRenderLite: renderObjId,
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
  };

  const data = requests?.map((request) => [
    request.obj.id,
    request.status,
    request.obj.ra,
    request.obj.dec,
    request.obj.redshift,
    request.requester.username,
    request.payload.priority,
    request.rise_time_utc,
    request.set_time_utc,
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
