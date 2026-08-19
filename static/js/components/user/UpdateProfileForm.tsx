import { ReactNode, useEffect, useState } from "react";
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
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";

import {
  useGetProfileQuery,
  useUpdateBasicUserInfoMutation,
} from "../../ducks/profile";
import { useTestNotificationsMutation } from "../../ducks/userNotifications";

const filter = createFilterOptions<any>();

const FIELDS = {
  username: {
    label: "Username (normalized upon save)",
    id: "usernameInput",
    rules: { required: true },
  },
  firstName: {
    label: "First Name",
    id: "firstName_id",
    rules: { required: true },
  },
  lastName: { label: "Last Name", id: "lastName_id" },
  bio: {
    label: "Bio (min 10, max 1000 chars)",
    id: "bio_id",
    props: { multiline: true, slotProps: { htmlInput: { maxLength: 1000 } } },
  },
  email: {
    label: "Preferred Contact Email",
    id: "email_id",
    rules: { pattern: /^\S+@\S+$/i },
    props: { type: "email" },
    test: { type: "email", id: "testEmailButton" },
  },
  phone: {
    label: "Contact Phone (Include Country Code)",
    id: "phone_id",
    rules: { maxLength: 16 },
    props: { type: "tel" },
    test: { type: "SMS", id: "testSMSButton" },
  },
} as Record<string, any>;

const UpdateProfileForm = () => {
  const { data: profile } = useGetProfileQuery();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);

  const dispatch = useAppDispatch();
  const [updateBasicUserInfo] = useUpdateBasicUserInfoMutation();
  const [testNotifications] = useTestNotificationsMutation();
  const {
    handleSubmit,
    register,
    reset,
    control,
    formState: { errors },
  } = useForm();

  const isNewUser =
    new URL(window.location as any).searchParams.get("newUser") === "true";

  const [welcomeDialogOpen, setWelcomeDialogOpen] = useState(isNewUser);

  useEffect(() => {
    reset({
      username: profile?.username,
      firstName: profile?.first_name,
      lastName: profile?.last_name,
      affiliations: profile?.affiliations,
      email: profile?.contact_email,
      phone: profile?.contact_phone,
      bio: profile?.bio,
      is_bot: profile?.is_bot,
    });
  }, [reset, profile]);

  const onSubmit = async (values: any) => {
    setIsSubmitting(true);
    try {
      await updateBasicUserInfo({
        formData: {
          username: values.username,
          first_name: values.firstName,
          last_name: values.lastName,
          affiliations: values.affiliations,
          contact_email: values.email,
          contact_phone: values.phone,
          bio: values.bio,
          is_bot: values.is_bot,
        },
      }).unwrap();
      dispatch(showNotification("Profile data saved"));
    } catch {
      // error notification handled by the API layer
    }
    setIsSubmitting(false);
  };

  const handleTest = async (notification_type: string) => {
    setTesting(notification_type);
    await testNotifications({ notification_type });
    setTesting(null);
  };

  const labelled = (id: string, label: string, children: ReactNode) => (
    <div>
      <InputLabel htmlFor={id}>{label}</InputLabel>
      {children}
    </div>
  );

  const field = (name: string) => {
    const { label, id, rules, props, test } = FIELDS[name];
    return labelled(
      id,
      label,
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <TextField
          {...register(name, rules)}
          name={name}
          id={id}
          fullWidth
          error={!!errors[name]}
          helperText={rules?.required && errors[name] ? "Required" : ""}
          {...props}
        />
        {test && (
          <Button
            secondary
            type="submit"
            id={test.id}
            onClick={() => handleTest(test.type)}
            disabled={testing === test.type}
          >
            Test
          </Button>
        )}
      </div>,
    );
  };

  return (
    <Card>
      <CardContent data-testid="tour-profile-details">
        <form
          onSubmit={handleSubmit(onSubmit)}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "1rem",
            maxWidth: "40rem",
          }}
        >
          <h2 style={{ margin: 0 }}>Username</h2>
          {field("username")}
          <h2 style={{ margin: 0 }}>Contact Information</h2>
          {field("firstName")}
          {field("lastName")}
          {field("bio")}
          {profile?.affiliations &&
            labelled(
              "affilations_id",
              "Affiliations",
              <Controller
                name="affiliations"
                control={control}
                defaultValue={profile?.affiliations}
                render={({ field: { onChange, value } }) => (
                  <Autocomplete
                    multiple
                    freeSolo
                    onChange={(_e, data) => onChange(data)}
                    value={value}
                    options={profile?.affiliations ?? []}
                    filterOptions={(options, params) => {
                      const filtered = filter(options, params);
                      // Suggest the creation of a new value
                      if (
                        params.inputValue !== "" &&
                        !options.includes(params.inputValue)
                      ) {
                        filtered.push(params.inputValue);
                      }
                      return filtered;
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        name="affiliations"
                        id="affilations_id"
                      />
                    )}
                  />
                )}
              />,
            )}
          {field("email")}
          {field("phone")}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <InputLabel htmlFor="is_bot_id">
              Is this a bot account (used only from the API)?
            </InputLabel>
            <Controller
              name="is_bot"
              control={control}
              defaultValue={profile?.is_bot}
              render={({ field: { onChange, value } }) => (
                <Switch
                  id="is_bot_id"
                  checked={value}
                  onChange={(e) => onChange(e.target.checked)}
                />
              )}
            />
          </div>
          <Button
            primary
            type="submit"
            id="updateProfileButton"
            disabled={isSubmitting}
            sx={{ alignSelf: "flex-start" }}
          >
            Update Profile
          </Button>
        </form>
      </CardContent>
      <Dialog
        open={welcomeDialogOpen}
        onClose={() => setWelcomeDialogOpen(false)}
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
          <Button onClick={() => setWelcomeDialogOpen(false)}>
            Got it. Let&apos;s go!
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default UpdateProfileForm;
