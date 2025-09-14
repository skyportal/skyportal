import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";

import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
import BuildIcon from "@mui/icons-material/Build";
import CloudIcon from "@mui/icons-material/Cloud";

import Link from "@mui/material/Link";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ImageAspectRatioIcon from "@mui/icons-material/ImageAspectRatio";
import CircularProgress from "@mui/material/CircularProgress";

import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";

import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";

import makeStyles from "@mui/styles/makeStyles";

import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import AssignmentForm from "../observing_run/AssignmentForm";
import ThumbnailList from "../thumbnail/ThumbnailList";
import { observingRunTitle } from "./AssignmentForm";
import { ObservingRunStarList } from "../StarList";
import withRouter from "../withRouter";

import * as SourceAction from "../../ducks/source";
import * as Action from "../../ducks/observingRun";
import { dec_to_dms, ra_to_hours } from "../../units";

import SkyCam from "../SkyCam";
import VegaPhotometry from "../plot/VegaPhotometry";
import Spinner from "../Spinner";

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
}));

function getStatusColors(status) {
  // if it starts with success, green
  if (status.startsWith("complete")) {
    return ["black", "MediumAquaMarine"];
  }
  // if any of these strings are present, yellow
  if (status.includes("not observed")) {
    return ["black", "Orange"];
  }
  // if it starts with error, red
  if (status.startsWith("error")) {
    return ["white", "Crimson"];
  }
  // else grey
  return ["black", "LightGrey"];
}

const SimpleMenu = ({ assignment }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const dispatch = useDispatch();

  const { observingRunList } = useSelector((state) => state.observingRuns);

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const updateAssignmentStatus = (status) => () => {
    handleClose();
    return dispatch(SourceAction.editAssignment({ status }, assignment.id));
  };

  const openDialog = () => {
    setDialogOpen(true);
  };
  const closeDialog = () => {
    setDialogOpen(false);
  };

  const reassignAssignment = () => () => {
    handleClose();
    openDialog();
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
        {(assignment.status === "pending" ||
          assignment.status === "not observed") && (
          <MenuItem
            onClick={updateAssignmentStatus("complete")}
            variant="contained"
            key={`${assignment.id}_done`}
          >
            Mark Observed
          </MenuItem>
        )}
        {(assignment.status === "pending" ||
          assignment.status === "complete") && (
          <MenuItem
            onClick={updateAssignmentStatus("not observed")}
            variant="contained"
            key={`${assignment.id}_notdone`}
          >
            Mark Not Observed
          </MenuItem>
        )}
        {(assignment.status === "complete" ||
          assignment.status === "not observed") && (
          <MenuItem
            onClick={updateAssignmentStatus("pending")}
            variant="contained"
            key={`${assignment.id}_pending`}
          >
            Mark Pending
          </MenuItem>
        )}
        {assignment.status === "not observed" && (
          <MenuItem
            onClick={reassignAssignment()}
            variant="contained"
            key={`${assignment.id}_reassign`}
          >
            Reassign
          </MenuItem>
        )}
        {assignment.status === "complete" && (
          <MenuItem key={`${assignment.id}_upload_spec`} onClick={handleClose}>
            <Link
              href={`/upload_spectrum/${assignment.obj_id}`}
              underline="none"
              color="textPrimary"
            >
              Upload Spectrum
            </Link>
          </MenuItem>
        )}
        {assignment.status === "complete" && (
          <MenuItem
            key={`${assignment.id}_upload_phot`}
            variant="contained"
            onClick={handleClose}
          >
            <Link
              href={`/upload_photometry/${assignment.obj_id}`}
              underline="none"
              color="textPrimary"
            >
              Upload Photometry
            </Link>
          </MenuItem>
        )}
      </Menu>
      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="md">
        <DialogTitle>Reassign to Observing Run</DialogTitle>
        <DialogContent dividers>
          <AssignmentForm
            obj_id={assignment.obj_id}
            observingRunList={observingRunList}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

SimpleMenu.propTypes = {
  assignment: PropTypes.shape({
    status: PropTypes.string,
    id: PropTypes.number,
    obj_id: PropTypes.string,
  }).isRequired,
};

const RunSummary = ({ route }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const observingRun = useSelector((state) => state.observingRun);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);
  const [dialog, setDialog] = useState(false);

  const closeDialog = () => {
    setDialog(false);
  };

  useEffect(() => {
    dispatch(Action.fetchObservingRun(route.id));
  }, [route.id, dispatch]);

  if (observingRun?.id !== parseInt(route.id, 10)) return <Spinner />;

  const assignments = observingRun?.assignments || [];

  const notObservedFunction = () => {
    dispatch(Action.putObservingRunNotObserved(observingRun.id)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(
            showNotification("Observing run assignments set to not observed"),
          );
          closeDialog();
        }
      },
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderPullOutRow = (rowData, rowMeta) => {
    if (observingRun === undefined) {
      return (
        <div>
          <CircularProgress color="secondary" />
        </div>
      );
    }

    const colSpan = rowData.length + 1;
    const assignment = assignments[rowMeta.dataIndex];

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
              thumbnails={assignment.obj.thumbnails}
              ra={assignment.obj.ra}
              dec={assignment.obj.dec}
              useGrid={false}
            />
            <Grid item>
              <Suspense fallback={<div>Loading plot...</div>}>
                <AirmassPlot
                  dataUrl={`/api/internal/plot/airmass/assignment/${assignment.id}`}
                  ephemeris={observingRun.ephemeris}
                />
              </Suspense>
            </Grid>
            <Grid item>
              <Suspense fallback={<div>Loading plot...</div>}>
                <VegaPhotometry sourceId={assignment.obj.id} />
              </Suspense>
            </Grid>
          </Grid>
        </TableCell>
      </TableRow>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderObjId = (dataIndex) => {
    const objid = assignments[dataIndex].obj.id;
    return (
      <a href={`/source/${objid}`} key={`${objid}_objid`}>
        {objid}
      </a>
    );
  };

  const renderStatus = (dataIndex) => {
    const { id, status } = assignments[dataIndex];
    const colors = getStatusColors(status);
    return (
      <Typography
        variant="body2"
        style={{
          backgroundColor: colors[1],
          color: colors[0],
          padding: "0.25rem 0.75rem 0.25rem 0.75rem",
          borderRadius: "1rem",
          maxWidth: "fit-content",
          // don't allow line breaks unless the status contains "error"
          whiteSpace: status.includes("error") ? "normal" : "nowrap",
        }}
        name={`${id}_status`}
      >
        {status}
      </Typography>
    );
  };

  const renderDateRequested = (dataIndex) => {
    const assignment = assignments[dataIndex];
    return (
      <div key={`${assignment.id}_date_requested`}>{assignment.created_at}</div>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderRA = (dataIndex) => {
    const assignment = assignments[dataIndex];
    return (
      <div key={`${assignment.id}_ra`}>
        {assignment.obj.ra}
        <br />
        {ra_to_hours(assignment.obj.ra)}
      </div>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderDec = (dataIndex) => {
    const assignment = assignments[dataIndex];
    return (
      <div key={`${assignment.id}_dec`}>
        {assignment.obj.dec}
        <br />
        {dec_to_dms(assignment.obj.dec)}
      </div>
    );
  };

  const renderRise = (dataIndex) => {
    const assignment = assignments[dataIndex];
    return (
      <div key={`${assignment.id}_rise`}>
        {assignment.rise_time_utc === ""
          ? "Never up"
          : new Date(assignment.rise_time_utc).toLocaleTimeString()}
      </div>
    );
  };

  const renderSet = (dataIndex) => {
    const assignment = assignments[dataIndex];
    return (
      <div key={`${assignment.id}_set`}>
        {assignment.set_time_utc === ""
          ? "Never up"
          : new Date(assignment.set_time_utc).toLocaleTimeString()}
      </div>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderFinderButton = (dataIndex) => {
    const assignment = assignments[dataIndex];
    return (
      <>
        <IconButton size="small" key={`${assignment.id}_actions`}>
          <Link href={`/api/sources/${assignment.obj.id}/finder`}>
            <PictureAsPdfIcon />
          </Link>
        </IconButton>
        <IconButton size="small" key={`${assignment.id}_actions_int`}>
          <Link
            href={`/source/${assignment.obj.id}/finder`}
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
  const RenderGroups = (dataIndex) => {
    const classes = useStyles();
    const assignment = assignments[dataIndex];
    return (
      <div key={`${assignment.obj.id}_groups`}>
        {assignment.accessible_group_names?.map((name) => (
          <div key={name}>
            <Chip
              label={name.substring(0, 15)}
              key={name}
              size="small"
              className={classes.chip}
              data-testid={`chip-assignment_${assignment.id}-group_${name}`}
            />
            <br />
          </div>
        ))}
      </div>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderActionsButton = (dataIndex) => {
    const assignment = assignments[dataIndex];
    return <SimpleMenu assignment={assignment} key={`${assignment.id}_menu`} />;
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
        customBodyRenderLite: renderStatus,
      },
    },
    {
      name: "Date Requested",
      options: {
        filter: true,
        customBodyRenderLite: renderDateRequested,
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
      name: "Request",
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
        customBodyRenderLite: renderRise,
      },
    },
    {
      name: "Sets at (<30deg alt, UT)",
      options: {
        filter: false,
        customBodyRenderLite: renderSet,
      },
    },
    {
      name: "Groups",
      options: {
        filter: false,
        customBodyRenderLite: RenderGroups,
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
    customToolbar: () => (
      <IconButton name="clouds" onClick={() => setDialog(true)}>
        <CloudIcon />
      </IconButton>
    ),
  };

  const data = assignments?.map((assignment) => [
    assignment.obj.id,
    assignment.status,
    assignment.created_at,
    assignment.obj.ra,
    assignment.obj.dec,
    assignment.obj.redshift,
    assignment.requester.username,
    assignment.comment,
    assignment.priority,
    assignment.rise_time_utc,
    assignment.set_time_utc,
    assignment.accessible_group_names,
    null,
    null,
  ]);

  return (
    <div className={styles.center}>
      <Typography variant="h4" gutterBottom color="textSecondary">
        Plan for:{" "}
        <b>
          {observingRunTitle(
            observingRun,
            instrumentList,
            telescopeList,
            groups,
          )}
        </b>
      </Typography>
      <MUIDataTable
        title="Targets"
        columns={columns}
        data={data}
        options={options}
      />
      <Grid container spacing={1} style={{ marginTop: "0.5rem" }}>
        <Grid
          item
          xs={12}
          sm={12}
          md={12}
          lg={8}
          xl={8}
          className={styles.displayInlineBlock}
        >
          <Paper style={{ padding: "0.5rem" }}>
            <Typography gutterBottom align="center">
              Starlist and Offsets
            </Typography>
            <ObservingRunStarList observingRunId={observingRun.id} />
          </Paper>
        </Grid>
        <Grid
          item
          xs={12}
          sm={12}
          md={12}
          lg={4}
          xl={4}
          className={styles.displayInlineBlock}
        >
          <SkyCam telescope={observingRun.instrument.telescope} />
        </Grid>
      </Grid>
      <div>
        {dialog && (
          <Dialog open={dialog} onClose={closeDialog} maxWidth="md">
            <DialogContent dividers>
              Is your observing run clouded out and want to set all pending
              objects to not observered?
            </DialogContent>
            <DialogActions>
              <Button secondary autoFocus onClick={closeDialog}>
                Dismiss
              </Button>
              <Button primary onClick={() => notObservedFunction()}>
                Confirm
              </Button>
            </DialogActions>
          </Dialog>
        )}
      </div>
    </div>
  );
};

RunSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(RunSummary);
