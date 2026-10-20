import InstrumentTable from "./InstrumentTable";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useGetTelescopesQuery } from "../../ducks/telescopes";

const InstrumentList = () => {
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();

  return (
    <div data-testid="tour-instruments-list">
      <InstrumentTable
        instruments={instrumentList}
        telescopes={telescopeList}
        fixedHeader={true}
      />
    </div>
  );
};

export default InstrumentList;
