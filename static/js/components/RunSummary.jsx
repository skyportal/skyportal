import React, { useEffect, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import TableCell from "@material-ui/core/TableCell";
import TableRow from "@material-ui/core/TableRow";

import Typography from "@material-ui/core/Typography";
import IconButton from "@material-ui/core/IconButton";
import Grid from "@material-ui/core/Grid";
import Chip from "@material-ui/core/Chip";
import BuildIcon from "@material-ui/icons/Build";

import Link from "@material-ui/core/Link";
import PictureAsPdfIcon from "@material-ui/icons/PictureAsPdf";

import Menu from "@material-ui/core/Menu";
import MenuItem from "@material-ui/core/MenuItem";

import { makeStyles } from "@material-ui/core/styles";

import MUIDataTable from "mui-datatables";
import ThumbnailList from "./ThumbnailList";
import styles from "./RunSummary.css";
import { observingRunTitle } from "./AssignmentForm";
import { ObservingRunStarList } from "./StarList";
import * as SourceAction from "../ducks/source";
import * as Action from "../ducks/observingRun";
import { ra_to_hours, dec_to_dms } from "../units";

import SkyCam from "./SkyCam";

const VegaPlot = React.lazy(() => import("./VegaPlot"));
const AirmassPlot = React.lazy(() => import("./AirmassPlot"));

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
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
          <MenuItem
            key={`${assignment.id}_upload_spec (Coming Soon)`}
            onClick={handleClose}
          >
            Upload Spectrum
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
    return <b>Loading run...</b>;
  }
  const { assignments } = observingRun;

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderPullOutRow = (rowData, rowMeta) => {
    if (observingRun === undefined) {
      return "Loading...";
    }

    const colSpan = rowData.length + 1;
    const assignment = assignments[rowMeta.rowIndex];

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
            justify="center"
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
                  dataUrl={`/api/internal/plot/airmass/${assignment.id}`}
                  ephemeris={observingRun.ephemeris}
                />
              </Suspense>
            </Grid>
            <Grid item>
              <Suspense fallback={<div>Loading plot...</div>}>
                <VegaPlot
                  dataUrl={`/api/sources/${assignment.obj.id}/photometry`}
                />
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

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderFinderButton = (dataIndex) => {
    const assignment = assignments[dataIndex];
    return (
      <IconButton size="small" key={`${assignment.id}_actions`}>
        <Link href={`/api/sources/${assignment.obj.id}/finder`}>
          <PictureAsPdfIcon />
        </Link>
      </IconButton>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const RenderGroups = (dataIndex) => {
    const classes = useStyles();
    const assignment = assignments[dataIndex];
    return (
      <div key={`${assignment.obj.id}_groups`}>
        {assignment.accessible_group_names.map((name) => (
          <div key={name}>
            <Chip
              label={name.substring(0, 15)}
              key={name}
              size="small"
              className={classes.chip}
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
      name: "Rise Time (UT)",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) =>
          new Date(assignments[dataIndex].rise_time_utc).toLocaleTimeString(),
      },
    },
    {
      name: "Set Time (UT)",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) =>
          new Date(assignments[dataIndex].set_time_utc).toLocaleTimeString(),
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

  const data = assignments.map((assignment) => [
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
    <div className={styles.source}>
      <div className={styles.center}>
        <Typography variant="h4" gutterBottom color="textSecondary">
          Plan for:{" "}
          <b>
            {observingRunTitle(
              observingRun,
              instrumentList,
              telescopeList,
              groups
            )}
          </b>
        </Typography>
        <MUIDataTable
          title="Targets"
          columns={columns}
          data={data}
          options={options}
        />
        <Grid container className={styles.center}>
          <Grid
            item
            xs={12}
            sm={12}
            md={12}
            lg={8}
            xl={8}
            className={styles.displayInlineBlock}
          >
            <Typography gutterBottom align="center">
              Starlist and Offsets
            </Typography>
            <ObservingRunStarList observingRunId={observingRun.id} />
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
    </div>
  );
};

RunSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default RunSummary;
