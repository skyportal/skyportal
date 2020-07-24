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

import Link from '@material-ui/core/Link';
import PictureAsPdfIcon from '@material-ui/icons/PictureAsPdf';
import { time_relative_to_local, ra_to_hours, dec_to_hours } from "../units";
import ThumbnailList from "./ThumbnailList";
import { makeStyles, useTheme } from '@material-ui/core/styles';

const VegaPlot = React.lazy(() => import('./VegaPlot'));

const useRowStyles = makeStyles({
  root: {
    '& > *': {
      borderBottom: 'unset',
    },
  },
});

const useStyles1 = makeStyles((theme) => ({
  root: {
    flexShrink: 0,
    marginLeft: theme.spacing(2.5),
  },
}));

function TablePaginationActions(props) {
  const classes = useStyles1();
  const theme = useTheme();
  const { count, page, rowsPerPage, onChangePage } = props;

  const handleFirstPageButtonClick = (event) => {
    onChangePage(event, 0);
  };

  const handleBackButtonClick = (event) => {
    onChangePage(event, page - 1);
  };

  const handleNextButtonClick = (event) => {
    onChangePage(event, page + 1);
  };

  const handleLastPageButtonClick = (event) => {
    onChangePage(event, Math.max(0, Math.ceil(count / rowsPerPage) - 1));
  };

  return (
    <div className={classes.root}>
      <IconButton
        onClick={handleFirstPageButtonClick}
        disabled={page === 0}
        aria-label="first page"
      >
        {theme.direction === 'rtl' ? <LastPageIcon /> : <FirstPageIcon />}
      </IconButton>
      <IconButton onClick={handleBackButtonClick} disabled={page === 0} aria-label="previous page">
        {theme.direction === 'rtl' ? <KeyboardArrowRight /> : <KeyboardArrowLeft />}
      </IconButton>
      <IconButton
        onClick={handleNextButtonClick}
        disabled={page >= Math.ceil(count / rowsPerPage) - 1}
        aria-label="next page"
      >
        {theme.direction === 'rtl' ? <KeyboardArrowLeft /> : <KeyboardArrowRight />}
      </IconButton>
      <IconButton
        onClick={handleLastPageButtonClick}
        disabled={page >= Math.ceil(count / rowsPerPage) - 1}
        aria-label="last page"
      >
        {theme.direction === 'rtl' ? <FirstPageIcon /> : <LastPageIcon />}
      </IconButton>
    </div>
  );
}

TablePaginationActions.propTypes = {
  count: PropTypes.number.isRequired,
  onChangePage: PropTypes.func.isRequired,
  page: PropTypes.number.isRequired,
  rowsPerPage: PropTypes.number.isRequired,
};

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

const ObserverActions = ({ assignment }) => {

  const dispatch = useDispatch();
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
    <React.Fragment>
      <Button onClick={complete_action} variant="contained">
        Mark Observed
      </Button>
    </React.Fragment>
  );

  const mark_pending = (
    <Button onClick={pending_action} variant="contained">
      Mark Pending
    </Button>
  );

  const mark_not_observed = (
    <React.Fragment>
      <Button onClick={not_observed_action} variant="contained">
        Mark Not Observed
      </Button>
    </React.Fragment>
  );

  const upload_photometry = (
    <React.Fragment>
      <a href={`/source/${assignment.obj.id}/upload_photometry`}>
        <Button>
          Upload Photometry
        </Button>
      </a>
    </React.Fragment>
  );

  const upload_spectrum = (
    <React.Fragment>
      <Button>
        Upload Spectrum
      </Button>
    </React.Fragment>

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
    <List dense={true}>
      {render_items.map((item) => (
        <ListItem>
          {item}
        </ListItem>
      ))}
    </List>
  )
};


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

  const comment_part = (
    <React.Fragment>
      <br />
      <b>
        With comment:
      </b>
      &nbsp;
      {assignment.comment}
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
          <a href={`/source/${assignment.obj.id}`}>
            {assignment.obj.id}
          </a>
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
          {(assignment.obj.redshift !== undefined && assignment.obj.redshift > 0) &&
            redshift_part
          }
          <br />
          <b>Assigned by:</b>
          &nbsp;
          {assignment.requester.username}
          {(assignment.comment !== undefined && assignment.comment !== "") && comment_part}
          <br />
          <b>Priority:</b>
          &nbsp;
          {assignment.priority}
        </TableCell>
        <TableCell align="center">
          <Suspense fallback={<div>Loading plot...</div>}>
            <VegaPlot
              dataUrl={`/api/internal/plot/airmass/${assignment.id}`}
              type="airmass"
            />
          </Suspense>

        </TableCell>
        <TableCell align="center">
          <Suspense fallback={<div>Loading plot...</div>}>
            <VegaPlot
              dataUrl={`/api/sources/${assignment.obj.id}/photometry`}
            />
          </Suspense>
        </TableCell>
        <TableCell align="center">
          <List dense={true}>
            {assignment.obj.comments.slice(0, 3).map(
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
        <TableCell align="center">
          <ObserverActions assignment={assignment} />
        </TableCell>
        <TableCell align="center">
          <IconButton aria-label="expand row" size="small">
            <Link href={`/api/sources/${assignment.obj.id}/finder`}>
              <PictureAsPdfIcon/>
            </Link>
          </IconButton>
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={7}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box margin={1}>
              <Typography gutterBottom component="div" align="center">
                <b>Thumbnails</b>
              </Typography>
              <ThumbnailList
                thumbnails={assignment.obj.thumbnails}
                ra={assignment.obj.ra}
                dec={assignment.obj.dec}
                gridKwargs={{justify: "center", alignItems: "center"}}
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

    const emptyRows = rowsPerPage - Math.min(rowsPerPage, observingRun.assignments.length - page * rowsPerPage);

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
                        <TableCell align="center">Target Info</TableCell>
                        <TableCell align="center">Airmass Chart</TableCell>
                        <TableCell align="center">Light Curve</TableCell>
                        <TableCell align="center">Recent Comments</TableCell>
                        <TableCell align="center">Actions</TableCell>
                        <TableCell align="center">Finder Chart</TableCell>
                      </ErrorBoundary>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {observingRun.assignments.map((assignment) => (
                      <Row assignment={assignment}/>
                    ))}
                    {emptyRows > 0 && (
                      <TableRow style={{ height: 53 * emptyRows }}>
                        <TableCell colSpan={6} />
                      </TableRow>
                    )}
                  </TableBody>
                  <TableFooter>
                    <TableRow>
                      <TablePagination
                        rowsPerPageOptions={[5, 10, 25, { label: 'All', value: -1 }]}
                        colSpan={3}
                        count={observingRun.assignments.length}
                        rowsPerPage={rowsPerPage}
                        page={page}
                        SelectProps={{
                          inputProps: { 'aria-label': 'rows per page' },
                          native: true,
                        }}
                        onChangePage={handleChangePage}
                        onChangeRowsPerPage={handleChangeRowsPerPage}
                        ActionsComponent={TablePaginationActions}
                      />
                    </TableRow>
                  </TableFooter>
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
