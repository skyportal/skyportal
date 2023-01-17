import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import DeleteIcon from "@mui/icons-material/Delete";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import { showNotification } from "baselayer/components/Notifications";
import CircularProgress from "@mui/material/CircularProgress";
import ModifyAllocation from "./ModifyAllocation";
import NewAllocation from "./NewAllocation";
import NewDefaultSurveyEfficiency from "./NewDefaultSurveyEfficiency";
import NewDefaultObservationPlan from "./NewDefaultObservationPlan";

import * as defaultSurveyEfficienciesActions from "../ducks/default_survey_efficiencies";
import * as defaultObservationPlansActions from "../ducks/default_observation_plans";
import * as allocationsActions from "../ducks/allocations";
import Button from "./Button";
import ConfirmDeletionDialog from "./ConfirmDeletionDialog";
import AllocationTable from "./AllocationTable";
import DefaultObservationPlanTable from "./DefaultObservationPlanTable";
import Spinner from "./Spinner";

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
  hover: {
    "&:hover": {
      textDecoration: "underline",
    },
    color: theme.palette.mode === "dark" ? "#fafafa !important" : null,
  },
  defaultSurveyEfficiencyDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  defaultSurveyEfficiencyDeleteDisabled: {
    opacity: 0,
  },
}));

const textStyles = makeStyles(() => ({
  primary: {
    fontWeight: "bold",
    fontSize: "110%",
  },
}));

export function observationPlanTitle(
  default_observation_plan,
  instrumentList,
  telescopeList
) {
  const { allocation, default_plan_name } = default_observation_plan;
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

  const result = `${instrument?.name}/${telescope?.nickname} - ${default_plan_name}`;

  return result;
}

const userLabel = (user) => {
  let label = user.username;
  if (user.first_name && user.last_name) {
    label = `${user.first_name} ${user.last_name} (${user.username})`;
    if (user.contact_email) {
      label = `${label} (${user.contact_email})`;
    }
    if (user.affiliations && user.affiliations.length > 0) {
      label = `${label} (${user.affiliations.join()})`;
    }
  }
  return label;
};

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

  const allocation_users = [];
  if (allocation.allocation_users?.length > 0) {
    allocation.allocation_users.forEach((user) => {
      allocation_users.push(userLabel(user));
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
    if (allocation_users.length > 0) {
      result += ` / Admins: ${allocation_users.join(", ")}`;
    }
    result += ")";
  }

  return result;
}

export function defaultSurveyEfficiencyInfo(default_survey_efficiency) {
  let result = "";
  if (default_survey_efficiency?.payload) {
    result += `Payload: ${JSON.stringify(
      default_survey_efficiency?.payload,
      null,
      " "
    )}`;
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

const AllocationList = () => {
  const dispatch = useDispatch();
  const classes = useStyles();

  const allocationsState = useSelector((state) => state.allocations);
  const instrumentsState = useSelector((state) => state.instruments);
  const telescopesState = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);
  const currentUser = useSelector((state) => state.profile);
  const [rowsPerPage, setRowsPerPage] = useState(100);

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");

  useEffect(() => {
    dispatch(allocationsActions.fetchAllocations());
  }, [dispatch]);

  const handleAllocationTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData
  ) => {
    setRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(allocationsActions.fetchAllocations(data));
  };

  const handleAllocationTableSorting = (sortData, filterData) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(allocationsActions.fetchAllocations(data));
  };

  if (!allocationsState.allocationList) {
    return <Spinner />;
  }

  return (
    <div className={classes.paper}>
      <Typography variant="h6" display="inline">
        List of Allocations
      </Typography>
      {allocationsState.allocationList && (
        <AllocationTable
          instruments={instrumentsState.instrumentList}
          telescopes={telescopesState.telescopeList}
          groups={groups}
          allocations={allocationsState.allocationList}
          deletePermission={permission}
          paginateCallback={handleAllocationTablePagination}
          totalMatches={allocationsState.totalMatches}
          pageNumber={allocationsState.pageNumber}
          numPerPage={allocationsState.numPerPage}
          sortingCallback={handleAllocationTableSorting}
        />
      )}
    </div>
  );
};

const DefaultSurveyEfficiencyList = ({
  default_survey_efficiencies,
  deletePermission,
}) => {
  const dispatch = useDispatch();
  const classes = useStyles();
  const textClasses = textStyles();
  const groups = useSelector((state) => state.groups.all);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [defaultSurveyEfficiencyToDelete, setDefaultSurveyEfficiencyToDelete] =
    useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setDefaultSurveyEfficiencyToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setDefaultSurveyEfficiencyToDelete(null);
  };

  const deleteDefaultSurveyEfficiency = () => {
    dispatch(
      defaultSurveyEfficienciesActions.deleteDefaultSurveyEfficiency(
        defaultSurveyEfficiencyToDelete
      )
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Default survey efficiency deleted"));
        closeDialog();
      }
    });
  };

  return (
    <div className={classes.root}>
      <List component="nav">
        {default_survey_efficiencies?.map((default_survey_efficiency) => (
          <ListItem button key={default_survey_efficiency.id}>
            <ListItemText
              primary={
                default_survey_efficiency.default_observationplan_request
                  .default_plan_name
              }
              secondary={defaultSurveyEfficiencyInfo(
                default_survey_efficiency,
                groups
              )}
              classes={textClasses}
            />
            <Button
              key={default_survey_efficiency.id}
              id="delete_button"
              classes={{
                root: classes.defaultSurveyEfficiencyDelete,
                disabled: classes.defaultSurveyEfficiencyDeleteDisabled,
              }}
              onClick={() => openDialog(default_survey_efficiency.id)}
              disabled={!deletePermission}
            >
              <DeleteIcon />
            </Button>
            <ConfirmDeletionDialog
              deleteFunction={deleteDefaultSurveyEfficiency}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="default survey efficiency"
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const DefaultObservationPlanList = ({ default_observation_plans }) => {
  const classes = useStyles();
  const textClasses = textStyles();
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  return (
    <div className={classes.root}>
      <List component="nav">
        {default_observation_plans?.map((default_observation_plan) => (
          <ListItem button key={default_observation_plan.id}>
            <ListItemText
              primary={observationPlanTitle(
                default_observation_plan,
                instrumentList,
                telescopeList
              )}
              secondary={defaultObservationPlanInfo(
                default_observation_plan,
                groups
              )}
              classes={textClasses}
            />
          </ListItem>
        ))}
      </List>
    </div>
  );
};

const AllocationPage = () => {
  const { defaultObservationPlanList } = useSelector(
    (state) => state.default_observation_plans
  );
  const { defaultSurveyEfficiencyList } = useSelector(
    (state) => state.default_survey_efficiencies
  );

  const [rowsPerPage, setRowsPerPage] = useState(100);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();

  const dispatch = useDispatch();

  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");

  const handleDefaultObservationPlanTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData
  ) => {
    setRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(defaultObservationPlansActions.fetchDefaultObservationPlans(data));
  };

  const handleDefaultObservationPlanTableSorting = (sortData, filterData) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(defaultObservationPlansActions.fetchDefaultObservationPlans(data));
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={8} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">Allocations</Typography>
            <AllocationList deletePermission={permission} />
          </div>
        </Paper>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">
              List of Default Observation Plans
            </Typography>
            {defaultObservationPlanList && (
              <DefaultObservationPlanTable
                default_observation_plans={defaultObservationPlanList}
                instruments={instrumentList}
                telescopes={telescopeList}
                paginateCallback={handleDefaultObservationPlanTablePagination}
                totalMatches={defaultObservationPlanList.totalMatches}
                deletePermission={permission}
                pageNumber={defaultObservationPlanList.pageNumber}
                numPerPage={defaultObservationPlanList.numPerPage}
                sortingCallback={handleDefaultObservationPlanTableSorting}
              />
            )}
          </div>
        </Paper>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Typography variant="h6">
              List of Default Survey Efficiencies
            </Typography>
            <DefaultSurveyEfficiencyList
              default_survey_efficiencies={defaultSurveyEfficiencyList}
              deletePermission={permission}
            />
          </div>
        </Paper>
      </Grid>
      {permission && (
        <>
          <Grid item md={4} sm={12}>
            <Paper>
              <div className={classes.paperContent}>
                <Typography variant="h6">Add a New Allocation</Typography>
                <NewAllocation />
              </div>
            </Paper>
            <br />
            <Paper>
              <div className={classes.paperContent}>
                <Typography variant="h6">Modify an Allocation</Typography>
                <ModifyAllocation />
              </div>
            </Paper>
            <br />
            <Paper>
              <div className={classes.paperContent}>
                <Typography variant="h6">
                  Add a New Default Observation Plan
                </Typography>
                <NewDefaultObservationPlan />
              </div>
            </Paper>
            <Paper>
              <div className={classes.paperContent}>
                <Typography variant="h6">
                  Add a New Default Survey Efficiency
                </Typography>
                <NewDefaultSurveyEfficiency />
              </div>
            </Paper>
          </Grid>
        </>
      )}
    </Grid>
  );
};

DefaultObservationPlanList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  default_observation_plans: PropTypes.arrayOf(PropTypes.any).isRequired,
};

DefaultSurveyEfficiencyList.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  default_survey_efficiencies: PropTypes.arrayOf(PropTypes.any).isRequired,
  deletePermission: PropTypes.bool.isRequired,
};

export default AllocationPage;
