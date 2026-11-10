import { useEffect, useState } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";

import { useSaveBrokerFilterMutation } from "../../../ducks/brokers";
import { useFilterBuilder } from "../../../hooks/useContexts";
import BlockComponent from "../../filter/boom/block/BlockComponent";
import LasairCreateDialog from "./LasairCreateDialog";
import { asRootBlocks } from "./lasairTree";

interface LasairBlocksProps {
  brokerId: number;
  filterId: number;
  filterName: string;
  survey: string;
  tree: any;
  onPreview: (params: Record<string, unknown>) => void;
}

const LasairBlocks = ({
  brokerId,
  filterId,
  filterName,
  survey,
  tree,
  onPreview,
}: LasairBlocksProps) => {
  const { filters, setFilters, fieldOptions, createDefaultBlock } =
    useFilterBuilder();
  const [saveFilter, { isLoading }] = useSaveBrokerFilterMutation();
  const [sql, setSql] = useState<
    { selected?: string; conditions?: string } | undefined
  >();

  const savedTree = JSON.stringify(tree ?? null);
  useEffect(() => {
    setFilters(tree ? asRootBlocks(tree) : [createDefaultBlock("And")]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedTree]);

  const openCreate = async () => {
    const result = await saveFilter({
      brokerId,
      filterId,
      query: { tree: filters },
    });
    if ("data" in result) setSql((result.data?.altdata as any)?.lasair);
  };

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
        <Button variant="contained" disabled={isLoading} onClick={openCreate}>
          Create on Lasair
        </Button>
        <Tooltip title="Not available yet: the Lasair API cannot create filters">
          <span>
            <Button
              variant="outlined"
              disabled
              onClick={() =>
                saveFilter({
                  brokerId,
                  filterId,
                  query: { tree: filters, publish: true },
                })
              }
            >
              Save to Lasair
            </Button>
          </span>
        </Tooltip>
      </Box>
      <LasairCreateDialog
        open={Boolean(sql)}
        onClose={() => setSql(undefined)}
        brokerId={brokerId}
        filterId={filterId}
        survey={survey}
        defaultName={filterName}
        tree={filters}
        sql={sql}
      />
    </Box>
  );
};

export default LasairBlocks;
