import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import { useDispatch } from 'react-redux';

import TextField from '@material-ui/core/TextField';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import Typography from '@material-ui/core/Typography';

import InputLabel from '@material-ui/core/InputLabel';
import Grid from '@material-ui/core/Grid';

import { useForm } from "react-hook-form";

import * as ProfileActions from '../ducks/profile';

import UIPreferences from './UIPreferences';

const UpdateProfileForm = ({ profile }) => {
  const dispatch = useDispatch();

  const { handleSubmit, register, reset } = useForm({
  });

  useEffect(() => {
    reset({
      firstName: profile.first_name,
      lastName: profile.last_name,
      email: profile.contact_email ? profile.contact_email : profile.username,
      phone: profile.contact_phone
    });
  }, [reset, profile]);

  const onSubmit = async (value) => {
    const data = {
      first_name: value.firstName,
      last_name: value.lastName,
      contact_email: value.email,
      contact_phone: value.phone,
    };

    await dispatch(ProfileActions.updateUserPreferences(data));
  };

  return (
    <div>
      <Typography variant="h5">
        Change User Profile
      </Typography>

      <Card>
        <CardContent>
          <h2>Contact Information</h2>
          <form onSubmit={handleSubmit(onSubmit)}>
            <Grid
              container
              direction="row"
              justify="flex-start"
              alignItems="baseline"
              spacing={2}
            >
              <Grid item xs={6} sm={3}>
                <InputLabel htmlFor="firstName_id">First Name</InputLabel>
                <TextField
                  inputRef={register}
                  name="firstName"
                  id="firstName_id"
                />
              </Grid>
              <Grid item xs={6} sm={3}>
                <InputLabel htmlFor="lastName_id">Last Name</InputLabel>
                <TextField
                  inputRef={register}
                  name="lastName"
                  id="lastName_id"
                />
              </Grid>
            </Grid>
            <br />
            <Grid
              container
              direction="row"
              justify="flex-start"
              alignItems="baseline"
              spacing={2}
            >
              <Grid item xs={6} sm={3}>
                <InputLabel htmlFor="email_id">Preferred Contact Email</InputLabel>
                <TextField
                  inputRef={register}
                  name="email"
                  type="email"
                  id="email_id"
                />
              </Grid>
            </Grid>
            <br />
            <Grid
              container
              direction="row"
              justify="flex-start"
              alignItems="baseline"
              spacing={2}
            >
              <Grid item xs={6} sm={3}>
                <InputLabel htmlFor="phone_id">Contact Phone (Cell)</InputLabel>
                <TextField
                  inputRef={register}
                  name="phone"
                  type="tel"
                  id="phone_id"
                />
              </Grid>
            </Grid>
            <br />
            <Button
              variant="contained"
              type="submit"
            >
              Update Profile
            </Button>
          </form>
        </CardContent>
        <CardContent>
          <UIPreferences />
        </CardContent>
      </Card>

    </div>


  );
};
UpdateProfileForm.propTypes = {
  profile: PropTypes.objectOf(PropTypes.object()).isRequired
};

export default UpdateProfileForm;
