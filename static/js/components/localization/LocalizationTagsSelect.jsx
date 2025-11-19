import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import SelectWithChips from "../SelectWithChips";

import * as localizationTagsActions from "../../ducks/localizationTags";

const LocalizationTagsSelect = ({
  title = "Localization Tags",
  selectedLocalizationTags,
  setSelectedLocalizationTags,
}) => {
  const dispatch = useDispatch();
  const localizationTags = [
    ...(useSelector((state) => state.localizationTags) || []),
  ].sort();

  useEffect(() => {
    dispatch(localizationTagsActions.fetchLocalizationTags());
  }, [dispatch]);

  if (!localizationTags?.length) return null;

  return (
    <SelectWithChips
      label={title}
      id="selectLocalizations"
      initValue={selectedLocalizationTags}
      onChange={(e) => setSelectedLocalizationTags(e.target.value)}
      options={localizationTags}
    />
  );
};

LocalizationTagsSelect.propTypes = {
  title: PropTypes.string,
  selectedLocalizationTags: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedLocalizationTags: PropTypes.func.isRequired,
};

export default LocalizationTagsSelect;
