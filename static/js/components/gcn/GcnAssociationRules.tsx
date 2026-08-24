import { useState } from "react";

import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import Button from "../Button";
import GcnTagsSelect from "./GcnTagsSelect";
import {
  useDeleteGcnAssociationRuleMutation,
  useGetGcnAssociationRulesQuery,
  useSaveGcnAssociationRuleMutation,
} from "../../ducks/gcnAssociationRules";

const MESSENGERS = [
  "gravitational-wave",
  "neutrino",
  "gamma-ray-burst",
  "x-ray",
];

/** Days, rendered as the unit that makes the number readable. */
const humanWindow = (days: number) => {
  const seconds = days * 86400;
  if (seconds < 90) return `${seconds.toFixed(0)} s`;
  if (seconds < 5400) return `${(seconds / 60).toFixed(1)} min`;
  if (days < 1) return `${(days * 24).toFixed(1)} hr`;
  return `${days} d`;
};

const GcnAssociationRules = () => {
  const { data: rules } = useGetGcnAssociationRulesQuery();
  const [saveRule] = useSaveGcnAssociationRuleMutation();
  const [deleteRule] = useDeleteGcnAssociationRuleMutation();

  const [type1, setType1] = useState(MESSENGERS[0] as string);
  const [type2, setType2] = useState(MESSENGERS[1] as string);
  const [days, setDays] = useState("");
  const [minConsistency, setMinConsistency] = useState("0.5");
  const [tags1, setTags1] = useState<string[]>([]);
  const [tags2, setTags2] = useState<string[]>([]);

  const handleAdd = async () => {
    const parsedDays = Number(days);
    if (!parsedDays || parsedDays <= 0) return;
    await saveRule({
      detector_type_1: type1,
      detector_type_2: type2,
      days: parsedDays,
      min_consistency: Number(minConsistency) || 0.5,
      tags_1: tags1,
      tags_2: tags2,
    });
    setDays("");
    setTags1([]);
    setTags2([]);
  };

  return (
    <div>
      <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
        Your cuts for which event pairs count as coincident. No rules means no
        associations are searched for.
      </Typography>

      <Table size="small" data-testid="gcn-association-rules">
        <TableHead>
          <TableRow>
            <TableCell>Messengers</TableCell>
            <TableCell>Within</TableCell>
            <TableCell>Min consistency</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {(rules ?? []).map((rule) => (
            <TableRow key={rule.id} hover>
              <TableCell>
                {rule.detector_type_1}
                {rule.tags_1?.length
                  ? ` (${rule.tags_1.join(", ")})`
                  : ""} × {rule.detector_type_2}
                {rule.tags_2?.length ? ` (${rule.tags_2.join(", ")})` : ""}
              </TableCell>
              <TableCell>{humanWindow(rule.days)}</TableCell>
              <TableCell>{rule.min_consistency}</TableCell>
              <TableCell align="right">
                <IconButton
                  size="small"
                  aria-label={`delete rule ${rule.id}`}
                  onClick={() => deleteRule(rule.id)}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
          {!(rules ?? []).length && (
            <TableRow>
              <TableCell colSpan={4}>
                <Typography variant="body2" sx={{ color: "text.secondary" }}>
                  No rules yet.
                </Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <Stack
        direction="row"
        spacing={1}
        sx={{ mt: 2, alignItems: "center", flexWrap: "wrap", rowGap: 1 }}
      >
        {[
          {
            label: "First messenger",
            testid: "association-tags-1",
            type: type1,
            setType: setType1,
            tags: tags1,
            setTags: setTags1,
          },
          {
            label: "Second messenger",
            testid: "association-tags-2",
            type: type2,
            setType: setType2,
            tags: tags2,
            setTags: setTags2,
          },
        ].map((side) => (
          <Stack
            key={side.label}
            spacing={1}
            sx={{ minWidth: "13rem", maxWidth: "15rem" }}
          >
            <TextField
              select
              size="small"
              label={side.label}
              value={side.type}
              onChange={(event) => {
                side.setType(event.target.value);
                // the tags offered are this messenger's, so drop the old ones
                side.setTags([]);
              }}
            >
              {MESSENGERS.map((messenger) => (
                <MenuItem key={messenger} value={messenger}>
                  {messenger}
                </MenuItem>
              ))}
            </TextField>
            {/* SelectWithChips labels are not associated with their input,
                so the picker is addressed by test id rather than by label */}
            <div data-testid={side.testid}>
              <GcnTagsSelect
                title="Only events tagged"
                selectedGcnTags={side.tags}
                setSelectedGcnTags={side.setTags}
                detectorType={side.type}
              />
            </div>
          </Stack>
        ))}
        <TextField
          size="small"
          label="Within (days)"
          helperText="e.g. 0.0001 is 9 s"
          value={days}
          onChange={(event) => setDays(event.target.value)}
        />
        <TextField
          size="small"
          label="Min consistency"
          helperText="0 to 1"
          value={minConsistency}
          onChange={(event) => setMinConsistency(event.target.value)}
        />
        <Button primary onClick={handleAdd} name="addAssociationRule">
          Add
        </Button>
      </Stack>
    </div>
  );
};

export default GcnAssociationRules;
