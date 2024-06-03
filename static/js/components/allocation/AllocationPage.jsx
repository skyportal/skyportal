import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import ModifyAllocation from "../ModifyAllocation";
import NewAllocation from "../NewAllocation";
import NewDefaultSurveyEfficiency from "../NewDefaultSurveyEfficiency";
import NewDefaultObservationPlan from "../NewDefaultObservationPlan";
import * as defaultSurveyEfficienciesActions from "../../ducks/default_survey_efficiencies";
import * as defaultObservationPlansActions from "../../ducks/default_observation_plans";
import * as allocationsActions from "../../ducks/allocations";
import AllocationTable from "./AllocationTable";
import DefaultObservationPlanTable from "../DefaultObservationPlanTable";
import DefaultSurveyEfficiencyTable from "../DefaultSurveyEfficiencyTable";
import Spinner from "../Spinner";

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
  hover: {
    "&:hover": {
      textDecoration: "underline",
    },
    color: theme.palette.mode === "dark" ? "#fafafa !important" : null,
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
    filterData,
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

const AllocationPage = () => {
  const { defaultObservationPlanList } = useSelector(
    (state) => state.default_observation_plans,
  );
  const { defaultSurveyEfficiencyList } = useSelector(
    (state) => state.default_survey_efficiencies,
  );

  const [rowsPerPage, setRowsPerPage] = useState(100);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const currentUser = useSelector((state) => state.profile);
  const classes = useStyles();

  const dispatch = useDispatch();

  const permissionAllocation =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations");
  const permissionDefaultSurveyEfficiency =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage allocations") ||
    currentUser.permissions?.includes("Manage observation plans");
  const permissionDefaultObservationPlan =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage observation plans");
  const anyPermission =
    permissionAllocation ||
    permissionDefaultSurveyEfficiency ||
    permissionDefaultObservationPlan;

  const handleDefaultObservationPlanTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData,
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

  const handleDefaultSurveyEfficiencyTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData,
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
    dispatch(
      defaultSurveyEfficienciesActions.fetchDefaultSurveyEfficiencies(data),
    );
  };

  const handleDefaultSurveyEfficiencyTableSorting = (sortData, filterData) => {
    const data = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(
      defaultSurveyEfficienciesActions.fetchDefaultSurveyEfficiencies(data),
    );
  };

  return (
    <Grid container spacing={3}>
      <Grid item md={anyPermission ? 8 : 12} sm={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <AllocationList deletePermission={permissionAllocation} />
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
                deletePermission={permissionDefaultObservationPlan}
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
            {defaultSurveyEfficiencyList && (
              <DefaultSurveyEfficiencyTable
                default_survey_efficiencies={defaultSurveyEfficiencyList}
                paginateCallback={handleDefaultSurveyEfficiencyTablePagination}
                totalMatches={defaultSurveyEfficiencyList.totalMatches}
                deletePermission={permissionDefaultSurveyEfficiency}
                pageNumber={defaultSurveyEfficiencyList.pageNumber}
                numPerPage={defaultSurveyEfficiencyList.numPerPage}
                sortingCallback={handleDefaultSurveyEfficiencyTableSorting}
              />
            )}
          </div>
        </Paper>
      </Grid>
      <Grid item md={4} sm={12}>
        {permissionAllocation && (
          <>
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
          </>
        )}
        <br />
        {permissionDefaultObservationPlan && (
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">
                Add a New Default Observation Plan
              </Typography>
              <NewDefaultObservationPlan />
            </div>
          </Paper>
        )}
        <br />
        {permissionDefaultSurveyEfficiency && (
          <Paper>
            <div className={classes.paperContent}>
              <Typography variant="h6">
                Add a New Default Survey Efficiency
              </Typography>
              <NewDefaultSurveyEfficiency />
            </div>
          </Paper>
        )}
      </Grid>
    </Grid>
  );
};

export default AllocationPage;
