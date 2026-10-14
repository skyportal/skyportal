import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";

const PERMISSIONS = [
  { name: "canSave", label: "Can save to this group" },
  {
    name: "canSharePhotometry",
    label: "Can share photometry with other groups",
  },
  { name: "admin", label: "Group admin" },
] as const;

export type Permissions = Record<(typeof PERMISSIONS)[number]["name"], boolean>;

export const DEFAULT_PERMISSIONS: Permissions = {
  canSave: true,
  canSharePhotometry: false,
  admin: false,
};

interface MemberPermissionsProps {
  value: Permissions;
  onChange: (value: Permissions) => void;
  hide?: string[];
}

const MemberPermissions = ({
  value,
  onChange,
  hide = [],
}: MemberPermissionsProps) => (
  <FormGroup>
    {PERMISSIONS.filter(({ name }) => !hide.includes(name)).map(
      ({ name, label }) => (
        <FormControlLabel
          key={name}
          label={label}
          control={
            <Checkbox
              checked={value[name]}
              onChange={(event) =>
                onChange({ ...value, [name]: event.target.checked })
              }
              data-testid={`${name}Checkbox`}
            />
          }
        />
      ),
    )}
  </FormGroup>
);

export default MemberPermissions;
