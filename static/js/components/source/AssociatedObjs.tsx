import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";

const SURVEY_LABELS: Record<string, string> = {
  DECAM: "DECam",
  ARGUS: "Argus",
};

interface AssociatedObj {
  obj_id: string;
  separation: number;
  survey?: string | null;
}

const AssociatedObjs = ({ objs }: { objs: AssociatedObj[] }) => (
  <>
    {objs.map((obj) => (
      <Tooltip
        key={obj.obj_id}
        title={`Same object, ${obj.separation.toFixed(2)}″ away`}
      >
        <Chip
          size="small"
          variant="outlined"
          clickable
          component={Link}
          to={`/source/${obj.obj_id}`}
          data-testid="associated-obj"
          label={
            <Box
              component="span"
              sx={{ display: "inline-flex", alignItems: "baseline", gap: 0.75 }}
            >
              {obj.survey && (
                <Box
                  component="span"
                  sx={{
                    fontSize: "0.65rem",
                    fontWeight: 600,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: "text.secondary",
                  }}
                >
                  {SURVEY_LABELS[obj.survey] ?? obj.survey}
                </Box>
              )}
              <Box
                component="span"
                sx={{
                  fontWeight: 600,
                  color: (theme) =>
                    theme.palette.mode === "dark"
                      ? theme.palette.secondary.main
                      : theme.palette.primary.main,
                }}
              >
                {obj.obj_id}
              </Box>
            </Box>
          }
        />
      </Tooltip>
    ))}
  </>
);

export default AssociatedObjs;
