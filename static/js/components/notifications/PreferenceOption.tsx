import { ReactNode } from "react";

import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";

export const PreferenceOptions = ({ children }: { children: ReactNode }) => (
  <Box
    sx={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(14rem, 1fr))",
      gap: 1,
    }}
  >
    {children}
  </Box>
);

interface OptionTileProps {
  checked: boolean;
  name: string;
  title: string;
  text?: string | undefined;
  onToggle: (checked: boolean) => void;
}

export const OptionTile = ({
  checked,
  name,
  title,
  text,
  onToggle,
}: OptionTileProps) => (
  <Box
    onClick={() => onToggle(!checked)}
    sx={(theme) => ({
      display: "flex",
      alignItems: "center",
      gap: 1.25,
      padding: "0.5rem 0.25rem 0.5rem 0.75rem",
      borderRadius: 2,
      border: 1,
      borderColor: checked ? "primary.main" : "divider",
      backgroundColor: checked
        ? alpha(theme.palette.primary.main, 0.08)
        : "background.paper",
      cursor: "pointer",
      userSelect: "none",
      transition: "border-color 120ms, background-color 120ms",
      "&:hover": { borderColor: "primary.main" },
    })}
  >
    <Box sx={{ flexGrow: 1, minWidth: 0 }}>
      <Typography
        variant="body2"
        sx={{
          fontWeight: 500,
          lineHeight: 1.3,
          color: checked ? "primary.main" : "text.primary",
        }}
      >
        {title}
      </Typography>
      {text && (
        <Typography
          variant="caption"
          color="text.secondary"
          component="div"
          sx={{ lineHeight: 1.3 }}
        >
          {text}
        </Typography>
      )}
    </Box>
    <Checkbox
      size="small"
      checked={checked}
      name={name}
      onClick={(event) => event.stopPropagation()}
      onChange={(event) => onToggle(event.target.checked)}
      sx={{ padding: 0.5 }}
    />
  </Box>
);

interface PreferenceOptionProps {
  type: string;
  field: string;
  title: string;
  text?: string;
}

const PreferenceOption = ({
  type,
  field,
  title,
  text,
}: PreferenceOptionProps) => {
  const { data: profile } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

  return (
    <OptionTile
      checked={profile?.preferences["notifications"]?.[type]?.[field] === true}
      name={`${type}_${field}`}
      title={title}
      text={text}
      onToggle={(checked) =>
        updateUserPreferences({
          notifications: { [type]: { [field]: checked } },
        })
      }
    />
  );
};

export default PreferenceOption;
