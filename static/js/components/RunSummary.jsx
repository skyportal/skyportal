import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';

import * as Action from '../ducks/observingRun';
import * as SourceAction from '../ducks/source';
import { ObservingRunStarList } from './StarList';
import { observingRunTitle } from './AssignmentForm';
import styles from './RunSummary.css';

import { Suspense } from 'react';

import Table from '@material-ui/core/Table';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemText from '@material-ui/core/ListItemText';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableContainer from '@material-ui/core/TableContainer';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import TablePagination from '@material-ui/core/TablePagination';
import TableFooter from '@material-ui/core/TableFooter';
import Paper from '@material-ui/core/Paper';
import Button from '@material-ui/core/Button';

import Typography from '@material-ui/core/Typography';
import IconButton from '@material-ui/core/IconButton';
import FirstPageIcon from '@material-ui/icons/FirstPage';
import KeyboardArrowUpIcon from '@material-ui/icons/KeyboardArrowUp';
import KeyboardArrowDownIcon from '@material-ui/icons/KeyboardArrowDown';

import KeyboardArrowLeft from '@material-ui/icons/KeyboardArrowLeft';
import KeyboardArrowRight from '@material-ui/icons/KeyboardArrowRight';
import Box from '@material-ui/core/Box';
import Collapse from '@material-ui/core/Collapse';
import Grid from '@material-ui/core/Grid';

import LastPageIcon from '@material-ui/icons/LastPage';
import BuildIcon from '@material-ui/icons/Build';

import Link from '@material-ui/core/Link';
import PictureAsPdfIcon from '@material-ui/icons/PictureAsPdf';
import { time_relative_to_local, ra_to_hours, dec_to_hours } from "../units";
import ThumbnailList from "./ThumbnailList";
import { makeStyles, useTheme } from '@material-ui/core/styles';

const VegaPlot = React.lazy(() => import('./VegaPlot'));

import Menu from '@material-ui/core/Menu';
import MenuItem from '@material-ui/core/MenuItem';

import MUIDataTable from "mui-datatables";


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
    SourceAction.editAssignment({status: "complete"}, assignment.id)
  );

  const pending_action = () => dispatch(
    SourceAction.editAssignment({status: "pending"}, assignment.id)
  );

  const not_observed_action = () => dispatch(
    SourceAction.editAssignment({status: "not observed"}, assignment.id)
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
        variant="contained">
        <BuildIcon/>
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

const useRowStyles = makeStyles({
  root: {
    '& > *': {
      borderBottom: 'unset',
    },
  },
});


const Row = ({ assignment }) => {
  const [open, setOpen] = React.useState(false);
  const classes = useRowStyles();


  return (
    <React.Fragment>
      <TableRow className={classes.root}>
        <TableCell>
          <IconButton aria-label="expand row" size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell scope="row" align="center">
          <a href={`/source/${assignment.obj.id}`}>
            {assignment.obj.id}
          </a>
        </TableCell>
        <TableCell scope="row" align="center">
          {assignment.obj.ra}
          <br />
          {ra_to_hours(assignment.obj.ra)}
        </TableCell>
        <TableCell scope="row" align="center">
          {assignment.obj.dec}
          <br />
          {dec_to_hours(assignment.obj.dec)}
        </TableCell>
        <TableCell scope="row" align="center">
          {assignment.obj.redshift}
        </TableCell>
        <TableCell scope="row" align="center">
          {assignment.requester.username}
        </TableCell>
        <TableCell scope="row" align="center">
          {assignment.comment}
        </TableCell>
        <TableCell scope="row" align="center">
          {assignment.priority}
        </TableCell>
        <TableCell scope="row" align="center">
          {new Date(assignment.rise_time_utc).toLocaleTimeString()}
        </TableCell>
        <TableCell scope="row" align="center">
          {new Date(assignment.set_time_utc).toLocaleTimeString()}
        </TableCell>
        <TableCell align="center">
          <IconButton aria-label="expand row" size="small">
            <Link href={`/api/sources/${assignment.obj.id}/finder`}>
              <PictureAsPdfIcon/>
            </Link>
          </IconButton>
        </TableCell>
        <TableCell align="center">
          <SimpleMenu assignment={assignment} />
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={12}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box margin={1}>
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
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </React.Fragment>
  );
};


const RunSummary = ({ route }) => {

  const dispatch = useDispatch();
  const observingRun = useSelector((state) => state.observingRun);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const [page, setPage] = React.useState(0);
  const [rowsPerPage, setRowsPerPage] = React.useState(5);

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

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
      draggableColumns: {enabled: true},
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
        )
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
              <PictureAsPdfIcon/>
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
              <ObservingRunStarList observingRunId={observingRun.id}/>
            </Grid>
          </Grid>
        </div>
      </div>
    );
  }
};

export default RunSummary;
