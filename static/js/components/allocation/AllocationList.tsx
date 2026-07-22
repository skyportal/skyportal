import React from "react";
import { TabContext, TabList, TabPanel } from "@mui/lab";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";

import { useGetDefaultSurveyEfficienciesQuery } from "../../ducks/default_survey_efficiencies";
import { useGetDefaultObservationPlansQuery } from "../../ducks/default_observation_plans";
import { useGetAllocationsQuery } from "../../ducks/allocations";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useGetProfileQuery } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import Spinner from "../Spinner";
import AllocationTableComponent from "./AllocationTable";
import DefaultObservationPlanTableComponent from "../observation_plan/DefaultObservationPlanTable";
import DefaultSurveyEfficiencyTableComponent from "../survey_efficiency/DefaultSurveyEfficiencyTable";
import { useGetInstrumentsQuery } from "../../ducks/instruments";

const AllocationTable = AllocationTableComponent as any;
const DefaultObservationPlanTable = DefaultObservationPlanTableComponent as any;
const DefaultSurveyEfficiencyTable =
  DefaultSurveyEfficiencyTableComponent as any;

interface AllocationsTabProps {
  managePermission?: boolean;
}

const AllocationsTab = ({ managePermission = false }: AllocationsTabProps) => {
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const groups = useGetGroupsQuery().data?.all ?? null;
  const { data: allocationList } = useGetAllocationsQuery();

  if (allocationList == null) return <Spinner />;

  return (
    <AllocationTable
      instruments={instrumentList}
      telescopes={telescopeList}
      groups={groups}
      allocations={allocationList}
      managePermission={managePermission}
      fixedHeader={true}
    />
  );
};

const AllocationList = () => {
  const { data: defaultObservationPlanList = [] } =
    useGetDefaultObservationPlansQuery();
  const { data: defaultSurveyEfficiencyList = [] } =
    useGetDefaultSurveyEfficienciesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: currentUser } = useGetProfileQuery();

  const hasPermission = (specificPermission: string) =>
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes(specificPermission) ||
    false;

  const [tabIndex, setTabIndex] = React.useState("1");

  return (
    <TabContext value={tabIndex}>
      <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
        <TabList onChange={(_, newValue) => setTabIndex(newValue)} centered>
          <Tab label="Allocations" value="1" />
          <Tab label="Default Observation Plans" value="2" />
          <Tab label="Default Survey Efficiencies" value="3" />
        </TabList>
      </Box>
      <TabPanel value="1">
        <AllocationsTab
          managePermission={hasPermission("Manage allocations")}
        />
      </TabPanel>
      <TabPanel value="2">
        <DefaultObservationPlanTable
          default_observation_plans={defaultObservationPlanList}
          instruments={instrumentList}
          telescopes={telescopeList}
          deletePermission={hasPermission("Manage observation plans")}
        />
      </TabPanel>
      <TabPanel value="3">
        <DefaultSurveyEfficiencyTable
          default_survey_efficiencies={defaultSurveyEfficiencyList}
          deletePermission={hasPermission("Manage observation plans")}
        />
      </TabPanel>
    </TabContext>
  );
};

export default AllocationList;
