import { useEffect, useState } from "react";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  useGetBrokerFiltersQuery,
  useSaveBrokerFilterMutation,
} from "../../ducks/brokers";

interface LasairFilterBuilderProps {
  brokerId: number;
  survey: string;
  onPreview: (params: Record<string, unknown>) => void;
}

// Lasair's query API is Select / From tables / Where (raw SQL parts), which is
// what a filter here edits directly (joins, aliases, functions like mjdnow(),
// NOT IN — none of which a single-table condition tree can express). Column
// names differ by instance (ZTF vs LSST); the schema browser lists them all:
//   https://lasair-ztf.lsst.ac.uk/schema  /  https://lasair.lsst.ac.uk/schema
const DEFAULTS = {
  LSST: {
    selected: "objects.diaObjectId, objects.ra, objects.decl",
    tables: "objects",
  },
  ZTF: {
    selected: "objects.objectId, objects.ramean, objects.decmean",
    tables: "objects",
  },
} as const;

const REFERENCE_TABLES =
  "objects, sherlock_classifications, crossmatch_tns, watchlist_hits";

const LasairFilterBuilder = ({
  brokerId,
  survey,
  onPreview,
}: LasairFilterBuilderProps) => {
  const defaults = survey === "LSST" ? DEFAULTS.LSST : DEFAULTS.ZTF;
  const { data: filters } = useGetBrokerFiltersQuery(brokerId);
  const [saveFilter, saveState] = useSaveBrokerFilterMutation();

  const [filterId, setFilterId] = useState<number | "">("");
  const [selected, setSelected] = useState<string>(defaults.selected);
  const [tables, setTables] = useState<string>(defaults.tables);
  const [conditions, setConditions] = useState<string>("");

  // Load the chosen filter's saved query (or fall back to survey defaults).
  useEffect(() => {
    if (filterId === "") return;
    const f = (filters || []).find((x) => x.id === filterId);
    const lasair = (f?.altdata as any)?.lasair;
    setSelected(lasair?.selected ?? defaults.selected);
    setTables(lasair?.tables ?? defaults.tables);
    setConditions(lasair?.conditions ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterId, filters]);

  const canSave = filterId !== "" && selected.trim() && tables.trim();

  return (
    <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 1.5 }}>
      <Typography variant="subtitle1">Lasair query filter</Typography>

      <TextField
        size="small"
        label="Select (fields)"
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        multiline
        minRows={2}
      />
      <TextField
        size="small"
        label="From (tables)"
        value={tables}
        onChange={(e) => setTables(e.target.value)}
        helperText={`Comma-separated; joins allowed. Available: ${REFERENCE_TABLES}`}
      />
      <TextField
        size="small"
        label="Where (conditions)"
        value={conditions}
        onChange={(e) => setConditions(e.target.value)}
        multiline
        minRows={3}
        placeholder="objects.nDiaSources > 2 AND ... AND objects.firstDiaSourceMjdTai > (mjdnow() - 40)"
      />

      <Box
        sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}
      >
        <Button
          variant="outlined"
          onClick={() => onPreview({ selected, tables, conditions, limit: 20 })}
          disabled={!selected.trim() || !tables.trim()}
        >
          Preview
        </Button>

        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel id={`lasair-filter-${brokerId}`}>
            Save to filter
          </InputLabel>
          <Select
            labelId={`lasair-filter-${brokerId}`}
            label="Save to filter"
            value={filterId}
            onChange={(e) => setFilterId(e.target.value as number)}
          >
            {(filters || []).map((f) => (
              <MenuItem key={f.id} value={f.id}>
                {f.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Button
          variant="contained"
          disabled={!canSave || saveState.isLoading}
          onClick={() =>
            filterId !== "" &&
            saveFilter({
              brokerId,
              filterId,
              query: {
                selected: selected.trim(),
                tables: tables.trim(),
                conditions: conditions.trim(),
              },
            })
          }
        >
          {saveState.isLoading ? "Saving…" : "Save"}
        </Button>

        {saveState.isSuccess && (
          <Typography variant="body2" color="success.main">
            Saved.
          </Typography>
        )}
        {saveState.isError && (
          <Typography variant="body2" color="error">
            Save failed.
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default LasairFilterBuilder;
