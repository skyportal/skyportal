import {
  useGetProfileQuery,
  useUpdateUserPreferencesMutation,
} from "../../../ducks/profile";
import { useGetTelescopesQuery } from "../../../ducks/telescopes";
import { useGetAcrossInstrumentsQuery } from "../../../ducks/across";
import UserPreferencesHeader from "./UserPreferencesHeader";
import SelectWithChips from "../../SelectWithChips";

const ObservabilityPreferences = () => {
  const { data: profileData } = useGetProfileQuery();
  const profile = (profileData?.preferences ?? {}) as any;
  const { data: telescopeListData = [] } = useGetTelescopesQuery();
  const { data: acrossInstruments = [] } = useGetAcrossInstrumentsQuery();
  const telescopeList = [...telescopeListData];
  // Telescopes backed by an ACROSS instrument (space facilities) are selectable
  // too, even though they have no fixed location; their visibility is computed
  // via the ACROSS calculator rather than airmass.
  const acrossTelescopeIds = new Set(
    acrossInstruments.map((inst: any) => inst.telescope_id),
  );

  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

  const telescopeNametoID: Record<string, any> = { "Clear selections": "-1" };
  const telescopeIDToName: Record<string, any> = { "-1": "Clear selections" };

  const handleChange = (event: any) => {
    const prefs = {
      observabilityTelescopes: event.target.value.includes("Clear selections")
        ? []
        : event.target.value.map(
            (telescopeName: string) => telescopeNametoID[telescopeName],
          ),
    };
    updateUserPreferences(prefs);
  };

  telescopeList?.sort((a: any, b: any) => (a.name < b.name ? -1 : 1));
  telescopeList?.forEach((telescope: any) => {
    telescopeNametoID[telescope.name] = telescope.id;
    telescopeIDToName[telescope.id] = telescope.name;
  });
  const telescopeNameList = telescopeList
    .filter(
      (telescope: any) =>
        telescope.fixed_location || acrossTelescopeIds.has(telescope.id),
    )
    .map((telescope: any) => telescope.name);
  telescopeNameList.unshift("Clear selections");

  return (
    <div style={{ marginBottom: "1rem" }}>
      <UserPreferencesHeader
        title="Observability Preferences"
        popupText={
          "The telescopes to display observability plots for on sources' observability pages. You can see 16 telescopes at a time, and change page to see more."
        }
      />
      <SelectWithChips
        label="Telescopes to show"
        id="selectTelescopes"
        initValue={profile?.observabilityTelescopes?.map(
          (telescopeID: any) => telescopeIDToName[telescopeID],
        )}
        onChange={handleChange}
        options={telescopeNameList}
      />
    </div>
  );
};

export default ObservabilityPreferences;
