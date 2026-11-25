import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Popover from "@mui/material/Popover";

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

const AssociatedObjs = ({ objs }: { objs: AssociatedObj[] }) => {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const counts = objs.reduce<Record<string, number>>((acc, obj) => {
    const label = surveyLabel(obj.survey);
    acc[label] = (acc[label] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <>
      <Chip
        size="small"
        variant="outlined"
        data-testid="associated-objs-button"
        label={Object.entries(counts)
          .map(([survey, n]) => (n > 1 ? `${survey} ×${n}` : survey))
          .join(" · ")}
        onClick={(e) => setAnchor(e.currentTarget)}
        sx={{
          fontWeight: 600,
          color: (theme) =>
            theme.palette.mode === "dark"
              ? theme.palette.secondary.main
              : theme.palette.primary.main,
        }}
      />
      <Popover
        open={Boolean(anchor)}
        anchorEl={anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        transformOrigin={{ vertical: -6, horizontal: "left" }}
      >
        <Box
          sx={{
            p: 1.5,
            display: "grid",
            gridTemplateColumns: "auto auto auto",
            columnGap: 2,
            rowGap: 0.5,
            fontSize: "0.85rem",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {objs.map((obj) => (
            <Box key={obj.obj_id} sx={{ display: "contents" }}>
              <Box sx={{ color: "text.secondary" }}>
                {surveyLabel(obj.survey)}
              </Box>
              <Link
                component={RouterLink}
                to={`/source/${obj.obj_id}`}
                underline="hover"
                sx={{ fontWeight: 600 }}
              >
                {obj.obj_id}
              </Link>
              <Box sx={{ color: "text.secondary", textAlign: "right" }}>
                {obj.separation.toFixed(2)}″
              </Box>
            </Box>
          ))}
        </Box>
      </Popover>
    </>
  );
};

export default AssociatedObjs;
