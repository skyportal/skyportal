import { Fragment } from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";

interface AssociatedFollowup {
  instrument_id: number;
  instrument_name: string;
  status: string;
  run_date?: string | null;
}

interface AssociatedObj {
  obj_id: string;
  separation: number;
  survey?: string | null;
  followup?: AssociatedFollowup[];
}

const followupLabel = (followup: AssociatedFollowup) =>
  `${followup.instrument_name}${
    followup.run_date ? ` run of ${followup.run_date.slice(0, 10)}` : ""
  }: ${followup.status}`;

const AssociatedObjs = ({
  objs,
  ownInstrumentIds,
}: {
  objs: AssociatedObj[];
  ownInstrumentIds: Set<number>;
}) => (
  <>
    {objs.map((obj) => {
      const followups = obj.followup ?? [];
      const instruments = [
        ...new Map(
          followups.map((f) => [f.instrument_id, f.instrument_name]),
        ).entries(),
      ];
      return (
        <Box
          key={obj.obj_id}
          sx={{ display: "inline-flex", alignItems: "center", gap: 0.75 }}
        >
          <Tooltip title={`${obj.obj_id}, ${obj.separation.toFixed(2)}″ away`}>
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
                  sx={{
                    display: "inline-flex",
                    alignItems: "baseline",
                    gap: 0.75,
                  }}
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
                      {obj.survey}
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
                    {obj.obj_id.length > 12
                      ? `${obj.obj_id.slice(0, 8)}…`
                      : obj.obj_id}
                  </Box>
                </Box>
              }
            />
          </Tooltip>
          {instruments.length > 0 && (
            <Tooltip
              title={
                <>
                  {followups.map((f, i) => (
                    <div key={i}>
                      {followupLabel(f)}
                      {ownInstrumentIds.has(f.instrument_id) &&
                        " (also on this source)"}
                    </div>
                  ))}
                </>
              }
            >
              <Box
                component="span"
                data-testid="associated-obj-followup"
                sx={{ fontSize: "0.75rem", color: "text.secondary" }}
              >
                {instruments.map(([id, name], i) => (
                  <Fragment key={id}>
                    {i > 0 && ", "}
                    <Box
                      component="span"
                      sx={
                        ownInstrumentIds.has(id)
                          ? { color: "warning.main", fontWeight: 600 }
                          : undefined
                      }
                    >
                      {name}
                    </Box>
                  </Fragment>
                ))}
              </Box>
            </Tooltip>
          )}
        </Box>
      );
    })}
  </>
);

export default AssociatedObjs;
