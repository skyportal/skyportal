import React, { Suspense, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";

import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
import BuildIcon from "@mui/icons-material/Build";

import Link from "@mui/material/Link";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import ImageAspectRatioIcon from "@mui/icons-material/ImageAspectRatio";
import CircularProgress from "@mui/material/CircularProgress";

import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";

import makeStyles from "@mui/styles/makeStyles";

import MUIDataTable from "mui-datatables";
import ThumbnailList from "./thumbnail/ThumbnailList";
import { observingRunTitle } from "./AssignmentForm";
import { ObservingRunStarList } from "./StarList";
import withRouter from "./withRouter";

import * as SourceAction from "../ducks/source";
import * as Action from "../ducks/observingRun";
import { dec_to_dms, ra_to_hours } from "../units";

import SkyCam from "./SkyCam";
import VegaPhotometry from "./vega/VegaPhotometry";

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

const SimpleMenu = ({ assignment }) => {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const dispatch = useDispatch();

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
        {assignment.status === "complete" && (
          <MenuItem key={`${assignment.id}_upload_spec`} onClick={handleClose}>
            <Link
              href={`/upload_spectrum/${assignment.obj.id}`}
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
              href={`/upload_photometry/${assignment.obj.id}`}
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
  assignment: PropTypes.shape({
    status: PropTypes.string,
    id: PropTypes.number,
    obj: PropTypes.shape({
      id: PropTypes.string,
    }).isRequired,
  }).isRequired,
};

const RunSummary = ({ route }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const observingRun = useSelector((state) => state.observingRun);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  // Load the observing run and its assignments if needed
  useEffect(() => {
    dispatch(Action.fetchObservingRun(route.id));
  }, [route.id, dispatch]);

  if (!("id" in observingRun && observingRun.id === parseInt(route.id, 10))) {
    // Don't need to do this for assignments -- we can just let the page be blank for a short time
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }
  const { assignments } = observingRun;

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
  };

  const data = assignments?.map((assignment) => [
    assignment.obj.id,
    assignment.status,
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
    </div>
  );
};

RunSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(RunSummary);
