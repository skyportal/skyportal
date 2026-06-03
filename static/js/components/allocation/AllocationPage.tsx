import React, { useEffect, useState } from "react";
import Grid from "@mui/material/Grid";
import CircularProgress from "@mui/material/CircularProgress";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as defaultSurveyEfficienciesActions from "../../ducks/default_survey_efficiencies";
import * as defaultObservationPlansActions from "../../ducks/default_observation_plans";
import * as allocationsActions from "../../ducks/allocations";
import Spinner from "../Spinner";
import AllocationTableComponent from "./AllocationTable";
import DefaultObservationPlanTableComponent from "../observation_plan/DefaultObservationPlanTable";
import DefaultSurveyEfficiencyTableComponent from "../survey_efficiency/DefaultSurveyEfficiencyTable";

const AllocationTable = AllocationTableComponent as any;
const DefaultObservationPlanTable = DefaultObservationPlanTableComponent as any;
const DefaultSurveyEfficiencyTable =
  DefaultSurveyEfficiencyTableComponent as any;

export function allocationTitle(
  allocation: any,
  instrumentList: any[],
  telescopeList: any[],
) {
  const { instrument_id } = allocation;
  const instrument = instrumentList?.filter((i) => i.id === instrument_id)[0];
  const telescope = telescopeList?.filter(
    (t) => t.id === instrument?.telescope_id,
  )[0];

  if (!instrument?.name || !telescope?.name) {
    return <CircularProgress color="secondary" />;
  }
  return `${instrument?.name}/${telescope?.nickname}`;
}

interface AllocationListProps {
  managePermission?: boolean;
}

const AllocationList = ({ managePermission = false }: AllocationListProps) => {
  const dispatch = useAppDispatch();
  const allocationsState = useAppSelector((state) => state["allocations"]);
  const instrumentsState = useAppSelector((state) => state["instruments"]);
  const telescopesState = useAppSelector((state) => state["telescopes"]);
  const groups = useAppSelector((state) => state.groups.all);
  const [rowsPerPage, setRowsPerPage] = useState(100);

  useEffect(() => {
    dispatch(allocationsActions.fetchAllocations());
  }, [dispatch]);

  const handleAllocationTablePagination = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    setRowsPerPage(numPerPage);
    const data: any = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch((allocationsActions.fetchAllocations as any)(data));
  };

  const handleAllocationTableSorting = (sortData: any, filterData: any) => {
    const data: any = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch((allocationsActions.fetchAllocations as any)(data));
  };

  if (!allocationsState.allocationList) return <Spinner />;

  return (
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
      managePermission={managePermission}
      fixedHeader={true}
    />
  );
};

const AllocationPage = () => {
  const dispatch = useAppDispatch();
  const { defaultObservationPlanList } = useAppSelector(
    (state) => state["default_observation_plans"],
  );
  const { defaultSurveyEfficiencyList } = useAppSelector(
    (state) => state["default_survey_efficiencies"],
  );
  const { instrumentList } = useAppSelector((state) => state["instruments"]);
  const { telescopeList } = useAppSelector((state) => state["telescopes"]);
  const currentUser = useAppSelector((state) => state.profile);

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
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    setRowsPerPage(numPerPage);
    const data: any = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(
      (defaultObservationPlansActions.fetchDefaultObservationPlans as any)(
        data,
      ),
    );
  };

  const handleDefaultObservationPlanTableSorting = (
    sortData: any,
    filterData: any,
  ) => {
    const data: any = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(
      (defaultObservationPlansActions.fetchDefaultObservationPlans as any)(
        data,
      ),
    );
  };

  const handleDefaultSurveyEfficiencyTablePagination = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
    filterData: any,
  ) => {
    setRowsPerPage(numPerPage);
    const data: any = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(
      (defaultSurveyEfficienciesActions.fetchDefaultSurveyEfficiencies as any)(
        data,
      ),
    );
  };

  const handleDefaultSurveyEfficiencyTableSorting = (
    sortData: any,
    filterData: any,
  ) => {
    const data: any = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    dispatch(
      (defaultSurveyEfficienciesActions.fetchDefaultSurveyEfficiencies as any)(
        data,
      ),
    );
  };

  const [tabIndex, setTabIndex] = React.useState(0);

  return (
    <Grid container spacing={3}>
      <Grid size={12}>
        <Tabs
          value={tabIndex}
          onChange={(_, newValue) => setTabIndex(newValue)}
          centered
        >
          <Tab label="Allocations" />
          <Tab label="Default Observation Plans" />
          <Tab label="Default Survey Efficiencies" />
        </Tabs>
      </Grid>
      {tabIndex === 0 && (
        <Grid size={12} style={{ paddingTop: 0 }}>
          <AllocationList managePermission={permissionAllocation} />
        </Grid>
      )}
      {tabIndex === 1 && (
        <Grid size={12} style={{ paddingTop: 0 }}>
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
        <Grid size={12} style={{ paddingTop: 0 }}>
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
