import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";

const SHARED_FIELDS = [
  { key: "affiliations", label: "Affiliations", shared: true },
  { key: "bio", label: "Bio", shared: true },
  { key: "contact_email", label: "Contact email", shared: false },
  { key: "contact_phone", label: "Contact phone", shared: false },
  { key: "roles", label: "User roles", shared: false },
  { key: "groups", label: "Groups", shared: false },
];

const PublicProfilePreferences = () => {
  const preferences = useGetProfileQuery().data?.preferences as any;
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

  const fieldToggled = (key: string) => (event: any) => {
    updateUserPreferences({ publicProfile: { [key]: event.target.checked } });
  };

  return (
    <FormGroup>
      {SHARED_FIELDS.map(({ key, label, shared }) => (
        <FormControlLabel
          key={key}
          control={
            <Switch
              checked={preferences?.publicProfile?.[key] ?? shared}
              name={`publicProfile_${key}`}
              onChange={fieldToggled(key)}
            />
          }
          label={label}
        />
      ))}
    </FormGroup>
  );
};

export default PublicProfilePreferences;
