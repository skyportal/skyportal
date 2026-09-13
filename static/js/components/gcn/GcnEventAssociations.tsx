import { useState } from "react";
import { Link } from "react-router-dom";

import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Table from "@mui/material/Table";
import Tooltip from "@mui/material/Tooltip";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";

import Button from "../Button";
import {
  useGetGcnEventAssociationsQuery,
  useVetGcnEventAssociationMutation,
} from "../../ducks/gcnEventAssociations";

const VERDICTS: [string, string][] = [
  ["confirmed", "CONFIRM"],
  ["rejected", "REJECT"],
  ["ambiguous", "AMBIGUOUS"],
];

const STATUS_COLOR: Record<string, any> = {
  confirmed: "success",
  rejected: "error",
  ambiguous: "warning",
  pending: "default",
};

/** A separation in the unit that reads: seconds for a neutrino, days for a GRB. */
const humanGap = (days: number) => {
  const seconds = Math.abs(days) * 86400;
  const sign = days < 0 ? "-" : "+";
  if (seconds < 90) return `${sign}${seconds.toFixed(1)} s`;
  if (seconds < 5400) return `${sign}${(seconds / 60).toFixed(1)} min`;
  if (Math.abs(days) < 1)
    return `${sign}${(Math.abs(days) * 24).toFixed(1)} hr`;
  return `${sign}${Math.abs(days).toFixed(2)} d`;
};

interface GcnEventAssociationsProps {
  dateobs: string;
}

const GcnEventAssociations = ({ dateobs }: GcnEventAssociationsProps) => {
  const [includeRejected, setIncludeRejected] = useState(false);
  const { data: associations } = useGetGcnEventAssociationsQuery({
    dateobs,
    includeRejected,
  });
  const [vet] = useVetGcnEventAssociationMutation();

  // The verdict buttons select; SAVE commits. Same as the source page: one
  // click should not be a permanent ruling.
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [explanations, setExplanations] = useState<Record<number, string>>({});

  const handleSave = async (id: number) => {
    const status = selected[id];
    if (!status) return;
    await vet({
      dateobs,
      association_id: id,
      status,
      explanation: explanations[id] ?? null,
    });
    setSelected({ ...selected, [id]: "" });
  };

  const rows = associations ?? [];

  return (
    <div>
      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={includeRejected}
            onChange={(event) => setIncludeRejected(event.target.checked)}
            slotProps={{
              input: { "aria-label": "show rejected associations" },
            }}
          />
        }
        label="Show rejected"
      />
      <Table size="small" data-testid="gcn-event-associations">
        <TableHead>
          <TableRow>
            <TableCell>Event</TableCell>
            <TableCell>Detectors</TableCell>
            <TableCell>
              <Tooltip title="How well the two localizations agree, as a fraction of the most they could. 1 means they agree as well as localizations of these shapes can, 0 means disjoint.">
                <span>Consistency</span>
              </Tooltip>
            </TableCell>
            <TableCell>Separation</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Verdict</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((association) => (
            <TableRow key={association.id} hover>
              <TableCell>
                <Link to={`/gcn_events/${association.dateobs}`}>
                  {dayjs(association.dateobs).format("YYYY-MM-DD HH:mm:ss")}
                </Link>
                {association.aliases?.length ? (
                  <Typography variant="caption" sx={{ display: "block" }}>
                    {association.aliases.join(", ")}
                  </Typography>
                ) : null}
              </TableCell>
              <TableCell>
                {(association.detectors ?? []).join(", ") ||
                  (association.tags ?? []).join(", ")}
              </TableCell>
              <TableCell>
                <Tooltip
                  title={`Sky-map overlap integral ${association.overlap}. Its ceiling is set by the localization areas, which is why this column normalises it to 0-1.`}
                >
                  <span>
                    {association.consistency === null ||
                    association.consistency === undefined
                      ? "—"
                      : association.consistency.toFixed(3)}
                  </span>
                </Tooltip>
              </TableCell>
              <TableCell>{humanGap(association.dt_days)}</TableCell>
              <TableCell>
                <Chip
                  size="small"
                  label={association.status}
                  color={STATUS_COLOR[association.status] ?? "default"}
                />
              </TableCell>
              <TableCell>
                {VERDICTS.map(([status, label]) => (
                  <Button
                    key={status}
                    onClick={() =>
                      setSelected({ ...selected, [association.id]: status })
                    }
                    primary={selected[association.id] === status}
                  >
                    {label}
                  </Button>
                ))}
                <TextField
                  size="small"
                  variant="standard"
                  placeholder="why"
                  value={explanations[association.id] ?? ""}
                  onChange={(event) =>
                    setExplanations({
                      ...explanations,
                      [association.id]: event.target.value,
                    })
                  }
                />
                <Button
                  secondary
                  disabled={!selected[association.id]}
                  onClick={() => handleSave(association.id)}
                  name={`saveAssociation${association.id}`}
                >
                  SAVE
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {!rows.length && (
            <TableRow>
              <TableCell colSpan={6}>
                <Typography variant="body2" sx={{ color: "text.secondary" }}>
                  No associated events.
                </Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
};

export default GcnEventAssociations;
