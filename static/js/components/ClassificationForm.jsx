/* eslint-disable react/jsx-props-no-spreading */
/* eslint-disable react/no-danger */

import React, { useReducer } from 'react';
import { useDispatch } from 'react-redux';
import PropTypes from 'prop-types';
import { useForm } from 'react-hook-form';
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import TextField from '@material-ui/core/TextField';
import Button from '@material-ui/core/Button';
import FormControl from "@material-ui/core/FormControl";
import MenuItem from "@material-ui/core/MenuItem";
import { makeStyles } from "@material-ui/core/styles";
import Autocomplete from '@material-ui/lab/Autocomplete';
import * as Actions from '../ducks/source';


function makeMenuItem(taxonomy, index) {
  const render_string = `${taxonomy.name} (${taxonomy.version})`;

  return (
    <MenuItem value={index} key={index.toString()}>
      {render_string}
    </MenuItem>
  );
}


const ClassificationForm = ({ obj_id, taxonomyList }) => {
  const latest_taxonomyList = taxonomyList.filter((t) => t.isLatest);

  function reducer(state, action) {
    switch (action.name) {
      case 'taxonomy_index':
        return {
          ...state,
          [action.name]: action.value,
          allowed_classes: latest_taxonomyList[action.value].allowed_classes,
        };
      default:
        return {
          ...state,
          [action.name]: action.value
        };
    }
  }

  const submitDispatch = useDispatch();

  const initialState = {
    taxonomy_index: latest_taxonomyList.length > 0 ? 0 : null,
    classification: null,
    probability: 1.0,
    class_select_enabled: false,
    probability_select_enabled: false,
    probability_errored: false,
    allowed_classes: latest_taxonomyList.length > 0 ?
      latest_taxonomyList[0].allowed_classes : [null]
  };
  const [state, dispatch] = useReducer(reducer, initialState);
  const { handleSubmit } = useForm();

  const useStyles = makeStyles((theme) => ({
    formControl: {
      margin: theme.spacing(1),
      fullWidth: true,
      display: 'flex',
      wrap: 'nowrap'
    }
  }));
  const classes = useStyles();

  if (latest_taxonomyList.length === 0) {
    return (
      <b>
        No taxonomies loaded...
      </b>
    );
  }

  const handleTaxonomyChange = (event) => {
    dispatch({ name: "taxonomy_index", value: event.target.value });
    dispatch({ name: "classification", value: "" });
    dispatch({ name: "class_select_enabled", value: true });
    dispatch({ name: "probability_select_enabled", value: false });
    dispatch({ name: "probability_errored", value: false });
    dispatch({ name: "probability", value: 1.0 });
  };

  const handleClasschange = (event, value) => {
    dispatch({ name: "classification", value });
    dispatch({ name: "probability_select_enabled", value: true });
  };

  const processProb = (event) => {
    // make sure that the probability in in [0,1], otherwise set
    // an error state on the entry
    if ((Number.isNaN(parseFloat(event.target.value))) ||
       ((parseFloat(event.target.value) > 1) ||
       (parseFloat(event.target.value) < 0))) {
      dispatch({ name: "probability_errored", value: true });
    } else {
      dispatch({ name: "probability_errored", value: false });
      dispatch({ name: "probability", value: event.target.value });
    }
  };

  const onSubmit = () => {
    // TODO: allow fine-grained user groups in submission
    const formData = {
      taxonomy_id: latest_taxonomyList[state.taxonomy_index].id,
      obj_id,
      classification: state.classification.class,
      probability: parseFloat(state.probability)
    };
    // We need to include this field in request, but it isn't in form data
    submitDispatch(Actions.addClassification(formData));
  };


  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div>
          <h3>Add Classification</h3>
          <FormControl className={classes.formControl}>
            <InputLabel id="taxonomy-label">Taxonomy</InputLabel>
            <Select
              id="tax-select"
              defaultValue=""
              onChange={handleTaxonomyChange}
            >
              {latest_taxonomyList.map((taxonomy, index) => makeMenuItem(
                taxonomy, index
              ))}
            </Select>
          </FormControl>
          <div style={{ display: state.class_select_enabled ? "block" : "none" }}>
            <Autocomplete
              options={state.allowed_classes}
              id="classification"
              getOptionSelected={(option) => {
                if (option === null) {
                  return (true);
                }
                if (option === '') {
                  return (true);
                }
                return (true);
              }}
              value={state.classification || ""}
              onChange={handleClasschange}
              getOptionLabel={(option) => option.class || ""}
              renderInput={(params) => <TextField {...params} style={{ width: '100%' }} label="Classification" fullWidth />}
              renderOption={(option) => {
                const val = `${option.label}`;
                return (
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
            name="classificationSubmitButton"
            disabled={!(state.class_select_enabled && state.probability_select_enabled &&
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
