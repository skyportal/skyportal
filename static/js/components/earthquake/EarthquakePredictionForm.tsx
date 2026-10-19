import { useState } from "react";
import Box from "@mui/material/Box";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { useSubmitPredictionMutation } from "../../ducks/earthquake";
import { useGetMMADetectorsQuery } from "../../ducks/mmadetector";
import Button from "../Button";

interface EarthquakePredictionFormProps {
  earthquake: { event_id: string };
}

const EarthquakePredictionForm = ({
  earthquake,
}: EarthquakePredictionFormProps) => {
  const { data: detectors = [] } = useGetMMADetectorsQuery();
  const [detectorId, setDetectorId] = useState<number | null>(null);
  const [submitPrediction, { isLoading }] = useSubmitPredictionMutation();
  const selectedId = detectorId ?? detectors[0]?.id;
  if (selectedId == null) {
    return (
      <Typography sx={{ color: "text.secondary" }}>
        Add an MMA detector to make predictions.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <TextField
        select
        size="small"
        label="MMA Detector"
        value={selectedId}
        onChange={(e) => setDetectorId(Number(e.target.value))}
        sx={{ minWidth: 200 }}
      >
        {detectors.map((detector: any) => (
          <MenuItem key={detector.id} value={detector.id}>
            {detector.name}
          </MenuItem>
        ))}
      </TextField>
      <Button
        primary
        loading={isLoading}
        onClick={() =>
          submitPrediction({
            id: earthquake.event_id,
            mmadetector_id: selectedId,
          })
        }
      >
        Predict
      </Button>
    </Box>
  );
};

export default EarthquakePredictionForm;
