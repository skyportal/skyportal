import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";

import TextField from "@mui/material/TextField";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Switch from "@mui/material/Switch";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import InputLabel from "@mui/material/InputLabel";
import Grid from "@mui/material/Grid";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";

import * as ProfileActions from "../ducks/profile";
import * as userNotificationsActions from "../ducks/userNotifications";

import UIPreferences from "./UIPreferences";
import NotificationPreferences from "./NotificationPreferences";
import SlackPreferences from "./SlackPreferences";
import OpenAIPreferences from "./OpenAIPreferences";
import ObservabilityPreferences from "./ObservabilityPreferences";
import FollowupRequestPreferences from "./followup_request/FollowupRequestPreferences";
import PhotometryPlottingPreferences from "./photometry/PhotometryPlottingPreferences";
import SpectroscopyPlottingPreferences from "./SpectroscopyPlottingPreferences";
import ClassificationsShortcutForm from "./classification/ClassificationsShortcutForm";
import QuickSaveSourcePreferences from "./QuickSaveSourcePreferences";

const useStyles = makeStyles(() => ({
  spacing: {
    paddingBottom: 0,
  },
}));

const UpdateProfileForm = () => {
  const classes = useStyles();
  const profile = useSelector((state) => state.profile);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmittingEmailTest, setIsSubmittingEmailTest] = useState(false);
  const [isSubmittingSMSTest, setIsSubmittingSMSTest] = useState(false);

  const dispatch = useDispatch();
  const {
    handleSubmit,
    register,
    reset,
    control,

    formState: { errors },
  } = useForm();

  const isNewUser =
    new URL(window.location).searchParams.get("newUser") === "true";

  const [welcomeDialogOpen, setWelcomeDialogOpen] = useState(isNewUser);

  const filter = createFilterOptions();

  useEffect(() => {
    reset({
      username: profile.username,
      firstName: profile.first_name,
      lastName: profile.last_name,
      affiliations: profile.affiliations,
      email: profile.contact_email,
      phone: profile.contact_phone,
      bio: profile.bio,
      is_bot: profile.is_bot,
    });
  }, [reset, profile]);

  const onSubmit = async (initialValues) => {
    setIsSubmitting(true);
    const basicinfo = {
      username: initialValues.username,
      first_name: initialValues.firstName,
      last_name: initialValues.lastName,
      affiliations: initialValues.affiliations,
      contact_email: initialValues.email,
      contact_phone: initialValues.phone,
      bio: initialValues.bio,
      is_bot: initialValues.is_bot,
    };
    const result = await dispatch(
      ProfileActions.updateBasicUserInfo(basicinfo),
    );
    if (result.status === "success") {
      dispatch(showNotification("Profile data saved"));
    }
    setIsSubmitting(false);
  };

  const handleEmailTest = async () => {
    setIsSubmittingEmailTest(true);
    const data = { notification_type: "email" };
    await dispatch(userNotificationsActions.testNotifications(data));
    setIsSubmittingEmailTest(false);
  };

  const handleSMSTest = async () => {
    setIsSubmittingSMSTest(true);
    const data = { notification_type: "SMS" };
    await dispatch(userNotificationsActions.testNotifications(data));
    setIsSubmittingSMSTest(false);
  };

  return (
    <div>
      <Card>
        <CardContent>
          <h2>Username</h2>
          <form onSubmit={handleSubmit(onSubmit)}>
            <InputLabel htmlFor="usernameInput">
              Username (normalized upon save)
            </InputLabel>
            <Grid
              container
              direction="row"
              justifyContent="flex-start"
              alignItems="baseline"
              spacing={2}
            >
              <Grid item xs={12} lg={3}>
                <TextField
                  {...register("username", { required: true })}
                  name="username"
                  id="usernameInput"
                  error={!!errors.username}
                  helperText={errors.username ? "Required" : ""}
                  style={{ width: "100%" }}
                />
              </Grid>
            </Grid>
            <h2>Contact Information</h2>
            <Grid
              container
              direction="row"
              justifyContent="flex-start"
              alignItems="baseline"
              spacing={2}
            >
              <Grid item xs={6} lg={3}>
                <InputLabel htmlFor="firstName_id">First Name</InputLabel>
                <TextField
                  {...register("firstName", { required: true })}
                  name="firstName"
                  id="firstName_id"
                  error={!!errors.firstName}
                  helperText={errors.firstName ? "Required" : ""}
                  style={{ width: "100%" }}
                />
              </Grid>
              <Grid item xs={6} lg={3}>
                <InputLabel htmlFor="lastName_id">Last Name</InputLabel>
                <TextField
                  {...register("lastName", { required: false })}
                  name="lastName"
                  id="lastName_id"
                  style={{ width: "100%" }}
                />
              </Grid>
            </Grid>
            <br />
            <Grid
              container
              direction="row"
              justifyContent="flex-start"
              alignItems="baseline"
              spacing={2}
            >
              <Grid item xs={12} lg={6}>
                <InputLabel htmlFor="bio_id">
                  Bio (min 10, max 1000 chars)
                </InputLabel>
                <TextField
                  {...register("bio", { required: false })}
                  name="bio"
                  id="bio_id"
                  multiline
                  style={{ width: "100%" }}
                  inputProps={{ maxLength: 1000 }}
                />
              </Grid>
            </Grid>
            <br />
            {profile?.affiliations && (
              <Grid
                container
                direction="row"
                justifyContent="flex-start"
                alignItems="baseline"
                spacing={2}
              >
                <Grid item xs={12} lg={6}>
                  <InputLabel htmlFor="affiliationsInput">
                    Affiliations
                  </InputLabel>
                  <Controller
                    name="affiliations"
                    render={({ field: { onChange, value } }) => (
                      <Autocomplete
                        multiple
                        onChange={(e, data) => onChange(data)}
                        value={value}
                        options={profile?.affiliations?.map((aff) => aff)}
                        filterOptions={(options, params) => {
                          const filtered = filter(options, params);

                          const { inputValue } = params;
                          // Suggest the creation of a new value
                          const isExisting = options.some(
                            (option) => inputValue === option,
                          );
                          if (inputValue !== "" && !isExisting) {
                            filtered.push(inputValue);
                          }

                          return filtered;
                        }}
                        getOptionLabel={(option) => {
                          // Value selected with enter, right from the input
                          if (typeof option === "string") {
                            return option;
                          }
                          // Add "xxx" option created dynamically
                          if (option?.inputValue) {
                            return option?.inputValue;
                          }
                          return option;
                        }}
                        freeSolo
                        renderInput={(params) => (
                          <TextField
                            // eslint-disable-next-line react/jsx-props-no-spreading
                            {...params}
                            variant="outlined"
                            name="affiliations"
                            id="affilations_id"
                          />
                        )}
                      />
                    )}
                    control={control}
                    error={!!errors.affiliations}
                    defaultValue={profile?.affiliations}
                  />
                </Grid>
              </Grid>
            )}
            <br />
            <Grid
              container
              direction="row"
              justifyContent="flex-start"
              alignItems="baseline"
              spacing={2}
            >
              <Grid item xs={12} lg={6}>
                <InputLabel htmlFor="email_id">
                  Preferred Contact Email
                </InputLabel>
                <div style={{ display: "flex", width: "100%" }}>
                  <TextField
                    {...register("email", { pattern: /^\S+@\S+$/i })}
                    name="email"
                    type="email"
                    fullWidth
                    id="email_id"
                  />
                  <Button
                    secondary
                    style={{ marginLeft: "0.5rem" }}
                    type="submit"
                    id="testEmailButton"
                    onClick={handleEmailTest}
                    disabled={isSubmittingEmailTest}
                  >
                    Test
                  </Button>
                </div>
              </Grid>
            </Grid>
            <br />
            <Grid
              container
              direction="row"
              justifyContent="flex-start"
              alignItems="baseline"
              spacing={2}
            >
              <Grid item xs={12} lg={6}>
                <InputLabel htmlFor="phone_id">
                  Contact Phone (Include Country Code)
                </InputLabel>
                <div style={{ display: "flex", width: "100%" }}>
                  <TextField
                    {...register("phone", { maxLength: 16 })}
                    name="phone"
                    type="tel"
                    id="phone_id"
                    style={{ width: "100%" }}
                  />
                  <Button
                    secondary
                    style={{ marginLeft: "0.5rem" }}
                    type="submit"
                    id="testSMSButton"
                    onClick={handleSMSTest}
                    disabled={isSubmittingSMSTest}
                  >
                    Test
                  </Button>
                </div>
              </Grid>
            </Grid>
            <br />
            <Accordion>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="advancedOptions-content"
                id="advancedOptions"
              >
                <Typography variant="h6">Advanced Options</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid
                  container
                  direction="row"
                  justifyContent="flex-start"
                  alignItems="baseline"
                  spacing={2}
                >
                  <Grid item xs={12} lg={6}>
                    <InputLabel htmlFor="is_bot_id">
                      Is this a bot account (used only from the API)?
                    </InputLabel>
                    <Controller
                      name="is_bot"
                      render={({ field: { onChange, value } }) => (
                        <Switch
                          checked={value}
                          onChange={(e) => onChange(e.target.checked)}
                          color="primary"
                          inputProps={{ "aria-label": "primary checkbox" }}
                        />
                      )}
                      control={control}
                      defaultValue={profile?.is_bot}
                    />
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>
            <br />
            <Button
              primary
              type="submit"
              id="updateProfileButton"
              disabled={isSubmitting}
            >
              Update Profile
            </Button>
          </form>
        </CardContent>
        <CardContent>
          <NotificationPreferences />
        </CardContent>
        <CardContent>
          <SlackPreferences />
        </CardContent>
        <CardContent>
          <OpenAIPreferences />
        </CardContent>
        <CardContent>
          <UIPreferences />
        </CardContent>
        <CardContent>
          <ObservabilityPreferences />
        </CardContent>
        <CardContent>
          <FollowupRequestPreferences />
        </CardContent>
        <CardContent className={classes.spacing}>
          <ClassificationsShortcutForm />
        </CardContent>
        <CardContent>
          <PhotometryPlottingPreferences />
        </CardContent>
        <CardContent>
          <SpectroscopyPlottingPreferences />
        </CardContent>
        <CardContent>
          <QuickSaveSourcePreferences />
        </CardContent>
      </Card>
      <Dialog
        open={welcomeDialogOpen}
        onClose={() => {
          setWelcomeDialogOpen(false);
        }}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">Welcome!</DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            First, please change your username as you see fit. You can also
            change your contact email address to something other than the one
            you used to authenticate. If you have a gravatar (
            <a href="https://en.gravatar.com/">https://en.gravatar.com/</a>)
            account set up for your contact email address then we&apos;ll use
            that gravatar picture throughout. Once you&apos;re done setting up
            your profile info, click Dashboard to get started.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setWelcomeDialogOpen(false);
            }}
          >
            Got it. Let&apos;s go!
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default UpdateProfileForm;
