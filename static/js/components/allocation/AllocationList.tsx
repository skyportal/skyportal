import { useState } from "react";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

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

  const [tab, setTab] = useState(0);

  if (tab === 0 && allocationList == null) return <Spinner />;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Tabs
        value={tab}
        onChange={(_event, value) => setTab(value)}
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Allocations" />
        <Tab label="Default Observation Plans" />
        <Tab label="Default Survey Efficiencies" />
      </Tabs>
      {tab === 0 && (
        <AllocationTable
          instruments={instrumentList}
          telescopes={telescopeList}
          groups={groups as any}
          allocations={allocationList as any}
          managePermission={hasPermission("Manage allocations")}
          fixedHeader
        />
      )}
      {tab === 1 && (
        <DefaultObservationPlanTable
          default_observation_plans={defaultObservationPlanList}
          instruments={instrumentList}
          telescopes={telescopeList}
          managePermission={hasPermission("Manage observation plans")}
        />
      )}
      {tab === 2 && (
        <DefaultSurveyEfficiencyTable
          default_survey_efficiencies={defaultSurveyEfficiencyList}
        />
      )}
    </Box>
  );
};

export default AllocationList;
