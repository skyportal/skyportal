import { useState } from "react";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Box from "@mui/material/Box";
import FormControlLabel from "@mui/material/FormControlLabel";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";

import Button from "../Button";
import SearchableSelect from "../SearchableSelect";
import Spinner from "../Spinner";
import UserAvatar, { getUserRealName } from "../user/UserAvatar";
import { useGetUsersQuery } from "../../ducks/users";
import {
  useAddInstanceManagerMutation,
  useGetInstanceManagersQuery,
  useRemoveInstanceManagerMutation,
  useUpdateInstanceManagerMutation,
  type InstanceManager,
} from "../../ducks/instanceManagers";

dayjs.extend(utc);

export const managerName = (manager: InstanceManager) =>
  getUserRealName(manager.first_name, manager.last_name) ||
  manager.username ||
  "";

const userLabel = (user: any) => {
  const name = getUserRealName(user.first_name, user.last_name);
  return name ? `${name} (${user.username})` : user.username;
};

const AddManager = ({ managers }: { managers: InstanceManager[] }) => {
  const { data: usersData } = useGetUsersQuery();
  const [addManager, { isLoading }] = useAddInstanceManagerMutation();
  const [user, setUser] = useState<any>(null);

  const managerIds = new Set(managers.map((manager) => manager.user_id));
  const options = (usersData?.users ?? []).filter(
    (candidate: any) => !managerIds.has(candidate.id),
  );

  const add = async () => {
    const { error } = await addManager(user.id);
    if (!error) setUser(null);
  };

  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      spacing={1.5}
      sx={{ alignItems: { sm: "center" } }}
    >
      <SearchableSelect
        label="Add a maintainer"
        value={user}
        onChange={(_event, value) => setUser(value)}
        options={options}
        getOptionLabel={userLabel}
        isOptionEqualToValue={(option: any, value: any) =>
          option.id === value.id
        }
        loading={!usersData}
        sx={{ flexGrow: 1, maxWidth: { sm: 420 } }}
      />
      <Button primary async loading={isLoading} disabled={!user} onClick={add}>
        Add
      </Button>
    </Stack>
  );
};

const ManagerCard = ({
  manager,
  isAdmin,
}: {
  manager: InstanceManager;
  isAdmin: boolean;
}) => {
  const [updateManager] = useUpdateInstanceManagerMutation();
  const [removeManager] = useRemoveInstanceManagerMutation();

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, height: "100%" }}>
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
        <UserAvatar
          size={48}
          noTooltip
          username={manager.username ?? ""}
          firstName={manager.first_name ?? null}
          lastName={manager.last_name ?? null}
          gravatarUrl={manager.gravatar_url}
          userId={manager.user_id}
        />
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography sx={{ fontWeight: 600 }} noWrap>
            {managerName(manager)}
          </Typography>
          {manager.affiliations?.length ? (
            <Typography variant="body2" color="text.secondary" noWrap>
              {manager.affiliations.join(", ")}
            </Typography>
          ) : null}
          {manager.email && (
            <Typography variant="body2" color="text.secondary" noWrap>
              {manager.email}
            </Typography>
          )}
          <Typography variant="caption" color="text.secondary">
            Since {dayjs.utc(manager.created_at).format("MMM D, YYYY")}
          </Typography>
        </Box>
        {isAdmin && (
          <Tooltip title="Remove">
            <IconButton
              size="small"
              onClick={() => removeManager(manager.user_id)}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Stack>
      {isAdmin && (
        <FormControlLabel
          sx={{ mt: 1, ml: 0 }}
          control={
            <Switch
              size="small"
              checked={manager.show_email}
              onChange={(event) =>
                updateManager({
                  userId: manager.user_id,
                  show_email: event.target.checked,
                })
              }
            />
          }
          label={
            <Typography variant="body2" color="text.secondary">
              Show email publicly
            </Typography>
          }
        />
      )}
    </Paper>
  );
};

const InstanceManagers = ({ isAdmin }: { isAdmin: boolean }) => {
  const { data: managers = [], isLoading } = useGetInstanceManagersQuery();

  if (isLoading) return <Spinner />;

  return (
    <Stack spacing={2}>
      <Typography color="text.secondary">
        The people who run this instance, shown on the login and About pages.
      </Typography>
      {isAdmin && <AddManager managers={managers} />}
      {managers.length === 0 ? (
        <Typography color="text.secondary">No maintainer yet.</Typography>
      ) : (
        <Grid container spacing={2}>
          {managers.map((manager) => (
            <Grid key={manager.user_id} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
              <ManagerCard manager={manager} isAdmin={isAdmin} />
            </Grid>
          ))}
        </Grid>
      )}
    </Stack>
  );
};

export default InstanceManagers;
