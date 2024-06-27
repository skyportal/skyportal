import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import makeStyles from "@mui/styles/makeStyles";
import Grid from "@mui/material/Grid";
import CircularProgress from "@mui/material/CircularProgress";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import * as defaultSurveyEfficienciesActions from "../../ducks/default_survey_efficiencies";
import * as defaultObservationPlansActions from "../../ducks/default_observation_plans";
import * as allocationsActions from "../../ducks/allocations";
import Spinner from "../Spinner";
import AllocationTable from "./AllocationTable";
import DefaultObservationPlanTable from "../observation_plan/DefaultObservationPlanTable";
import DefaultSurveyEfficiencyTable from "../survey_efficiency/DefaultSurveyEfficiencyTable";

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

const AllocationList = ({ deletePermission }) => {
  const dispatch = useDispatch();
  const classes = useStyles();

  const allocationsState = useSelector((state) => state.allocations);
  const instrumentsState = useSelector((state) => state.instruments);
  const telescopesState = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);
  const [rowsPerPage, setRowsPerPage] = useState(100);

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
          paginateCallback={handleAllocationTablePagination}
          totalMatches={allocationsState.totalMatches}
          pageNumber={allocationsState.pageNumber}
          numPerPage={allocationsState.numPerPage}
          sortingCallback={handleAllocationTableSorting}
          deletePermission={deletePermission}
        />
      )}
    </div>
  );
};

AllocationList.propTypes = {
  deletePermission: PropTypes.bool,
};

AllocationList.defaultProps = {
  deletePermission: false,
};

const AllocationPage = () => {
  const dispatch = useDispatch();

  const { defaultObservationPlanList } = useSelector(
    (state) => state.default_observation_plans,
  );
  const { defaultSurveyEfficiencyList } = useSelector(
    (state) => state.default_survey_efficiencies,
  );
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const currentUser = useSelector((state) => state.profile);

  const [rowsPerPage, setRowsPerPage] = useState(100);

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

  const [tabIndex, setTabIndex] = React.useState(0);

  const handleChangeTab = (event, newValue) => {
    setTabIndex(newValue);
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Tabs value={tabIndex} onChange={handleChangeTab} centered>
          <Tab label="Allocations" />
          <Tab label="Default Observation Plans" />
          <Tab label="Default Survey Efficiencies" />
        </Tabs>
      </Grid>
      {tabIndex === 0 && (
        <Grid item xs={12} style={{ paddingTop: 0 }}>
          <AllocationList deletePermission={permissionAllocation} />
        </Grid>
      )}
      {tabIndex === 1 && (
        <Grid item xs={12} style={{ paddingTop: 0 }}>
          <DefaultObservationPlanTable
            default_observation_plans={defaultObservationPlanList || []}
            instruments={instrumentList}
            telescopes={telescopeList}
            paginateCallback={handleDefaultObservationPlanTablePagination}
            totalMatches={defaultObservationPlanList.totalMatches}
            pageNumber={defaultObservationPlanList.pageNumber}
            numPerPage={defaultObservationPlanList.numPerPage}
            sortingCallback={handleDefaultObservationPlanTableSorting}
            deletePermission={permissionDefaultObservationPlan}
          />
        </Grid>
      )}
      {tabIndex === 2 && (
        <Grid item xs={12} style={{ paddingTop: 0 }}>
          <DefaultSurveyEfficiencyTable
            default_survey_efficiencies={defaultSurveyEfficiencyList || []}
            paginateCallback={handleDefaultSurveyEfficiencyTablePagination}
            totalMatches={defaultSurveyEfficiencyList.totalMatches}
            pageNumber={defaultSurveyEfficiencyList.pageNumber}
            numPerPage={defaultSurveyEfficiencyList.numPerPage}
            sortingCallback={handleDefaultSurveyEfficiencyTableSorting}
            deletePermission={permissionDefaultSurveyEfficiency}
          />
        </Grid>
      )}
    </Grid>
  );
};

export default AllocationPage;
