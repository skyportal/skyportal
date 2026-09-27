import { useState } from "react";

import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import MenuItem from "@mui/material/MenuItem";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Tooltip from "@mui/material/Tooltip";
import AddIcon from "@mui/icons-material/Add";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import Button from "../Button";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";
import GcnTagsSelect from "./GcnTagsSelect";
import { useGetGroupsQuery } from "../../ducks/groups";
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

type Side = { type: string; tags: string[] };
const INITIAL_SIDES: [Side, Side] = [
  { type: "gravitational-wave", tags: [] },
  { type: "neutrino", tags: [] },
];

const humanWindow = (days: number) => {
  const seconds = days * 86400;
  if (seconds < 90) return `${seconds.toFixed(0)} s`;
  if (seconds < 5400) return `${(seconds / 60).toFixed(1)} min`;
  if (days < 1) return `${(days * 24).toFixed(1)} hr`;
  return `${days} d`;
};

const MessengerFields = ({
  title,
  testId,
  side,
  onChange,
}: {
  title: string;
  testId: string;
  side: Side;
  onChange: (patch: Partial<Side>) => void;
}) => (
  <Box
    sx={{
      p: 2,
      borderRadius: 1,
      bgcolor: "action.hover",
      display: "flex",
      flexDirection: "column",
      gap: 2,
    }}
  >
    <Typography variant="subtitle2">{title}</Typography>
    <TextField
      select
      label="Messenger"
      value={side.type}
      onChange={(event) => onChange({ type: event.target.value, tags: [] })}
    >
      {MESSENGERS.map((messenger) => (
        <MenuItem key={messenger} value={messenger}>
          {messenger}
        </MenuItem>
      ))}
    </TextField>
    {/* SelectWithChips' label isn't tied to its input: tests use this id */}
    <div data-testid={testId}>
      <GcnTagsSelect
        title="Only with tags"
        selectedGcnTags={side.tags}
        setSelectedGcnTags={(tags: string[]) => onChange({ tags })}
        detectorType={side.type}
      />
    </div>
  </Box>
);

const RulesToolbar = ({ onAdd }: { onAdd: () => void }) => (
  <DataGridToolbar
    title="Association rules"
    showColumns={false}
    showQuickFilter={false}
    showExport={false}
  >
    <Tooltip title="New association rule">
      <IconButton onClick={onAdd}>
        <AddIcon />
      </IconButton>
    </Tooltip>
  </DataGridToolbar>
);

const GcnAssociationRules = () => {
  const { data: rules } = useGetGcnAssociationRulesQuery();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const [saveRule] = useSaveGcnAssociationRuleMutation();
  const [deleteRule] = useDeleteGcnAssociationRuleMutation();

  const [[first, second], setSides] = useState(INITIAL_SIDES);
  const [days, setDays] = useState("");
  const [minConsistency, setMinConsistency] = useState("0.5");
  const [groupId, setGroupId] = useState<number | "">("");
  const [showErrors, setShowErrors] = useState(false);
  const [open, setOpen] = useState(false);

  const consistency = Number(minConsistency);
  const daysInvalid = !Number(days) || Number(days) < 0;
  const consistencyInvalid =
    minConsistency === "" ||
    Number.isNaN(consistency) ||
    consistency < 0 ||
    consistency > 1;

  const handleAdd = async () => {
    setShowErrors(true);
    if (!groupId || daysInvalid || consistencyInvalid) return;
    const { error } = await saveRule({
      detector_type_1: first.type,
      detector_type_2: second.type,
      days: Number(days),
      group_id: groupId,
      min_consistency: consistency,
      tags_1: first.tags,
      tags_2: second.tags,
    });
    if (error) return;
    setOpen(false);
    setShowErrors(false);
    setDays("");
    setSides([
      { ...first, tags: [] },
      { ...second, tags: [] },
    ]);
  };

  const columns: any[] = [
    {
      field: "group_id",
      headerName: "Group",
      flex: 1,
      valueGetter: (value: number) =>
        groups.find((group: any) => group.id === value)?.name ?? value,
    },
    {
      field: "messengers",
      headerName: "Messengers",
      flex: 2,
      valueGetter: (_value: any, rule: any) =>
        [1, 2]
          .map((side) => {
            const tags = rule[`tags_${side}`];
            const type = rule[`detector_type_${side}`];
            return tags?.length ? `${type} (${tags.join(", ")})` : type;
          })
          .join(" × "),
    },
    {
      field: "days",
      headerName: "Within",
      flex: 1,
      valueFormatter: humanWindow,
    },
    { field: "min_consistency", headerName: "Min consistency", flex: 1 },
    {
      field: "actions",
      headerName: "",
      width: 60,
      sortable: false,
      align: "right",
      renderCell: ({ row }: any) => (
        <IconButton
          size="small"
          aria-label={`delete rule ${row.id}`}
          onClick={() => deleteRule(row.id)}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      ),
    },
  ];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Two events are linked when they arrive within the rule&apos;s window and
        their sky maps are consistent enough. Pairs without a rule are never
        linked.
      </Typography>
      <StyledDataGrid
        autoHeight
        data-testid="gcn-association-rules"
        rows={rules ?? []}
        columns={columns}
        hideFooter
        disableColumnMenu
        localeText={{ noRowsLabel: "No rules yet." }}
        slots={{ toolbar: RulesToolbar }}
        slotProps={{ toolbar: { onAdd: () => setOpen(true) } }}
        showToolbar
      />
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>Add a rule</DialogTitle>
        <DialogContent
          dividers
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "1fr auto 1fr" },
              gap: 2,
            }}
          >
            <MessengerFields
              title="First event"
              testId="association-tags-1"
              side={first}
              onChange={(patch) => setSides([{ ...first, ...patch }, second])}
            />
            <Typography
              variant="h5"
              sx={{
                alignSelf: "center",
                textAlign: "center",
                color: "text.secondary",
              }}
            >
              ×
            </Typography>
            <MessengerFields
              title="Second event"
              testId="association-tags-2"
              side={second}
              onChange={(patch) => setSides([first, { ...second, ...patch }])}
            />
          </Box>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
              gap: 2,
              alignItems: "start",
            }}
          >
            <TextField
              select
              label="Group"
              value={groupId}
              onChange={(event) => setGroupId(Number(event.target.value))}
              error={showErrors && !groupId}
              helperText={showErrors && !groupId ? "Pick a group" : " "}
            >
              {groups.map((group: any) => (
                <MenuItem key={group.id} value={group.id}>
                  {group.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Within (days)"
              value={days}
              onChange={(event) => setDays(event.target.value)}
              error={showErrors && daysInvalid}
              helperText={
                showErrors && daysInvalid
                  ? "Must be a number greater than 0"
                  : "e.g. 0.0001 is 9 s"
              }
            />
            <TextField
              label="Min consistency"
              value={minConsistency}
              onChange={(event) => setMinConsistency(event.target.value)}
              error={showErrors && consistencyInvalid}
              helperText="Between 0 and 1"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button primary onClick={handleAdd} name="addAssociationRule">
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default GcnAssociationRules;
