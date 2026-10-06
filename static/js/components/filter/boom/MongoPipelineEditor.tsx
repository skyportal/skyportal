import { useState } from "react";
import TextField from "@mui/material/TextField";

import { isRawMongoPipeline } from "./pipelineFormat";

interface MongoPipelineEditorProps {
  pipeline: any[] | null;
  // Receives the parsed pipeline, or null while the text is not a valid one.
  onChange: (pipeline: any[] | null) => void;
}

const MongoPipelineEditor = ({
  pipeline,
  onChange,
}: MongoPipelineEditorProps) => {
  const [text, setText] = useState(() =>
    pipeline ? JSON.stringify(pipeline, null, 2) : "",
  );
  const [error, setError] = useState("");

  const handleChange = (value: string) => {
    setText(value);
    let parsed;
    try {
      parsed = JSON.parse(value);
    } catch (e: any) {
      setError(value.trim() ? `Invalid JSON: ${e.message}` : "");
      onChange(null);
      return;
    }
    if (!isRawMongoPipeline(parsed)) {
      setError(
        'Expected a MongoDB aggregation pipeline: a list of stages such as [{"$match": {...}}].',
      );
      onChange(null);
      return;
    }
    setError("");
    onChange(parsed);
  };

  return (
    <TextField
      multiline
      fullWidth
      minRows={16}
      value={text}
      onChange={(e) => handleChange(e.target.value)}
      error={!!error}
      helperText={
        error ||
        "Use Test/Preview filter output to run it on past alerts before saving."
      }
      placeholder='[{"$match": {"candidate.drb": {"$gt": 0.9}}}]'
      sx={{ "& textarea": { fontFamily: "monospace", fontSize: "0.8rem" } }}
    />
  );
};

export default MongoPipelineEditor;
