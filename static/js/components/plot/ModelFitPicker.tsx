import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

import { ModelSpectrumFit } from "./modelSpectrumTraces";

type FitKey = string | number;

interface ModelFitPickerProps {
  fits: ModelSpectrumFit[];
  // overlaid fits and the color each is drawn with
  shown: Map<FitKey, string>;
  onToggle: (key: FitKey) => void;
}

// One row per fitted spectrum, one column per service, so repeated runs read as
// a grid instead of a wall of near-identical labels.
const ModelFitPicker = ({ fits, shown, onToggle }: ModelFitPickerProps) => {
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
            {[...rows.entries()].map(([spectrum, byService]) => (
              <TableRow key={spectrum}>
                <TableCell sx={{ whiteSpace: "nowrap" }}>{spectrum}</TableCell>
                {services.map((service) => {
                  const fit = byService.get(service);
                  if (!fit) return <TableCell key={service} />;
                  const key = fit.id as FitKey;
                  const color = shown.get(key);
                  return (
                    <TableCell key={service} sx={{ maxWidth: "18rem" }}>
                      <Chip
                        size="small"
                        clickable
                        label={fit.summary || "fit"}
                        title={fit.summary || fit.label}
                        variant={color ? "filled" : "outlined"}
                        onClick={() => onToggle(key)}
                        sx={{
                          maxWidth: "100%",
                          ...(color && {
                            backgroundColor: color,
                            color: "#fff",
                          }),
                          "&&:hover": color ? { backgroundColor: color } : {},
                        }}
                      />
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default ModelFitPicker;
