import React from "react";
import { useSelector, useDispatch } from "react-redux";

import * as profileActions from "../ducks/profile";
import UserPreferencesHeader from "./UserPreferencesHeader";
import SelectWithChips from "./SelectWithChips";

const ObservabilityPreferences = () => {
  const profile = useSelector((state) => state.profile.preferences);
  const { telescopeList } = useSelector((state) => state.telescopes);

  const dispatch = useDispatch();

  const telescopeNametoID = { "Clear selections": "-1" };
  const telescopeIDToName = { "-1": "Clear selections" };

  const handleChange = (event) => {
    const prefs = {
      observabilityTelescopes: event.target.value.includes("Clear selections")
        ? []
        : event.target.value.map(
            (telescopeName) => telescopeNametoID[telescopeName]
          ),
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  telescopeList?.sort((a, b) => (a.name < b.name ? -1 : 1));
  telescopeList?.forEach((telescope) => {
    telescopeNametoID[telescope.name] = telescope.id;
    telescopeIDToName[telescope.id] = telescope.name;
  });
  const telescopeNameList = telescopeList
    .filter((telescope) => telescope.fixed_location)
    .map((telescope) => telescope.name);
  telescopeNameList.unshift("Clear selections");

  return (
    <div>
      <UserPreferencesHeader
        title="Observability Preferences"
        popupText={
          "The telescopes to display observability plots for on sources' observability pages. Leave blank to show all telescopes."
        }
      />
      <SelectWithChips
        label="Telescopes to show"
        id="selectTelescopes"
        initValue={profile?.observabilityTelescopes?.map(
          (telescopeID) => telescopeIDToName[telescopeID]
        )}
        onChange={handleChange}
        options={telescopeNameList}
      />
    </div>
  );
};

export default ObservabilityPreferences;
