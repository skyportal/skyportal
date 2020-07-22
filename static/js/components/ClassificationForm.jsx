import React, { useState, useEffect, useReducer } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import PropTypes from 'prop-types';
import { useForm, Controller } from 'react-hook-form';
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import TextField from '@material-ui/core/TextField';
import Button from '@material-ui/core/Button';
import FormControl from "@material-ui/core/FormControl";
import MenuItem from "@material-ui/core/MenuItem";
import { makeStyles } from "@material-ui/core/styles";
import Autocomplete, { createFilterOptions } from '@material-ui/lab/Autocomplete';
import * as Actions from '../ducks/source';



function makeMenuItem(taxonomy, index) {

  const render_string = `[${index} ${taxonomy.id}] ${taxonomy.name} ${taxonomy.version} (${taxonomy.created_at})`;

  return (
    <MenuItem value={index} key={index.toString()}>
      {render_string}
    </MenuItem>
  );
}


const ClassificationForm = ({ obj_id, taxonomyList }) => {

  function reducer(state, action) {
      switch (action.name) {
        case 'taxonomy_index':
          return {
            ...state,
            [action.name]: action.value,
            allowed_classes: taxonomyList[action.value].allowed_classes,
          };
        case 'classification':
          return {
            ...state,
            [action.name]: state.allowed_classes[action.value],
          };
        default:
          return {
            ...state,
            [action.name]: action.value
          };
      }
  }

  const ddd = useDispatch();

  const initialState = {
    taxonomy_index: taxonomyList.length > 0 ? 0 : null,
    classification: "",
    probability: null,
    allowed_classes: taxonomyList.length > 0 ? taxonomyList[0].allowed_classes : []
  }
  const [state, dispatch] = useReducer(reducer, initialState);
  const { handleSubmit, getValues, reset, register, control } = useForm();

  const useStyles = makeStyles((theme) => ({
    formControl: {
      margin: theme.spacing(1),
      minWidth: 120
    }
  }));
  const classes = useStyles();

  if (taxonomyList.length === 0) {
    return (
      <b>
        No taxonomies loaded...
      </b>
    );
  }

  const handleChange = (event) => {
    console.log(event.target.value);
    console.log(taxonomyList[event.target.value].allowed_classes);
    dispatch({name: "taxonomy_index", value: event.target.value});
  };

  const handleClasschange = (event) => {
    console.log(event.target.value);
    dispatch({name: "classification", value: event.target.value});
  };

  const onSubmit = () => {
    const formData = {
      taxonomy_id: state.taxonomy_id,
      obj_id: obj_id,
      classification: state.classification,
      probability: state.probability
    };
    // We need to include this field in request, but it isn't in form data
    dispatch(Actions.addClassification(formData));
    // reset(initialFormState);
  };


  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div>
        <h3>Add Classification</h3>
          <FormControl className={classes.formControl}>
            <Select
            defaultValue=""
            onChange={handleChange}
             >
              {taxonomyList.map((taxonomy, index) => makeMenuItem(
                taxonomy, index
              ))}
            </Select>
          </FormControl>
          <Autocomplete
          options={state.allowed_classes}
          loadingText='loading...'
          noOptionsText='Select a taxonomy'
          id="classification"
          value={state.classification}
          onChange={handleClasschange}
          renderInput={params => (
            <TextField
              {...params}
              variant="standard"
              label="Classification"
              placeholder="Classification"
              margin="normal"
              fullWidth
            />
          )}
        />
          <Button type="submit" name="classificationSubmitButton" variant="contained">
            Submit
          </Button>
        </div>
      </form>
    </div>
  );
};

const top100Films = [
  { title: 'The Shawshank Redemption', year: 1994 },
  { title: 'The Godfather', year: 1972 },
  { title: 'The Godfather: Part II', year: 1974 },
  { title: 'The Dark Knight', year: 2008 },
  { title: '12 Angry Men', year: 1957 },
  { title: "Schindler's List", year: 1993 },
  { title: 'Pulp Fiction', year: 1994 },
  { title: 'The Lord of the Rings: The Return of the King', year: 2003 },
  { title: 'The Good, the Bad and the Ugly', year: 1966 },
  { title: 'Fight Club', year: 1999 },
  { title: 'The Lord of the Rings: The Fellowship of the Ring', year: 2001 },
  { title: 'Star Wars: Episode V - The Empire Strikes Back', year: 1980 },
  { title: 'Forrest Gump', year: 1994 },
  { title: 'Inception', year: 2010 },
];

ClassificationForm.propTypes = {
  taxonomyList: PropTypes.arrayOf(PropTypes.shape({
    name: PropTypes.string,
    created_at: PropTypes.string,
    isLatest: PropTypes.bool,
    version: PropTypes.string,
  })).isRequired
};

export default ClassificationForm;
