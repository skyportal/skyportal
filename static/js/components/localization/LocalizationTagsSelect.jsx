import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import SelectWithChips from "../SelectWithChips";

import * as localizationTagsActions from "../../ducks/localizationTags";

const LocalizationTagsSelect = (props) => {
  const dispatch = useDispatch();

  const { selectedLocalizationTags, setSelectedLocalizationTags } = props;
  let localizationTags = [];
  localizationTags = localizationTags.concat(
    useSelector((state) => state.localizationTags),
  );
  localizationTags.sort();

  useEffect(() => {
    dispatch(localizationTagsActions.fetchLocalizationTags());
  }, [dispatch]);

  const handleChange = (event) =>
    setSelectedLocalizationTags(event.target.value);

  return (
    <div>
      {localizationTags?.length > 0 && (
        <SelectWithChips
          label="Localization Tags"
          id="selectLocalizations"
          initValue={selectedLocalizationTags}
          onChange={handleChange}
          options={localizationTags}
        />
      )}
    </div>
  );
};

LocalizationTagsSelect.propTypes = {
  selectedLocalizationTags: PropTypes.arrayOf(PropTypes.string).isRequired,
  setSelectedLocalizationTags: PropTypes.func.isRequired,
};

export default LocalizationTagsSelect;
