import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";
import type { FieldProps } from "@rjsf/utils";

// CCDs as seen on the sky, north up and east left.
const CCD_ROWS = [
  [13, 14, 15, 16],
  [9, 10, 11, 12],
  [5, 6, 7, 8],
  [1, 2, 3, 4],
];
const QUADRANT_ORDER = [1, 2, 4, 3];

const rcid = (ccd: number, quadrant: number) => 4 * (ccd - 1) + quadrant - 1;

const ZtfQuadrantsField = ({ formData, onChange, fieldPathId }: FieldProps) => {
  const missing = new Set<number>(formData || []);

  const toggle = (ids: number[]) => {
    const next = new Set(missing);
    const allMissing = ids.every((id) => next.has(id));
    ids.forEach((id) => (allMissing ? next.delete(id) : next.add(id)));
    onChange(
      [...next].sort((a, b) => a - b),
      fieldPathId.path,
    );
  };

  return (
    <Box sx={{ my: 2 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          maxWidth: 296,
          mb: 1,
        }}
      >
        <Typography variant="subtitle1">Active quadrants</Typography>
        <Typography variant="body2" color="text.secondary">
          {64 - missing.size} / 64
        </Typography>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "8px",
          width: 296,
          p: 1,
          borderRadius: 2,
          bgcolor: (theme) => alpha(theme.palette.text.primary, 0.04),
        }}
      >
        {CCD_ROWS.flat().map((ccd) => {
          const ids = QUADRANT_ORDER.map((q) => rcid(ccd, q));
          const ccdMissing = ids.every((id) => missing.has(id));
          return (
            <Box
              key={ccd}
              sx={{
                position: "relative",
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "2px",
              }}
            >
              {QUADRANT_ORDER.map((q) => {
                const id = rcid(ccd, q);
                const active = !missing.has(id);
                return (
                  <Tooltip key={id} title={`CCD ${ccd}, quadrant ${q}`}>
                    <ButtonBase
                      aria-pressed={active}
                      aria-label={`CCD ${ccd}, quadrant ${q}`}
                      onClick={() => toggle([id])}
                      sx={{
                        aspectRatio: "1",
                        borderRadius: "4px",
                        transition: "background-color 120ms, box-shadow 120ms",
                        ...(active
                          ? {
                              bgcolor: (theme) =>
                                alpha(theme.palette.primary.main, 0.75),
                              "&:hover": { bgcolor: "primary.main" },
                            }
                          : {
                              backgroundImage: (theme) =>
                                `repeating-linear-gradient(135deg, ${alpha(
                                  theme.palette.text.primary,
                                  0.18,
                                )} 0 2px, transparent 2px 6px)`,
                              boxShadow: (theme) =>
                                `inset 0 0 0 1px ${alpha(
                                  theme.palette.text.primary,
                                  0.2,
                                )}`,
                              "&:hover": {
                                boxShadow: (theme) =>
                                  `inset 0 0 0 1px ${theme.palette.primary.main}`,
                              },
                            }),
                      }}
                    />
                  </Tooltip>
                );
              })}
              <ButtonBase
                aria-label={`CCD ${ccd}`}
                onClick={() => toggle(ids)}
                sx={{
                  position: "absolute",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%, -50%)",
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  fontSize: 11,
                  fontWeight: 600,
                  bgcolor: "background.paper",
                  color: ccdMissing ? "text.disabled" : "text.primary",
                  boxShadow: (theme) =>
                    `0 0 0 1px ${alpha(theme.palette.text.primary, 0.15)}`,
                  "&:hover": { color: "primary.main" },
                }}
              >
                {ccd}
              </ButtonBase>
            </Box>
          );
        })}
      </Box>
      {missing.size > 0 && (
        <Button
          size="small"
          sx={{ mt: 1 }}
          onClick={() => onChange([], fieldPathId.path)}
        >
          Activate all
        </Button>
      )}
    </Box>
  );
};

export default ZtfQuadrantsField;
