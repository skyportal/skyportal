import React from "react";
import { TabContext, TabList, TabPanel } from "@mui/lab";
import Tab from "@mui/material/Tab";

import { useGetDefaultSurveyEfficienciesQuery } from "../../ducks/default_survey_efficiencies";
import { useGetDefaultObservationPlansQuery } from "../../ducks/default_observation_plans";
import { useGetAllocationsQuery } from "../../ducks/allocations";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import Spinner from "../Spinner";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import AllocationTable from "./AllocationTable";
import DefaultObservationPlanTable from "../observation_plan/DefaultObservationPlanTable";
import DefaultSurveyEfficiencyTable from "../survey_efficiency/DefaultSurveyEfficiencyTable";

const AllocationList = () => {
  const { data: defaultObservationPlanList = [] } =
    useGetDefaultObservationPlansQuery();
  const { data: defaultSurveyEfficiencyList = [] } =
    useGetDefaultSurveyEfficienciesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: allocationList } = useGetAllocationsQuery();
  const { data: currentUser } = useGetProfileQuery();
  const groups = useGetGroupsQuery().data?.all ?? null;

  const hasPermission = (specificPermission: string) =>
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes(specificPermission) ||
    false;

  const [tabIndex, setTabIndex] = React.useState(1);

  if (tabIndex == 1 && allocationList == null) return <Spinner />;

  return (
    <TabContext value={tabIndex}>
      <TabList onChange={(_, newValue) => setTabIndex(newValue)} centered>
        <Tab label="Allocations" value={1} />
        <Tab label="Default Observation Plans" value={2} />
        <Tab label="Default Survey Efficiencies" value={3} />
      </TabList>
      <TabPanel value={1}>
        <AllocationTable
          instruments={instrumentList}
          telescopes={telescopeList}
          groups={groups as any}
          allocations={allocationList as any}
          managePermission={hasPermission("Manage allocations")}
          fixedHeader={true}
        />
      </TabPanel>
      <TabPanel value={2}>
        <DefaultObservationPlanTable
          default_observation_plans={defaultObservationPlanList}
          instruments={instrumentList}
          telescopes={telescopeList}
          deletePermission={hasPermission("Manage observation plans")}
        />
      </TabPanel>
      <TabPanel value={3}>
        <DefaultSurveyEfficiencyTable
          default_survey_efficiencies={defaultSurveyEfficiencyList}
          deletePermission={hasPermission("Manage observation plans")}
        />
      </TabPanel>
    </TabContext>
  );
};

export default AllocationList;
