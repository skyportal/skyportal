import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";

import SegmentedControl from "../SegmentedControl";
import { guessSurvey } from "../broker/BrokerAlertSearch";

const SURVEY_LABELS: Record<string, string> = {
  DECAM: "DECam",
  ARGUS: "Argus",
};

interface AssociatedObj {
  obj_id: string;
  separation: number;
  survey?: string | null;
}

const surveyLabel = (survey?: string | null) =>
  survey ? (SURVEY_LABELS[survey] ?? survey) : "Other";

const SURVEY_ORDER = ["ZTF", "LSST", "DECam", "ASKAP", "Argus"];

const surveyRank = (label: string) => {
  const rank = SURVEY_ORDER.indexOf(label);
  return rank === -1 ? SURVEY_ORDER.length : rank;
};

const AssociatedObjs = ({
  sourceId,
  objs,
}: {
  sourceId: string;
  objs: AssociatedObj[];
}) => {
  const navigate = useNavigate();
  const entries = [
    { value: sourceId, label: surveyLabel(guessSurvey(sourceId)) },
    ...objs.map((obj) => ({
      value: obj.obj_id,
      label: surveyLabel(obj.survey),
    })),
  ].sort(
    (a, b) =>
      surveyRank(a.label) - surveyRank(b.label) ||
      a.value.localeCompare(b.value),
  );
  const counts: Record<string, number> = {};
  entries.forEach(({ label }) => {
    counts[label] = (counts[label] ?? 0) + 1;
  });
  const seen: Record<string, number> = {};
  const options = entries.map(({ value, label }) => {
    seen[label] = (seen[label] ?? 0) + 1;
    return {
      value,
      label: counts[label]! > 1 ? `${label} ${seen[label]}` : label,
    };
  });

  return (
    <Tooltip
      title={
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.25 }}>
          <Box sx={{ fontWeight: 600 }}>Same object in other surveys</Box>
          {objs.map((obj) => (
            <Box key={obj.obj_id}>
              {`${options.find((o) => o.value === obj.obj_id)!.label}: ${obj.obj_id}, ${obj.separation.toFixed(2)}″ away`}
            </Box>
          ))}
        </Box>
      }
    >
      <Box
        component="span"
        data-testid="associated-objs"
        sx={{ display: "inline-flex", ml: 0.5 }}
      >
        <SegmentedControl
          size="small"
          value={sourceId}
          options={options}
          onChange={(id) => id !== sourceId && navigate(`/source/${id}`)}
        />
      </Box>
    </Tooltip>
  );
};

export default AssociatedObjs;
