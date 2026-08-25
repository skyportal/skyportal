import InstrumentTable from "./InstrumentTable";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useGetProfileQuery } from "../../ducks/profile";

const InstrumentList = () => {
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: currentUser } = useGetProfileQuery();
  const managePermission =
    currentUser?.permissions?.includes("Manage instruments") ||
    currentUser?.permissions?.includes("System admin") ||
    false;

  return (
    <div data-testid="tour-instruments-list">
      <InstrumentTable
        instruments={instrumentList}
        telescopes={telescopeList}
        managePermission={managePermission}
        fixedHeader={true}
      />
    </div>
  );
};

export default InstrumentList;
