import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import React, { useState } from "react";
import Grid from "@mui/material/Grid";
import CircularProgress from "@mui/material/CircularProgress";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import { useGetDefaultSurveyEfficienciesQuery } from "../../ducks/default_survey_efficiencies";
import { useGetDefaultObservationPlansQuery } from "../../ducks/default_observation_plans";
import { useGetAllocationsQuery } from "../../ducks/allocations";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import Spinner from "../Spinner";
import AllocationTableComponent from "./AllocationTable";
import DefaultObservationPlanTableComponent from "../observation_plan/DefaultObservationPlanTable";
import DefaultSurveyEfficiencyTableComponent from "../survey_efficiency/DefaultSurveyEfficiencyTable";
import { useGetInstrumentsQuery } from "../../ducks/instruments";

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

interface AllocationsTabProps {
  managePermission?: boolean;
}

const AllocationsTab = ({ managePermission = false }: AllocationsTabProps) => {
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const groups = useGetGroupsQuery().data?.all ?? null;
  const [rowsPerPage, setRowsPerPage] = useState(100);
  const [allocationQueryParams, setAllocationQueryParams] =
    useState<any>(undefined);

  const { data: allocationList } = useGetAllocationsQuery(
    allocationQueryParams,
  );

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
    setAllocationQueryParams(data);
  };

  const handleAllocationTableSorting = (sortData: any, filterData: any) => {
    const data: any = {
      ...filterData,
      pageNumber: 1,
      rowsPerPage,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setAllocationQueryParams(data);
  };

  if (allocationList == null) return <Spinner />;

  return (
    <AllocationTable
      instruments={instrumentList}
      telescopes={telescopeList}
      groups={groups}
      allocations={allocationList}
      paginateCallback={handleAllocationTablePagination}
      totalMatches={undefined}
      pageNumber={undefined}
      numPerPage={undefined}
      sortingCallback={handleAllocationTableSorting}
      managePermission={managePermission}
      fixedHeader={true}
    />
  );
};

const AllocationList = () => {
  const { data: defaultObservationPlanList } =
    useGetDefaultObservationPlansQuery();
  const { data: defaultSurveyEfficiencyList } =
    useGetDefaultSurveyEfficienciesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: currentUser } = useGetProfileQuery();

  const [, setRowsPerPage] = useState(100);

  const permissionAllocation =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage allocations") ||
    false;
  const permissionDefaultSurveyEfficiency =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage allocations") ||
    currentUser?.permissions?.includes("Manage observation plans") ||
    false;
  const permissionDefaultObservationPlan =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage observation plans") ||
    false;

  const handleDefaultObservationPlanTablePagination = (
    _pageNumber: number,
    numPerPage: number,
    _sortData: any,
    _filterData: any,
  ) => {
    setRowsPerPage(numPerPage);
  };

  const handleDefaultObservationPlanTableSorting = () => {};

  const handleDefaultSurveyEfficiencyTablePagination = (
    _pageNumber: number,
    numPerPage: number,
    _sortData: any,
    _filterData: any,
  ) => {
    setRowsPerPage(numPerPage);
  };

  const handleDefaultSurveyEfficiencyTableSorting = () => {};

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
          <AllocationsTab managePermission={permissionAllocation} />
        </Grid>
      )}
      {tabIndex === 1 && (
        <Grid size={12} style={{ paddingTop: 0 }}>
          <DefaultObservationPlanTable
            default_observation_plans={defaultObservationPlanList || []}
            instruments={instrumentList}
            telescopes={telescopeList}
            paginateCallback={handleDefaultObservationPlanTablePagination}
            totalMatches={(defaultObservationPlanList as any)?.totalMatches}
            pageNumber={(defaultObservationPlanList as any)?.pageNumber}
            numPerPage={(defaultObservationPlanList as any)?.numPerPage}
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
            totalMatches={(defaultSurveyEfficiencyList as any)?.totalMatches}
            pageNumber={(defaultSurveyEfficiencyList as any)?.pageNumber}
            numPerPage={(defaultSurveyEfficiencyList as any)?.numPerPage}
            sortingCallback={handleDefaultSurveyEfficiencyTableSorting}
            deletePermission={permissionDefaultSurveyEfficiency}
          />
        </Grid>
      )}
    </Grid>
  );
};

export default AllocationList;
