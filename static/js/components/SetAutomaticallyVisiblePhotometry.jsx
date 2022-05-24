import { makeStyles } from '@material-ui/core';
import React from 'react';
import { useForm, Controller } from "react-hook-form";
import FilterSelect from './FilterSelect';
import OriginSelect from './OriginSelect';
import UserPreferencesHeader from './UserPreferencesHeader';

const useStyles = makeStyles(() => ({
  form: {
    marginBottom: '1rem'
  }
}))

const SetAutomaticallyVisiblePhotometry = () => {
  const classes = useStyles()
  const { handleSubmit, register, control, errors, reset } = useForm()
  const onSubmit = () => console.log('hi')
  return(
    <div>
      <UserPreferencesHeader title="Set Automatically Visible Photometry" popupText='Select filters and origins which you would like to automatically be visible on the photometry plot. All other photometry points will be hidden, unless the plot does not contain your selected filters/origins.'/>
      <form onSubmit={handleSubmit(onSubmit)} className={classes.form}>
        <FilterSelect control={control} />
        <OriginSelect control={control} />
      </form>
    </div>
  )
};

export default SetAutomaticallyVisiblePhotometry;