import { useContext, useMemo } from "react";
import { useTheme } from "@mui/material/styles";
import ReactJson from "react-json-view";

import { ExpandAllContext } from "./ExpandableCell";

const JsonCell = ({ data }: { data: any }) => {
  const { expandAll } = useContext(ExpandAllContext);
  const darkTheme = useTheme().palette.mode === "dark";
  const json = JSON.stringify(data ?? {});
  // ReactJson drops a toggle when it re-renders in the same update (e.g. the grid focusing the cell)
  return useMemo(
    () => (
      <ReactJson
        key={String(expandAll)}
        src={JSON.parse(json)}
        theme={darkTheme ? "monokai" : "rjv-default"}
        collapsed={!expandAll}
        displayDataTypes={false}
        displayObjectSize={false}
        enableClipboard={false}
        name={false}
        style={{ fontSize: "12px", lineHeight: "1.4", background: "none" }}
      />
    ),
    [json, expandAll, darkTheme],
  );
};

export default JsonCell;
