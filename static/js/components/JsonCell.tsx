import { useContext, useMemo } from "react";
import { useTheme } from "@mui/material/styles";
import ReactJson from "react-json-view";

import { ExpandAllContext } from "./ExpandableCell";

const JsonCell = ({ data }: { data: any }) => {
  const { expandAll } = useContext(ExpandAllContext);
  const darkTheme = useTheme().palette.mode === "dark";
  // ReactJson resets expansion whenever `src` changes identity, so key it on content
  const json = JSON.stringify(data ?? {});
  const src = useMemo(() => JSON.parse(json), [json]);
  return (
    <ReactJson
      key={String(expandAll)}
      src={src}
      theme={darkTheme ? "monokai" : "rjv-default"}
      collapsed={!expandAll}
      displayDataTypes={false}
      displayObjectSize={false}
      enableClipboard={false}
      name={false}
      style={{ fontSize: "12px", lineHeight: "1.4", background: "none" }}
    />
  );
};

export default JsonCell;
