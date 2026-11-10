import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { ModelSpectrumFit } from "./modelSpectrumTraces";

type FitKey = string | number;

export interface FitStyle {
  color: string;
  dash: string; // Plotly line dash
}

interface ModelFitPickerProps {
  fits: ModelSpectrumFit[];
  // overlaid fits and the style each is drawn with
  shown: Map<FitKey, FitStyle>;
  onToggle: (key: FitKey) => void;
  onHover: (key: FitKey | null) => void;
  // plotted spectra's line colors, by spectrumKey
  spectrumColors: Map<string, string>;
}

// SVG approximations of Plotly's dash patterns.
const DASH_ARRAYS: Record<string, string | undefined> = {
  dash: "4 2.5",
  dot: "1.5 2",
  dashdot: "4 2 1.5 2",
  longdash: "7 2.5",
};

const LineSwatch = ({ color, dash }: { color: string; dash?: string }) => (
  <svg width="22" height="6" aria-hidden style={{ flex: "none" }}>
    <line
      x1="1"
      y1="3"
      x2="21"
      y2="3"
      stroke={color}
      strokeWidth={dash ? 2 : 1.5}
      strokeDasharray={dash ? DASH_ARRAYS[dash] : undefined}
    />
  </svg>
);

// One row per fitted spectrum, one column per service, so repeated runs read as
// a grid instead of a wall of near-identical labels.
const ModelFitPicker = ({
  fits,
  shown,
  onToggle,
  onHover,
  spectrumColors,
}: ModelFitPickerProps) => {
  const theme = useTheme();
  const services = [...new Set(fits.map((f) => f.service || ""))].sort();
  const rows = new Map<string, Map<string, ModelSpectrumFit>>();
  // fits come oldest first; the newest spectrum is the one usually wanted
  [...fits].reverse().forEach((fit) => {
    const spectrum = fit.spectrum || "";
    if (!rows.has(spectrum)) rows.set(spectrum, new Map());
    rows.get(spectrum)!.set(fit.service || "", fit);
  });

  return (
    <div style={{ padding: "0.5rem 1rem 1rem 1rem" }}>
      <Typography variant="subtitle2">
        Overlay model fit ({fits.length})
      </Typography>
      <div style={{ maxHeight: "15rem", overflowY: "auto" }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Spectrum</TableCell>
              {services.map((service) => (
                <TableCell key={service}>{service}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {[...rows.entries()].map(([spectrum, byService]) => {
              const sourceKey = [...byService.values()][0]?.sourceKey;
              const spectrumColor = sourceKey
                ? spectrumColors.get(sourceKey)
                : undefined;
              return (
                <TableRow key={spectrum}>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.4rem",
                      }}
                    >
                      {spectrumColor && <LineSwatch color={spectrumColor} />}
                      {spectrum}
                    </span>
                  </TableCell>
                  {services.map((service) => {
                    const fit = byService.get(service);
                    if (!fit) return <TableCell key={service} />;
                    const key = fit.id as FitKey;
                    const style = shown.get(key);
                    const text = style
                      ? theme.palette.getContrastText(style.color)
                      : undefined;
                    return (
                      <TableCell key={service} sx={{ maxWidth: "18rem" }}>
                        <Chip
                          size="small"
                          clickable
                          label={fit.summary || "fit"}
                          title={fit.summary || fit.label}
                          variant={style ? "filled" : "outlined"}
                          icon={
                            style ? (
                              <LineSwatch color={text!} dash={style.dash} />
                            ) : undefined
                          }
                          onClick={() => onToggle(key)}
                          onMouseEnter={() => onHover(key)}
                          onMouseLeave={() => onHover(null)}
                          sx={{
                            maxWidth: "100%",
                            ...(style && {
                              backgroundColor: style.color,
                              color: text,
                            }),
                            "&&:hover": style
                              ? { backgroundColor: style.color }
                              : {},
                          }}
                        />
                      </TableCell>
                    );
                  })}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default ModelFitPicker;
