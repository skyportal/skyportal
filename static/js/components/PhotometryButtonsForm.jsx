import React from 'react';
import UserPreferencesHeader from './UserPreferencesHeader';
import { useForm } from "react-hook-form";
import { Button, TextField } from '@material-ui/core';
import FilterSelect from './FilterSelect';
import OriginSelect from './OriginSelect';
import { makeStyles } from '@material-ui/core/node_modules/@material-ui/styles';

const useStyles = makeStyles(() => ({
  submitButton: {
    margin: "1.5rem 0"
  }
}))

const PhotometryButtonsForm = () => {
  const classes = useStyles();
  const { handleSubmit, register, control, errors, reset } = useForm()
  const onSubmit = () => console.log('hi')
  return (
    <div>
      <UserPreferencesHeader title="Photometry Buttons" />
      <form onSubmit={handleSubmit(onSubmit)}>
        <div>
        <FilterSelect control={control}/>
        <OriginSelect control={control}/>
        <TextField
          label="Name"
          inputRef={register({
            required: true,
            validate: (value) => {
              if (filtersList.length !== 0 && originsList.length !== 0) {
                console.log(
                  "return",
                  !(
                    value in (profile?.photometryPlotting?.Filters || {}) &&
                    !(value in (profile?.photometryPlotting?.Origins || {}))
                  )
                );
                return !(
                  value in (profile?.photometryPlotting?.Filters || {}) &&
                  !(value in (profile?.photometryPlotting?.Origins || {}))
                );
              }
              return null;
            },
          })}
          name="photometryPlottingPreferencesName"
          id="photometryPlottingPreferencesNameInput"
          error={!!errors.photometryPlottingPreferencesName}
          helperText={
            errors.photometryPlottingPreferencesName
              ? "Required/Shortcut with that name already exists"
              : ""
          }
        />
        </div>
        <Button
          variant="contained"
          type="submit"
          className={classes.submitButton}
          onClick={(event) => handleClickSubmit(event)}
        >
          Submit
        </Button>
      </form>
    </div>
  )
};

export default PhotometryButtonsForm;