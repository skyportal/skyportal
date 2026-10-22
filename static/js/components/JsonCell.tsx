import { useContext } from "react";
import ReactJson from "react-json-view";

import { ExpandAllContext } from "./ExpandableCell";

const JsonCell = ({ data }: { data: any }) => {
  const { expandAll } = useContext(ExpandAllContext);
  return (
    <ReactJson
      // ReactJson only reads `collapsed` on mount, so remount on toggle
      key={String(expandAll)}
      src={data ?? {}}
      theme="rjv-default"
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
