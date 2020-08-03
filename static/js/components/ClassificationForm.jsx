import React, { useReducer } from 'react';
import { useDispatch } from 'react-redux';
import PropTypes from 'prop-types';
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import TextField from '@material-ui/core/TextField';
import Button from '@material-ui/core/Button';
import MenuItem from "@material-ui/core/MenuItem";
import Autocomplete from '@material-ui/lab/Autocomplete';
import { showNotification } from "baselayer/components/Notifications";
import * as Actions from '../ducks/source';


const ClassificationForm = ({ obj_id, taxonomyList }) => {
  const latestTaxonomyList = taxonomyList.filter((t) => t.isLatest);

  function reducer(state, action) {
    switch (action.name) {
      case 'taxonomy_index':
        return {
          ...state,
          [action.name]: action.value,
          allowed_classes: latestTaxonomyList[action.value].allowed_classes,
        };
      default:
        return {
          ...state,
          [action.name]: action.value
        };
    }
  }

  const reduxDispatch = useDispatch();

  const initialState = {
    isSubmitting: false,
    taxonomy_index: latestTaxonomyList.length > 0 ? 0 : null,
    classification: null,
    probability: 1.0,
    class_select_enabled: false,
    probability_select_enabled: false,
    probability_errored: false,
    allowed_classes: latestTaxonomyList.length > 0 ?
      latestTaxonomyList[0].allowed_classes : [null]
  };
  const [state, localDispatch] = useReducer(reducer, initialState);

  if (latestTaxonomyList.length === 0) {
    return (
      <b>
        No taxonomies loaded...
      </b>
    );
  }

  const handleTaxonomyChange = (event) => {
    localDispatch({ name: "taxonomy_index", value: event.target.value });
    localDispatch({ name: "classification", value: "" });
    localDispatch({ name: "class_select_enabled", value: true });
    localDispatch({ name: "probability_select_enabled", value: false });
    localDispatch({ name: "probability_errored", value: false });
    localDispatch({ name: "probability", value: 1.0 });
  };

  const handleClasschange = (event, value) => {
    localDispatch({ name: "classification", value });
    localDispatch({ name: "probability_select_enabled", value: true });
    localDispatch({ name: "probability", value: 1.0 });
  };

  const processProb = (event) => {
    // make sure that the probability in in [0,1], otherwise set
    // an error state on the entry
    if ((Number.isNaN(parseFloat(event.target.value))) ||
       ((parseFloat(event.target.value) > 1) ||
       (parseFloat(event.target.value) < 0))) {
      localDispatch({ name: "probability_errored", value: true });
    } else {
      localDispatch({ name: "probability_errored", value: false });
      localDispatch({ name: "probability", value: event.target.value });
    }
  };

  const onSubmit = async (event) => {
    // TODO: allow fine-grained user groups in submission
    event.preventDefault();
    localDispatch({ name: "isSubmitting", value: true });
    const formData = {
      taxonomy_id: latestTaxonomyList[state.taxonomy_index].id,
      obj_id,
      classification: state.classification.class,
      probability: parseFloat(state.probability)
    };
    const result = await reduxDispatch(Actions.addClassification(formData));
    if (result.status === "success") {
      reduxDispatch(showNotification("Classification saved"));
    }
    localDispatch({ name: "isSubmitting", value: false });
  };

  return (
    <div>
      <form onSubmit={onSubmit}>
        <div>
          <h3>Add Classification</h3>
          <InputLabel id="taxonomy-label">Taxonomy</InputLabel>
          <Select
            id="tax-select"
            defaultValue=""
            onChange={handleTaxonomyChange}
            style={{ fullWidth: "true", display: "flex", wrap: "nowrap" }}
          >
            {latestTaxonomyList.map((taxonomy, index) => (
              <MenuItem value={index} key={index.toString()}>
                {`${taxonomy.name} (${taxonomy.version})`}
              </MenuItem>
            ))}
          </Select>
          <div style={{ display: state.class_select_enabled ? "block" : "none" }}>
            <Autocomplete
              options={state.allowed_classes}
              id="classification"
              getOptionSelected={(option) => {
                if ((state.classification === null) || (state.classification === '')) {
                  return (true);
                }
                if (state.classification.class === '') {
                  return (true);
                }
                return state.classification.class === option.class;
              }}
              value={state.classification || ""}
              onChange={handleClasschange}
              getOptionLabel={(option) => option.class || ""}

              /* eslint-disable-next-line react/jsx-props-no-spreading */
              renderInput={(params) => <TextField {...params} style={{ width: '100%' }} label="Classification" fullWidth />}
              renderOption={(option) => {
                const val = `${option.label}`;
                return (
                  /* eslint-disable-next-line react/no-danger */
                  <div dangerouslySetInnerHTML={{ __html: val }} />
                );
              }}
            />
          </div>
          <div style={{ display: state.class_select_enabled && state.probability_select_enabled ? "block" : "none" }}>
            <TextField
              id="probability"
              label="Probability"
              error={state.probability_errored}
              type="number"
              defaultValue="1.0"
              helperText="[0-1]"
              InputLabelProps={{
                shrink: true,
              }}
              inputProps={{ min: "0", max: "1", step: "0.0001" }}
              onBlur={processProb}
            />
          </div>
          <br />
          <Button
            type="submit"
            id="classificationSubmitButton"
            disabled={state.isSubmitting ||
                      !(state.class_select_enabled && state.probability_select_enabled &&
                      !(state.probability_errored))}
            variant="contained"
          >
            ↵
          </Button>
        </div>
      </form>
    </div>
  );
};


ClassificationForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
  taxonomyList: PropTypes.arrayOf(PropTypes.shape({
    name: PropTypes.string,
    created_at: PropTypes.string,
    isLatest: PropTypes.bool,
    version: PropTypes.string,
  })).isRequired
};

export default ClassificationForm;
