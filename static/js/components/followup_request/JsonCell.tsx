import Box from "@mui/material/Box";
import { JSONTree } from "react-json-tree";

import ExpandableCell from "../ExpandableCell";

const JsonCell = ({ data }: { data: any }) => {
  const entries = Object.entries(data ?? {});
  return (
    <ExpandableCell
      count={entries.length}
      render={(visible, collapsible) => (
        <Box
          sx={{
            whiteSpace: "nowrap",
            ...(collapsible && { "& > ul": { pb: "2.5rem !important" } }),
          }}
        >
          <JSONTree
            data={Object.fromEntries(entries.slice(0, visible))}
            hideRoot
          />
        </Box>
      )}
    />
  );
};

export default JsonCell;
