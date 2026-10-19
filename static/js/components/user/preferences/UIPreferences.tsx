import {
  OptionTile,
  PreferenceOptions,
} from "../../notifications/PreferenceOption";
import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";

const TOGGLES = [
  { key: "invertThumbnails", label: "Invert thumbnails" },
  { key: "useAMPM", label: "AM/PM times", text: "Instead of 24-hour times." },
  { key: "useRefMag", label: "Use reference magnitude" },
  { key: "showBotComments", label: "Show bot comments" },
  { key: "hideMLClassifications", label: "Hide ML classifications" },
  { key: "showSimilarSources", label: "Show similar sources" },
  {
    key: "hideSourceSummary",
    label: "Hide source summaries",
    text: "On source pages.",
  },
  {
    key: "showAISourceSummary",
    label: "Show AI source summaries",
    text: "On source pages.",
    hidden: (prefs: any) => prefs?.hideSourceSummary === true,
  },
  {
    key: "hideDataFromDiscovery",
    label: "Hide my data",
    text: "Never tell others it exists, or let them ask for it.",
  },
];

const UIPreferences = () => {
  const { data: profile } = useGetProfileQuery();
  const preferences = profile?.preferences as any;
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

  return (
    <PreferenceOptions>
      {TOGGLES.filter(({ hidden }) => !hidden?.(preferences)).map(
        ({ key, label, text }) => (
          <OptionTile
            key={key}
            checked={preferences?.[key] === true}
            name={key}
            title={label}
            text={text}
            onToggle={(checked) => updateUserPreferences({ [key]: checked })}
          />
        ),
      )}
    </PreferenceOptions>
  );
};

export default UIPreferences;
