import React, { useEffect, Suspense } from 'react';
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
    <MenuItem onClick={complete_action} variant="contained">
      Mark Observed
    </MenuItem>
  );

  const mark_pending = (
    <MenuItem onClick={pending_action} variant="contained">
      Mark Pending
    </MenuItem>
  );

  const mark_not_observed = (
    <MenuItem onClick={not_observed_action} variant="contained">
      Mark Not Observed
    </MenuItem>
  );

  const upload_photometry = (
    <a href={`/source/${assignment.obj.id}/upload_photometry`}>
      <MenuItem>
        Upload Photometry
      </MenuItem>
    </a>
  );

  const upload_spectrum = (
    <MenuItem>
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

  if (!(("id" in observingRun) && (observingRun.id === parseInt(route.id)))) {
    // Don't need to do this for assignments -- we can just let the page be blank for a short time
    return (
      <b>
        Loading run...
      </b>
    );
  } else {
    const options = {
      draggableColumns: { enabled: true },
      expandableRows: true,
      renderExpandableRow: ((rowData, rowMeta) => {
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
                    <VegaPlot
                      dataUrl={`/api/internal/plot/airmass/${assignment.id}`}
                      type="airmass"
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
      }),
      selectableRows: "none"
    };

    const data = observingRun.assignments.map(
      (assignment) => (
        [
          <a href={`/source/${assignment.obj.id}`}>
            {assignment.obj.id}
          </a>,
          <div>
            {assignment.obj.ra}
            <br />
            {ra_to_hours(assignment.obj.ra)}
          </div>,
          <div>
            {assignment.obj.dec}
            <br />
            {dec_to_hours(assignment.obj.dec)}
          </div>,
          assignment.obj.redshift,
          assignment.requester.username,
          assignment.comment,
          assignment.priority,
          new Date(assignment.rise_time_utc).toLocaleTimeString(),
          new Date(assignment.set_time_utc).toLocaleTimeString(),
          <IconButton size="small">
            <Link href={`/api/sources/${assignment.obj.id}/finder`}>
              <PictureAsPdfIcon />
            </Link>
          </IconButton>,
          <SimpleMenu assignment={assignment} />
        ]
      )
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
                columns={["Target Name", "RA", "Dec", "Redshift", "Requester", "Request",
                  "Priority", "Rise Time (UT)", "Set Time (UT)", "Finder", "Actions"]}
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

export default RunSummary;
