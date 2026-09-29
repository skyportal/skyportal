import { useGetAllocationsApiClassnameQuery } from "../../ducks/allocations";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useGetTelescopesQuery } from "../../ducks/telescopes";

const useTriggeredAllocations = () => {
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: allocationList = [] } = useGetAllocationsApiClassnameQuery();

  const allocations = allocationList.filter((allocation: any) =>
    allocation.types.includes("triggered"),
  );
  const instruments = instrumentList
    .filter((instrument: any) =>
      allocations.some(({ instrument_id }) => instrument_id === instrument.id),
    )
    .map((instrument: any) => ({
      ...instrument,
      label: `${
        telescopeList.find(({ id }: any) => id === instrument.telescope_id)
          ?.name
      } / ${instrument.name}`,
    }))
    .sort((a: any, b: any) => a.label.localeCompare(b.label));

  return { allocations, instruments };
};

export default useTriggeredAllocations;
