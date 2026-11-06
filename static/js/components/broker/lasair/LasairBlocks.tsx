import { useEffect } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";

import { useSaveBrokerFilterMutation } from "../../../ducks/brokers";
import { useFilterBuilder } from "../../../hooks/useContexts";
import BlockComponent from "../../filter/boom/block/BlockComponent";
import { asRootBlocks } from "./lasairTree";

interface LasairBlocksProps {
  brokerId: number;
  filterId: number;
  tree: any;
  onPreview: (params: Record<string, unknown>) => void;
}

const LasairBlocks = ({
  brokerId,
  filterId,
  tree,
  onPreview,
}: LasairBlocksProps) => {
  const { filters, setFilters, fieldOptions, createDefaultBlock } =
    useFilterBuilder();
  const [saveFilter, { isLoading }] = useSaveBrokerFilterMutation();

  const savedTree = JSON.stringify(tree ?? null);
  useEffect(() => {
    setFilters(tree ? asRootBlocks(tree) : [createDefaultBlock("And")]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedTree]);

  return (
    <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 1.5 }}>
      {(filters || []).map((block: any, index: number) => (
        <BlockComponent
          key={block.id || index}
          block={block}
          parentBlockId={null}
          isRoot={index === 0}
          sentencePrefix="Keep objects that"
          fieldOptionsList={fieldOptions}
          localFilters={filters}
          setLocalFilters={setFilters}
        />
      ))}
      <Box sx={{ display: "flex", gap: 1 }}>
        <Button
          variant="outlined"
          onClick={() => onPreview({ tree: filters, limit: 20 })}
        >
          Preview
        </Button>
        <Button
          variant="contained"
          disabled={isLoading}
          onClick={() =>
            saveFilter({
              brokerId,
              filterId,
              query: { tree: filters, publish: true },
            })
          }
        >
          {isLoading ? "Saving…" : "Save to Lasair"}
        </Button>
      </Box>
    </Box>
  );
};

export default LasairBlocks;
