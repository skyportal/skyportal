import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";

import { useGetConfigQuery } from "../../ducks/config";
import {
  useDeleteLoginMutation,
  useGetProfileQuery,
} from "../../ducks/profile";
import Button from "../Button";
import { field } from "./ProfileFields";

interface AuthBackend {
  name: string;
  label: string;
}

const ProfileLogins = () => {
  const logins = useGetProfileQuery().data?.logins;
  const backends: AuthBackend[] =
    (useGetConfigQuery().data as any)?.authBackends ?? [];
  const [deleteLogin] = useDeleteLoginMutation();

  if (!logins || !backends.length) return null;

  const label = (name: string) =>
    backends
      .find((backend) => backend.name === name)
      ?.label.replace(/^Sign in with /, "") ?? name;
  const linked = new Set(logins.map((login) => login.provider));

  return field(
    "Logins",
    <Box
      component="span"
      sx={{
        display: "inline-flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 0.5,
      }}
    >
      {logins.map((login) => (
        <Chip
          key={login.id}
          size="small"
          label={label(login.provider)}
          onDelete={logins.length > 1 ? () => deleteLogin(login.id) : undefined}
        />
      ))}
      {backends
        .filter((backend) => !linked.has(backend.name))
        .map((backend) => (
          <Button
            key={backend.name}
            secondary
            size="small"
            href={`/login/${backend.name}/?next=/profile`}
          >
            Link {label(backend.name)}
          </Button>
        ))}
    </Box>,
  );
};

export default ProfileLogins;
