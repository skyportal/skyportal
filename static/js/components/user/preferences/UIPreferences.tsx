import FormGroup from "@mui/material/FormGroup";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";

import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";

const TOGGLES = [
  { key: "invertThumbnails", label: "Invert thumbnails" },
  { key: "useAMPM", label: "24 Hour or AM/PM" },
  { key: "useRefMag", label: "Use Reference Magnitude" },
  { key: "showBotComments", label: "Bot Comments" },
  { key: "hideMLClassifications", label: "Hide ML-based Classifications" },
  { key: "showSimilarSources", label: "Show Similar Sources" },
  { key: "hideSourceSummary", label: "Hide Source Summaries on Source page" },
  {
    key: "showAISourceSummary",
    label: "Show AI Source Summaries on Source page",
    hidden: (prefs: any) => prefs?.hideSourceSummary === true,
  },
];

const UIPreferences = () => {
  const { data: profile } = useGetProfileQuery();
  const preferences = profile?.preferences as any;
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

  const prefToggled = (key: string) => (event: any) => {
    updateUserPreferences({ [key]: event.target.checked });
  };

  return (
    <FormGroup>
      {TOGGLES.filter(({ hidden }) => !hidden?.(preferences)).map(
        ({ key, label }) => (
          <FormControlLabel
            key={key}
            control={
              <Switch
                checked={preferences?.[key] === true}
                name={key}
                onChange={prefToggled(key)}
              />
            }
            label={label}
          />
        ),
      )}
    </FormGroup>
  );
};

export default UIPreferences;
