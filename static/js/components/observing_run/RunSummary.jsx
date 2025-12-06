import React, { Suspense, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";

import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
import CloudIcon from "@mui/icons-material/Cloud";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import makeStyles from "@mui/styles/makeStyles";

import MUIDataTable from "mui-datatables";
import { showNotification } from "baselayer/components/Notifications";

import Button from "../Button";
import ThumbnailList from "../thumbnail/ThumbnailList";
import { ObservingRunStarList } from "../StarList";
import withRouter from "../withRouter";

import * as SourceAction from "../../ducks/source";
import * as Action from "../../ducks/observingRun";

import SkyCam from "../SkyCam";
import VegaPhotometry from "../plot/VegaPhotometry";
import {
  renderTargetName,
  renderStatus,
  renderRA,
  renderDec,
  renderRise,
  renderSet,
  renderFinderButton,
  ActionsMenu,
} from "../../utils/displaySummary";
import Box from "@mui/material/Box";
import Spinner from "../Spinner";

const AirmassPlot = React.lazy(() => import("../plot/AirmassPlot"));

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  displayInlineBlock: {
    display: "inline-block",
  },
}));

export function observingRunTitle(
  observingRun,
  instrumentList,
  telescopeList,
  groups,
  isBold = false,
) {
  const { instrument_id } = observingRun;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];
  const telescope = telescopeList?.filter(
    (t) => t.id === instrument?.telescope_id,
  )[0];
  const group = groups?.filter((g) => g.id === observingRun.group_id)[0];
  if (!observingRun?.calendar_date || !instrument?.name || !telescope?.name) {
    return <CircularProgress color="secondary" />;
  }
  let result = `${observingRun?.calendar_date} ${instrument?.name}/${telescope?.nickname}`;
  let moreInfo =
    (observingRun?.pi ? `PI: ${observingRun.pi}` : "") +
    (observingRun?.pi && group?.name ? " / " : "") +
    (group?.name ? `Group: ${group.name}` : "");
  moreInfo = moreInfo ? ` (${moreInfo})` : "";

  return isBold ? (
    <>
      <b>{result}</b>
      {moreInfo}
    </>
  ) : (
    result + moreInfo
  );
}

const RunSummary = ({ route }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const observingRun = useSelector((state) => state.observingRun);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);
  const [dialog, setDialog] = useState(false);

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
          setDialog(false);
        }
      },
    );
  };

  const renderPullOutRow = (rowData, rowMeta) => {
    if (observingRun === undefined)
      return <CircularProgress color="secondary" />;

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

  const RenderGroups = (dataIndex) => {
    const classes = useStyles();
    const assignment = assignments[dataIndex];
    return assignment.accessible_group_names?.map((name) => (
      <div key={name}>
        <Chip
          label={name.substring(0, 15)}
          size="small"
          className={classes.chip}
        />
        <br />
      </div>
    ));
  };

  const updateAssignmentStatus = async (assignment, status) => {
    const result = await dispatch(
      SourceAction.editAssignment({ status }, assignment.id),
    );
    if (result.status === "success") {
      dispatch(showNotification("Assignment status updated successfully"));
    }
  };

  const columns = [
    {
      name: "Target Name",
      options: {
        filter: true,
        customBodyRenderLite: (dataIndex) =>
          renderTargetName(assignments[dataIndex]),
      },
    },
    {
      name: "Request Date",
      options: {
        filter: true,
        customBodyRenderLite: (dataIndex) => assignments[dataIndex].created_at,
      },
    },
    {
      name: "Status",
      options: {
        filter: true,
        setCellProps: () => ({
          style: {
            minWidth: "250px",
          },
        }),
        customBodyRenderLite: (dataIndex) =>
          renderStatus(assignments[dataIndex]),
      },
    },
    {
      name: "RA",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) => renderRA(assignments[dataIndex]),
      },
    },
    {
      name: "Dec",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) => renderDec(assignments[dataIndex]),
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
        customBodyRenderLite: (dataIndex) => renderRise(assignments[dataIndex]),
      },
    },
    {
      name: "Sets at (<30deg alt, UT)",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) => renderSet(assignments[dataIndex]),
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
        customBodyRenderLite: (dataIndex) =>
          renderFinderButton(assignments[dataIndex]),
      },
    },
    {
      name: "Actions",
      options: {
        filter: false,
        customBodyRenderLite: (dataIndex) => (
          <ActionsMenu
            item={assignments[dataIndex]}
            updateFunction={updateAssignmentStatus}
            observingRunList={observingRunList}
          />
        ),
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
    assignment.created_at,
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
    <Box sx={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Typography variant="h1" gutterBottom color="textSecondary">
        Plan for:{" "}
        {observingRunTitle(
          observingRun,
          instrumentList,
          telescopeList,
          groups,
          true,
        )}
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
      <Dialog open={dialog} onClose={() => setDialog(false)} maxWidth="md">
        <DialogContent dividers>
          Is your observing run clouded out and you want to set all pending
          objects to not observed?
        </DialogContent>
        <DialogActions>
          <Button secondary autoFocus onClick={() => setDialog(false)}>
            Dismiss
          </Button>
          <Button primary onClick={() => notObservedFunction()}>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

RunSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(RunSummary);
