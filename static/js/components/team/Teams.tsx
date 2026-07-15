/**
 * Teams management page: create teams from existing groups, give each a color,
 * logo, and background, and edit/delete them. A team is an organizational layer
 * over groups; it never changes data visibility.
 */
import React, { useState } from "react";

import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import MuiButton from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import FormControl from "@mui/material/FormControl";
import Grid from "@mui/material/Grid";
import Input from "@mui/material/Input";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";

import Button from "../Button";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetProfileQuery } from "../../ducks/profile";
import {
  useAddTeamMutation,
  useDeleteTeamMutation,
  useGetTeamsQuery,
  useUpdateTeamMutation,
} from "../../ducks/teams";
import type { Team } from "../../ducks/teams";

const useStyles = makeStyles()((theme) => ({
  container: {
    padding: "1rem",
    margin: "1rem 0",
  },
  field: {
    width: "50%",
    minWidth: "16rem",
    marginBottom: theme.spacing(2),
  },
  formControl: {
    margin: `${theme.spacing(1)} 0`,
    minWidth: "50%",
  },
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  colorRow: {
    display: "flex",
    gap: "1rem",
    alignItems: "center",
    marginBottom: theme.spacing(2),
  },
  teamCard: {
    padding: "0.75rem 1rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.4rem",
    height: "100%",
  },
  teamHeader: {
    display: "flex",
    alignItems: "center",
    gap: "0.6rem",
  },
}));

const emptyForm = {
  name: "",
  nickname: "",
  description: "",
  primary_color: "#457b9d",
  secondary_color: "#a8dadc",
  logo_url: "",
  background_url: "",
  group_ids: [] as number[],
};

const TeamForm = ({ team, onDone }: { team?: Team; onDone?: () => void }) => {
  const { classes } = useStyles();
  const { data: groupsData } = useGetGroupsQuery();
  const [addTeam] = useAddTeamMutation();
  const [updateTeam] = useUpdateTeamMutation();

  const accessibleGroups = groupsData?.userAccessible ?? [];
  const groupIDToName: Record<number, string> = {};
  accessibleGroups.forEach((g: any) => {
    groupIDToName[g.id] = g.name;
  });

  const [form, setForm] = useState({
    ...emptyForm,
    ...(team
      ? {
          name: team.name ?? "",
          nickname: team.nickname ?? "",
          description: team.description ?? "",
          primary_color: team.primary_color ?? "#457b9d",
          secondary_color: team.secondary_color ?? "#a8dadc",
          logo_url: team.logo_url ?? "",
          background_url: team.background_url ?? "",
          group_ids: (team.groups ?? []).map((g) => g.id),
        }
      : {}),
  });

  const handleChange = (event: any) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  // Read an uploaded logo as a data URI so it can be stored in `logo_url`
  // without a separate file-storage endpoint.
  const handleLogoFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () =>
      setForm((prev) => ({ ...prev, logo_url: String(reader.result) }));
    reader.readAsDataURL(file);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      if (team) {
        await updateTeam({ teamID: team.id, form_data: form }).unwrap();
      } else {
        await addTeam(form).unwrap();
        setForm(emptyForm);
      }
      onDone?.();
    } catch {
      // error notification handled by the API layer
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <Box>
        <TextField
          label="Team Name"
          name="name"
          value={form.name}
          onChange={handleChange}
          className={classes.field}
          required
        />
      </Box>
      <Box>
        <TextField
          label="Nickname"
          name="nickname"
          value={form.nickname}
          onChange={handleChange}
          className={classes.field}
        />
      </Box>
      <Box>
        <TextField
          label="Description"
          name="description"
          value={form.description}
          onChange={handleChange}
          className={classes.field}
        />
      </Box>
      <div className={classes.colorRow}>
        <TextField
          label="Primary color"
          name="primary_color"
          type="color"
          value={form.primary_color}
          onChange={handleChange}
          sx={{ width: "8rem" }}
        />
        <TextField
          label="Accent color"
          name="secondary_color"
          type="color"
          value={form.secondary_color}
          onChange={handleChange}
          sx={{ width: "8rem" }}
        />
      </div>
      <Box sx={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <TextField
          label="Logo URL"
          name="logo_url"
          value={form.logo_url}
          onChange={handleChange}
          className={classes.field}
          placeholder="/static/images/team_logos/ZTF.png"
        />
        {form.logo_url ? (
          <Avatar src={form.logo_url} alt="logo preview" />
        ) : null}
        <MuiButton variant="outlined" component="label" size="small">
          Upload logo
          <input
            type="file"
            accept="image/*"
            hidden
            onChange={handleLogoFile}
          />
        </MuiButton>
      </Box>
      <Box>
        <TextField
          label="Background URL"
          name="background_url"
          value={form.background_url}
          onChange={handleChange}
          className={classes.field}
        />
      </Box>
      <Box>
        <FormControl className={classes.formControl}>
          <InputLabel id="select-groups-label">Groups</InputLabel>
          <Select
            labelId="select-groups-label"
            id="teamGroupsSelect"
            name="group_ids"
            multiple
            value={form.group_ids}
            onChange={handleChange}
            input={<Input id="selectGroupsChip" />}
            renderValue={(selected: any) => (
              <div className={classes.chips}>
                {selected.map((value: number) => (
                  <Chip key={value} label={groupIDToName[value]} />
                ))}
              </div>
            )}
          >
            {accessibleGroups.map((group: any) => (
              <MenuItem key={group.id} value={group.id}>
                {group.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>
      <Box sx={{ display: "flex", gap: "0.5rem", mt: 1 }}>
        <Button primary type="submit">
          {team ? "Save Changes" : "Create Team"}
        </Button>
        {team && onDone ? (
          <Button secondary onClick={onDone}>
            Cancel
          </Button>
        ) : null}
      </Box>
    </form>
  );
};

const TeamCard = ({ team, canManage }: { team: Team; canManage: boolean }) => {
  const { classes } = useStyles();
  const [deleteTeam] = useDeleteTeamMutation();
  const [editing, setEditing] = useState(false);

  if (editing) {
    return (
      <Paper className={classes.teamCard}>
        <TeamForm team={team} onDone={() => setEditing(false)} />
      </Paper>
    );
  }

  return (
    <Paper className={classes.teamCard}>
      <div className={classes.teamHeader}>
        {team.logo_url ? (
          <Avatar src={team.logo_url} alt={team.name} />
        ) : (
          <span
            style={{
              width: 16,
              height: 16,
              borderRadius: "50%",
              backgroundColor: team.primary_color || "#9b9a9a",
            }}
          />
        )}
        <Typography variant="h6">{team.name}</Typography>
      </div>
      {team.description ? (
        <Typography variant="body2">{team.description}</Typography>
      ) : null}
      <Typography variant="caption">
        {(team.groups ?? []).length} group(s) · {(team.users ?? []).length}{" "}
        member(s)
      </Typography>
      <div className={classes.chips}>
        {(team.groups ?? []).map((g) => (
          <Chip key={g.id} size="small" label={g.name} sx={{ m: 0.25 }} />
        ))}
      </div>
      {canManage ? (
        <Box sx={{ display: "flex", gap: "0.25rem", mt: "auto" }}>
          <Tooltip title="Edit team">
            <IconButton
              size="small"
              onClick={() => setEditing(true)}
              data-testid={`editTeam_${team.id}`}
            >
              <EditIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete team">
            <IconButton
              size="small"
              color="error"
              onClick={() => {
                if (window.confirm(`Delete team "${team.name}"?`)) {
                  deleteTeam(team.id);
                }
              }}
              data-testid={`deleteTeam_${team.id}`}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      ) : null}
    </Paper>
  );
};

const Teams = () => {
  const { classes } = useStyles();
  const { data: teams } = useGetTeamsQuery();
  const { data: profile } = useGetProfileQuery();
  const permissions = profile?.permissions ?? [];
  const canManage =
    permissions.includes("Manage teams") ||
    permissions.includes("System admin");

  return (
    <div>
      {canManage ? (
        <Paper className={classes.container}>
          <Typography variant="h5" sx={{ mb: 1 }}>
            Create New Team
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            A team groups together the groups a collaboration works across,
            giving it a shared home, feed, and visual identity. It does not
            change who can see what.
          </Typography>
          <TeamForm />
        </Paper>
      ) : null}
      <Paper className={classes.container}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          Teams
        </Typography>
        <Grid container spacing={2}>
          {(teams ?? []).map((team) => (
            <Grid key={team.id} size={{ xs: 12, sm: 6, md: 4 }}>
              <TeamCard team={team} canManage={canManage} />
            </Grid>
          ))}
        </Grid>
      </Paper>
    </div>
  );
};

export default Teams;
