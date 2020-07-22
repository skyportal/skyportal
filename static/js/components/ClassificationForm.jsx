import React, { useState, useEffect } from 'react';
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


function makeMenuItem(taxonomy) {

  const render_string = `[${taxonomy.id}] ${taxonomy.name} ${taxonomy.version} (${taxonomy.created_at})`;

  return (
    <MenuItem value={taxonomy.id} key={taxonomy.name.toString()}>
      {render_string}
    </MenuItem>
  );
}


const ClassificationForm = ({ obj_id, taxonomyList }) => {
  const dispatch = useDispatch();

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

  const initialFormState = {
    taxonomy_id: taxonomyList.length > 0 ? taxonomyList[0].id : null,
    obj_id: obj_id,
    classification: "Ia",
    probability: null

  };

  const onSubmit = () => {
    const formData = {
      // Need to add obj_id, etc to form data for request
      ...initialFormState,
      ...getValues({ nest: true })
    };
    // We need to include this field in request, but it isn't in form data
    dispatch(Actions.addClassification(formData));
    reset(initialFormState);
  };

  return (
    <div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div>
          <FormControl className={classes.formControl}>
            <InputLabel id="taxonomySelectLabel">
              Choose Taxonomy
            </InputLabel>
            <Controller
              as={Select}
              labelId="taxonomySelectLabel"
              name="taxonomy_id"
              control={control}
              rules={{ required: true }}
              defaultValue={taxonomyList.length > 0 ? taxonomyList[0].id : null}
            >
              {taxonomyList.map((taxonomy) => makeMenuItem(
                taxonomy
              ))}
            </Controller>
          </FormControl>
          <Button type="submit" name="classificationSubmitButton" variant="contained">
            Submit
          </Button>
        </div>
      </form>
    </div>
  );
};

ClassificationForm.propTypes = {
  taxonomyList: PropTypes.arrayOf(PropTypes.shape({
    name: PropTypes.string,
    created_at: PropTypes.string,
    isLatest: PropTypes.bool,
    version: PropTypes.string,
  })).isRequired
};

export default ClassificationForm;
