import * as profileActions from "../../../ducks/profile";
import { useAppDispatch, useAppSelector } from "../../../types/hooks";
import { useGetTelescopesQuery } from "../../../ducks/telescopes";
import UserPreferencesHeader from "./UserPreferencesHeader";
import SelectWithChips from "../../SelectWithChips";

const ObservabilityPreferences = () => {
  const profile = useAppSelector((state) => state.profile.preferences) as any;
  const { data: telescopeListData = [] } = useGetTelescopesQuery();
  const telescopeList = [...telescopeListData];

  const dispatch = useAppDispatch();

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
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  telescopeList?.sort((a: any, b: any) => (a.name < b.name ? -1 : 1));
  telescopeList?.forEach((telescope: any) => {
    telescopeNametoID[telescope.name] = telescope.id;
    telescopeIDToName[telescope.id] = telescope.name;
  });
  const telescopeNameList = telescopeList
    .filter((telescope: any) => telescope.fixed_location)
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
