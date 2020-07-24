import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';

import * as Action from '../ducks/observingRun';
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
import Paper from '@material-ui/core/Paper';

import Typography from '@material-ui/core/Typography';
import IconButton from '@material-ui/core/IconButton';
import FirstPageIcon from '@material-ui/icons/FirstPage';
import KeyboardArrowUpIcon from '@material-ui/icons/KeyboardArrowUp';
import KeyboardArrowDownIcon from '@material-ui/icons/KeyboardArrowDown';
import Box from '@material-ui/core/Box';
import Collapse from '@material-ui/core/Collapse';
import Grid from '@material-ui/core/Grid';

import LastPageIcon from '@material-ui/icons/LastPage';

import Link from '@material-ui/core/Link';
import PictureAsPdfIcon from '@material-ui/icons/PictureAsPdf';
import { time_relative_to_local, ra_to_hours, dec_to_hours } from "../units";
import ThumbnailList from "./ThumbnailList";
import { makeStyles } from '@material-ui/core/styles';

const VegaPlot = React.lazy(() => import('./VegaPlot'));

const useRowStyles = makeStyles({
  root: {
    '& > *': {
      borderBottom: 'unset',
    },
  },
});

function assignmentDescriptor(assignment){
  const relative = time_relative_to_local(assignment.modified);
  return `${relative} -- ${assignment.requester.username}: ${assignment.comment} (P${assignment.priority})`;
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service
    console.log(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return <td>Something went wrong.</td>;
    }

    return this.props.children;
  }
}


const Row = ({ assignment }) => {
  const [open, setOpen] = React.useState(false);
  const classes = useRowStyles();

  const redshift_part = (
    <React.Fragment>
      <br />
      <b>
        Redshift:
        &nbsp;
      </b>
      {assignment.obj.redshift}
    </React.Fragment>
  );

  return (
    <React.Fragment>
      <TableRow className={classes.root}>
        <TableCell>
          <IconButton aria-label="expand row" size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell scope="row" align="left">
          <b>Target Name:</b>
          &nbsp;
          {assignment.obj.id}
          <br />
          <b>
            Position (J2000):
          </b>
          &nbsp;
          {assignment.obj.ra}
          ,
          &nbsp;
          {assignment.obj.dec}
          <br />
          (&alpha;,&delta;=
          {ra_to_hours(assignment.obj.ra)}
          ,
          &nbsp;
          {dec_to_hours(assignment.obj.dec)}
          )
          {(assignment.obj.redshift > 0 && assignment.obj.redshift !== undefined) &&
            redshift_part
          }
        </TableCell>
        <TableCell align="center"><p>Placeholder</p></TableCell>
        <ErrorBoundary>
          <TableCell align="center">
            <Suspense fallback={<div>Loading plot...</div>}>
              <VegaPlot
                dataUrl={`/api/sources/${assignment.obj.id}/photometry`}
              />
            </Suspense>
          </TableCell>
        </ErrorBoundary>
        <ErrorBoundary>
          <TableCell align="center">
            {assignmentDescriptor(assignment)}
            <br />
            <List dense={true}>
              {assignment.obj.comments.slice(-3).map(
                (comment) => (
                  <ListItem key={comment.id}>
                    <ListItemText primary={comment.text} secondary={
                      `${comment.author} (${time_relative_to_local(comment.modified)})`
                    } />
                  </ListItem>
                )
              )}
            </List>
          </TableCell>
        </ErrorBoundary>
        <ErrorBoundary>
          <TableCell align="center">
            <IconButton aria-label="expand row" size="small">
              <Link href={`/api/sources/${assignment.obj.id}/finder`}>
                <PictureAsPdfIcon/>
              </Link>
            </IconButton>
          </TableCell>
        </ErrorBoundary>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={6}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box margin={1}>
              <Typography variant="h6" gutterBottom component="div" align="center">
                Thumbnails
              </Typography>
              <ThumbnailList
                thumbnails={assignment.obj.thumbnails}
                ra={assignment.obj.ra}
                dec={assignment.obj.dec}
              />
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
              <Typography gutterBottom align="center">
                Targets
              </Typography>
              <TableContainer className={styles.tableContainer} component={Paper}>
                <Table aria-label="simple table">
                  <TableHead>
                    <TableRow>
                      <ErrorBoundary>
                        <TableCell align="center" />
                        <TableCell align="center">Target</TableCell>
                        <TableCell align="center">Assignment Details</TableCell>
                        <TableCell align="center">Light Curve</TableCell>
                        <TableCell align="center">Recent Comments</TableCell>
                        <TableCell align="center">Finder Chart</TableCell>
                      </ErrorBoundary>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {observingRun.assignments.map((assignment) => (
                      <Row assignment={assignment}/>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
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
