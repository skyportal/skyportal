import { useContext, useMemo } from "react";
import ReactJson from "react-json-view";

import { ExpandAllContext } from "./ExpandableCell";

const JsonCell = ({ data }: { data: any }) => {
  const { expandAll } = useContext(ExpandAllContext);
  // ReactJson resets expansion whenever `src` changes identity, so key it on content
  const json = JSON.stringify(data ?? {});
  const src = useMemo(() => JSON.parse(json), [json]);
  return (
    <ReactJson
      src={src}
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
