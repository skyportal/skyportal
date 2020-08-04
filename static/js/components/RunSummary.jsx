import React, { useEffect, Suspense, useState } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';


import TableCell from '@material-ui/core/TableCell';
import TableRow from '@material-ui/core/TableRow';

import Typography from '@material-ui/core/Typography';
import IconButton from '@material-ui/core/IconButton';
import Grid from '@material-ui/core/Grid';
import BuildIcon from '@material-ui/icons/Build';

import Link from '@material-ui/core/Link';
import PictureAsPdfIcon from '@material-ui/icons/PictureAsPdf';

import Menu from '@material-ui/core/Menu';
import MenuItem from '@material-ui/core/MenuItem';

import MUIDataTable from "mui-datatables";
import ThumbnailList from "./ThumbnailList";
import styles from './RunSummary.css';
import { observingRunTitle } from './AssignmentForm';
import { ObservingRunStarList } from './StarList';
import * as SourceAction from '../ducks/source';
import * as Action from '../ducks/observingRun';
import { ra_to_hours, dec_to_hours } from "../units";

const VegaPlot = React.lazy(() => import('./VegaPlot'));
const AirmassPlot = React.lazy(() => import ('./AirmassPlot'));


const SimpleMenu = ({ assignment }) => {
  const [anchorEl, setAnchorEl] = React.useState(null);
  const dispatch = useDispatch();

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const ispending = assignment.status === "pending";
  const isdone = assignment.status === "complete";

  const complete_action = () => dispatch(
    SourceAction.editAssignment({ status: "complete" }, assignment.id)
  );

  const pending_action = () => dispatch(
    SourceAction.editAssignment({ status: "pending" }, assignment.id)
  );

  const not_observed_action = () => dispatch(
    SourceAction.editAssignment({ status: "not observed" }, assignment.id)
  );

  const mark_observed = (
    <MenuItem onClick={complete_action} variant="contained" key={`${assignment.id}_done`}>
      Mark Observed
    </MenuItem>
  );

  const mark_pending = (
    <MenuItem onClick={pending_action} variant="contained" key={`${assignment.id}_pending`}>
      Mark Pending
    </MenuItem>
  );

  const mark_not_observed = (
    <MenuItem onClick={not_observed_action} variant="contained" key={`${assignment.id}_notdone`}>
      Mark Not Observed
    </MenuItem>
  );

  const upload_photometry = (
    <a href={`/source/${assignment.obj.id}/upload_photometry`}>
      <MenuItem key={`${assignment.id}_upload_phot`} variant="contained">
        Upload Photometry
      </MenuItem>
    </a>
  );

  const upload_spectrum = (
    <MenuItem key={`${assignment.id}_upload_spec`}>
      Upload Spectrum
    </MenuItem>
  );

  const render_items = [];
  if (ispending) {
    render_items.push(mark_observed);
    render_items.push(mark_not_observed);
  } else if (isdone) {
    render_items.push(mark_pending);
    render_items.push(mark_not_observed);
    render_items.push(upload_photometry);
    render_items.push(upload_spectrum);
  } else {
    render_items.push(mark_pending);
    render_items.push(mark_observed);
  }

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
        {render_items}
      </Menu>
    </div>
  );
};

SimpleMenu.propTypes = {
  assignment: PropTypes.shape({
    status: PropTypes.string,
    id: PropTypes.number,
    obj: PropTypes.shape(
      {
        id: PropTypes.string
      }
    ).isRequired
  }).isRequired
};




/*PullOutRow.propTypes = {
  rowData: PropTypes.arrayOf(PropTypes.string).isRequired,
  rowMeta: PropTypes.shape(
    {
      dataIndex: PropTypes.number,
      rowIndex: PropTypes.number
    }
  ).isRequired
};*/


const RunSummary = ({ route }) => {
  const dispatch = useDispatch();
  const observingRun = useSelector((state) => state.observingRun);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  // for the clock
  const [now, setNow] = useState(Date.now());

  // Load the observing run and its assignments if needed
  useEffect(() => {
    dispatch(Action.fetchObservingRun(route.id));
  }, [route.id, dispatch]);

  useEffect(() => {
    // update the clock every five minutes
    const intervalms = 60 * 1000 * 5;
    const interval = setInterval(() => {
      setNow(now + intervalms)
    }, intervalms);
    return () => clearInterval(interval);
  }, []);

  if (!(("id" in observingRun) && (observingRun.id === parseInt(route.id, 10)))) {
    // Don't need to do this for assignments -- we can just let the page be blank for a short time
    return (
      <b>
        Loading run...
      </b>
    );
  } else {

    const { assignments } = observingRun;

    const renderPullOutRow = (( rowData, rowMeta ) => {
      if (observingRun === undefined) {
        return "Loading...";
      }

      const colSpan = rowData.length + 1;
      const assignment = observingRun.assignments[rowMeta.rowIndex];

      return (
        <TableRow>
          <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={colSpan}>
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
    });

      // ["Target Name", "RA", "Dec", "Redshift", "Requester", "Request",
      //            "Priority", "Rise Time (UT)", "Set Time (UT)", "Finder", "Actions"]

    const renderObjId = (dataIndex) => {
      const objid = assignments[dataIndex].obj.id;
      return (
        <a href={`/source/${objid}`} key={`${objid}_objid`}>
          {objid}
        </a>
      );
    };

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

    const renderDec = (dataIndex) => {
      const assignment = assignments[dataIndex];
      return (
        <div key={`${assignment.id}_dec`}>
          {assignment.obj.dec}
          <br />
          {dec_to_hours(assignment.obj.dec)}
        </div>
      );
    };

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

    const renderActionsButton = (dataIndex) => {
      const assignment = assignments[dataIndex];
      return <SimpleMenu assignment={assignment} key={`${assignment.id}_menu`} />;
    };

    const columns =
      [
        {
          name: "Target Name",
          options: {
            filter: true,
            customBodyRenderLite: renderObjId
          }
        },
        {
          name: "RA",
          options: {
            filter: false,
            customBodyRenderLite: renderRA
          }
        },
        {
          name: "Dec",
          options: {
            filter: false,
            customBodyRenderLite: renderDec
          }
        },
        {
          name: "Redshift",
          options: {
            filter: false
          }
        },
        {
          name: "Requester",
          options: {
            filter: true
          }
        },
        {
          name: "Request",
          options: {
            filter: true
          }
        },
        {
          name: "Priority",
          options: {
            filter: true
          }
        },
        {
          name: "Rise Time (UT)",
          options: {
            filter: false,
            customBodyRenderLite: (
              (dataIndex) => new Date(assignments[dataIndex].rise_time_utc).toLocaleTimeString()
            )
          }
        },
        {
          name: "Set Time (UT)",
          options: {
            filter: false,
            customBodyRenderLite: (
              (dataIndex) => new Date(assignments[dataIndex].set_time_utc).toLocaleTimeString()
            )
          }
        },
        {
          name: "Finder",
          options: {
            filter: false,
            customBodyRenderLite: renderFinderButton
          }
        },
        {
          name: "Actions",
          options: {
            filter: false,
            customBodyRenderLite: renderActionsButton
          }
        }
      ];


    const options = {
      draggableColumns: { enabled: true },
      expandableRows: true,
      renderExpandableRow: renderPullOutRow,
      selectableRows: "none"
    };

    const data = observingRun.assignments.map(
      (assignment) => ([
        assignment.obj.id,
        assignment.obj.ra,
        assignment.obj.dec,
        assignment.obj.redshift,
        assignment.requester.username,
        assignment.comment,
        assignment.priority,
        assignment.rise_time_utc,
        assignment.set_time_utc,
        null,
        null])
      );

    return (
      <div className={styles.source}>
        <div>
          <Grid container direction="column" alignItems="center" justify="flex-start" spacing={3}>
            <Grid item>
              <div>
                <Typography variant="h4" gutterBottom color="textSecondary" align="center">
                  <em>Observing Planner for:</em>
                </Typography>
                <Typography variant="h4" gutterBottom color="textSecondary">
                  <b>{observingRunTitle(observingRun, instrumentList, telescopeList, groups)}</b>
                </Typography>
              </div>
            </Grid>
            <Grid item>
              <MUIDataTable
                title="Targets"
                columns={columns}
                data={data}
                options={options}
              />
            </Grid>
            <Grid item>
              <Typography gutterBottom align="center">
                Starlist and Offsets
              </Typography>
              <ObservingRunStarList observingRunId={observingRun.id} />
            </Grid>
          </Grid>
        </div>
      </div>
    );
  }
};

RunSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired
};

export default RunSummary;
