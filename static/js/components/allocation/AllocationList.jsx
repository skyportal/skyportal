import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Grid from "@mui/material/Grid";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import * as defaultSurveyEfficienciesActions from "../../ducks/default_survey_efficiencies";
import * as defaultObservationPlansActions from "../../ducks/default_observation_plans";
import * as allocationsActions from "../../ducks/allocations";
import Spinner from "../Spinner";
import AllocationTable from "./AllocationTable";
import DefaultObservationPlanTable from "../observation_plan/DefaultObservationPlanTable";
import DefaultSurveyEfficiencyTable from "../survey_efficiency/DefaultSurveyEfficiencyTable";

const AllocationList = () => {
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const { defaultObservationPlanList } = useSelector(
    (state) => state.default_observation_plans,
  );
  const { defaultSurveyEfficiencyList } = useSelector(
    (state) => state.default_survey_efficiencies,
  );
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const allocationsState = useSelector((state) => state.allocations);
  const instrumentsState = useSelector((state) => state.instruments);
  const telescopesState = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  const [tabIndex, setTabIndex] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(100);

  const hasPermission = (permission) =>
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes(permission);

  useEffect(() => {
    dispatch(allocationsActions.fetchAllocations());
  }, [dispatch]);

  const handleTablePagination =
    (fetchAction) => (pageNumber, numPerPage, sortData, filterData) => {
      setRowsPerPage(numPerPage);
      const data = { ...filterData, pageNumber, numPerPage };
      if (sortData?.name) {
        data.sortBy = sortData.name;
        data.sortOrder = sortData.direction;
      }
      dispatch(fetchAction(data));
    };

  const handleTableSorting = (fetchAction) => (sortData, filterData) => {
    dispatch(
      fetchAction({
        ...filterData,
        pageNumber: 1,
        rowsPerPage,
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      }),
    );
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12}>
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
        <Grid item xs={12} style={{ paddingTop: 0 }}>
          {!allocationsState.allocationList ? (
            <AllocationTable
              instruments={instrumentsState.instrumentList}
              telescopes={telescopesState.telescopeList}
              groups={groups}
              allocations={allocationsState.allocationList}
              paginateCallback={handleTablePagination(
                allocationsActions.fetchAllocations,
              )}
              totalMatches={allocationsState.totalMatches}
              pageNumber={allocationsState.pageNumber}
              numPerPage={allocationsState.numPerPage}
              sortingCallback={handleTableSorting(
                allocationsActions.fetchAllocations,
              )}
              managePermission={hasPermission("Manage allocations")}
              fixedHeader={true}
            />
          ) : (
            <Spinner />
          )}
        </Grid>
      )}
      {tabIndex === 1 && (
        <Grid item xs={12} style={{ paddingTop: 0 }}>
          <DefaultObservationPlanTable
            default_observation_plans={defaultObservationPlanList || []}
            instruments={instrumentList}
            telescopes={telescopeList}
            paginateCallback={handleTablePagination(
              defaultObservationPlansActions.fetchDefaultObservationPlans,
            )}
            totalMatches={defaultObservationPlanList.totalMatches}
            pageNumber={defaultObservationPlanList.pageNumber}
            numPerPage={defaultObservationPlanList.numPerPage}
            sortingCallback={handleTableSorting(
              defaultObservationPlansActions.fetchDefaultObservationPlans,
            )}
            managePermission={hasPermission("Manage observation plans")}
          />
        </Grid>
      )}
      {tabIndex === 2 && (
        <Grid item xs={12} style={{ paddingTop: 0 }}>
          <DefaultSurveyEfficiencyTable
            default_survey_efficiencies={defaultSurveyEfficiencyList || []}
            paginateCallback={handleTablePagination(
              defaultSurveyEfficienciesActions.fetchDefaultSurveyEfficiencies,
            )}
            totalMatches={defaultSurveyEfficiencyList.totalMatches}
            pageNumber={defaultSurveyEfficiencyList.pageNumber}
            numPerPage={defaultSurveyEfficiencyList.numPerPage}
            sortingCallback={handleTableSorting(
              defaultSurveyEfficienciesActions.fetchDefaultSurveyEfficiencies,
            )}
            deletePermission={
              hasPermission("Manage allocations") ||
              hasPermission("Manage observation plans")
            }
          />
        </Grid>
      )}
    </Grid>
  );
};

export default AllocationList;
