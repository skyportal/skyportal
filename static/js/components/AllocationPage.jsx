import React from "react";
import { useSelector, useDispatch } from "react-redux";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import { showNotification } from "baselayer/components/Notifications";
import { Button } from "@mui/material";
import CircularProgress from "@mui/material/CircularProgress";
import NewAllocation from "./NewAllocation";
import NewDefaultObservationPlan from "./NewDefaultObservationPlan";

import * as defaultObservationPlansActions from "../ducks/default_observation_plans";
import * as allocationActions from "../ducks/allocation";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    maxWidth: "22.5rem",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  paperContent: {
    padding: "1rem",
  },
  allocationDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  allocationDeleteDisabled: {
    opacity: 0,
  },
  defaultObservationPlanDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  defaultObservationPlanDeleteDisabled: {
    opacity: 0,
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

export function allocationTitle(allocation, instrumentList, telescopeList) {
  const { instrument_id } = allocation;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];

  const telescope_id = instrument?.telescope_id;
  const telescope = telescopeList?.filter((t) => t.id === telescope_id)[0];

  if (!(instrument?.name && telescope?.name)) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const result = `${instrument?.name}/${telescope?.nickname}`;

  return result;
}

export function allocationInfo(allocation, groups) {
  const group = groups?.filter((g) => g.id === allocation.group_id)[0];

  if (!allocation?.start_date) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const share_groups = [];
  if (allocation.default_share_group_ids?.length > 0) {
    allocation.default_share_group_ids.forEach((share_group_id) => {
      share_groups.push(groups?.filter((g) => g.id === share_group_id)[0].name);
    });
  }

  const startDate = new Date(`${allocation.start_date}Z`).toLocaleString(
    "en-US",
    { hour12: false }
  );
  const endDate = new Date(`${allocation.end_date}Z`).toLocaleString("en-US", {
    hour12: false,
  });
  let result = `From ${startDate} to ${endDate}`;

  if (allocation?.pi || group?.name || share_groups.length > 0) {
    result += "\r\n(";
    if (allocation?.pi) {
      result += `PI: ${allocation.pi}`;
    }
    if (group?.name) {
      result += ` / Group: ${group?.name}`;
    }
    if (share_groups.length > 0) {
      result += ` / Default Share Groups: ${share_groups.join(", ")}`;
    }
    result += ")";
  }

  return result;
}

export function defaultObservationPlanInfo(default_observation_plan) {
  let result = "";
  if (default_observation_plan?.payload) {
    result += `Payload: ${JSON.stringify(
      default_observation_plan?.payload,
      null,
      " "
    )}`;
  }

  return result;
}

const AllocationList = ({ allocations, deletePermission }) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const textClasses = textStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const deleteAllocation = (allocation) => {
    dispatch(allocationActions.deleteAllocation(allocation.id)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Allocation deleted"));
        }
      }
    );
  };

  return (
    <div className={classes.root}>
      <List component="nav">
        {allocations?.map((allocation) => (
          <ListItem button key={allocation.id}>
            <ListItemText
              primary={allocationTitle(
                allocation,
                instrumentList,
                telescopeList
              )}
              secondary={allocationInfo(allocation, groups)}
              classes={textClasses}
            />
            <Button
              key={allocation.id}
              id="delete_button"
              classes={{
                root: classes.allocationDelete,
                disabled: classes.allocationDeleteDisabled,
              }}
              onClick={() => deleteAllocation(allocation)}
              disabled={!deletePermission}
            >
              &times;
            </Button>
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const DefaultObservationPlanList = ({
  default_observation_plans,
  deletePermission,
}) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const textClasses = textStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const deleteDefaultObservationPlan = (default_observation_plan) => {
    dispatch(
      defaultObservationPlansActions.deleteDefaultObservationPlan(
        default_observation_plan.id
      )
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Default observation plan deleted"));
      }
    });
  };

  return (
    <div className={classes.root}>
      <List component="nav">
        {default_observation_plans?.map((default_observation_plan) => (
          <ListItem button key={default_observation_plan.id}>
            <ListItemText
              primary={allocationTitle(
                default_observation_plan.allocation,
                instrumentList,
                telescopeList
              )}
              secondary={defaultObservationPlanInfo(
                default_observation_plan,
                groups
              )}
              classes={textClasses}
            />
            <Button
              key={default_observation_plan.id}
              id="delete_button"
              classes={{
                root: classes.defaultObservationPlanDelete,
                disabled: classes.defaultObservationPlanDeleteDisabled,
              }}
              onClick={() =>
                deleteDefaultObservationPlan(default_observation_plan)
              }
              disabled={!deletePermission}
            >
              &times;
            </Button>
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const AllocationPage = () => {
  const { allocationList } = useSelector((state) => state.allocations);
  const { defaultObservationPlanList } = useSelector(
    (state) => state.default_observation_plans
  );
  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");

  return (
    <Grid container spacing={3}>
      <Grid item md={6} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">List of Allocations</Typography>
            <AllocationList
              allocations={allocationList}
              deletePermission={permission}
            />
          </div>
        </Paper>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">
              List of Default Observation Plans
            </Typography>
            <DefaultObservationPlanList
              default_observation_plans={defaultObservationPlanList}
              deletePermission={permission}
            />
          </div>
        </Paper>
      </Grid>
      {permission && (
        <>
          <Grid item md={6} sm={12}>
            <Paper>
              <div className={classes.paperContent}>
                <Typography variant="h6">Add a New Allocation</Typography>
                <NewAllocation />
              </div>
            </Paper>
            <Paper>
              <div className={classes.paperContent}>
                <Typography variant="h6">
                  Add a New Default Observation Plan
                </Typography>
                <NewDefaultObservationPlan />
              </div>
            </Paper>
          </Grid>
        </>
      )}
    </Grid>
  );
};

AllocationList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  allocations: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

DefaultObservationPlanList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  default_observation_plans: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

export default AllocationPage;
