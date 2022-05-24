import { TextField } from '@material-ui/core';
import React from 'react';
import UserPreferencesHeader from './UserPreferencesHeader';

const DataPointSizeForm = () => {
  return (
    <>
    <UserPreferencesHeader title="Data Point Size" popupText='Size of data points on photometry plot. Ranges from 1-60.' />
    <TextField
      label="Size"
      type="number" 
      />
    </>
  )
}

export default DataPointSizeForm;