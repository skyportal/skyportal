import { useEffect } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";

import { UnifiedBuilderProvider } from "../../contexts/UnifiedBuilderContext";
import { fetchSchema } from "../../ducks/boom_filter_modules";
import { setBrokerFilterTarget } from "../../ducks/brokerFilterTarget";
import { useFilterBuilder } from "../../hooks/useContexts";
import { useAppDispatch } from "../../types/hooks";
import FilterBuilderContent from "../filter/boom/FilterBuilderContent";

interface LasairFilterBuilderProps {
  brokerId: number;
  survey: string;
  onPreview: (tree: unknown) => void;
}

// Runs inside UnifiedBuilderProvider so it can read the live condition tree.
const LasairBuilderInner = ({
  brokerId,
  survey,
  onPreview,
}: LasairFilterBuilderProps) => {
  const dispatch = useAppDispatch();
  const { filters, localFilterData, hasBeenModified } = useFilterBuilder();
  useEffect(() => {
    setBrokerFilterTarget(brokerId);
    // Load the broker's field schema so the builder offers valid columns.
    dispatch(fetchSchema(survey));
  }, [brokerId, survey, dispatch]);

  const tree = hasBeenModified && localFilterData ? localFilterData : filters;

  return (
    <Box sx={{ mt: 2 }}>
      <FilterBuilderContent />
      <Button
        variant="contained"
        sx={{ mt: 1 }}
        onClick={() => onPreview(tree)}
      >
        Preview filter
      </Button>
    </Box>
  );
};

// Reuses the schema-driven UnifiedBuilder editor for a query-kind broker
// (Lasair): the user picks valid fields from the schema (so no invalid-column
// errors), and Preview sends the neutral tree to the provider, which compiles
// it to SQL server-side.
const LasairFilterBuilder = (props: LasairFilterBuilderProps) => (
  <UnifiedBuilderProvider mode="filter">
    <LasairBuilderInner {...props} />
  </UnifiedBuilderProvider>
);

export default LasairFilterBuilder;
