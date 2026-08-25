import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { Link as RouterLink } from "react-router-dom";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import {
  useGetProfileQuery,
  useUpdateBasicUserInfoMutation,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useTestNotificationsMutation } from "../../ducks/userNotifications";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import EditIcon from "@mui/icons-material/Edit";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";

import UserAvatar, { isAllKoreanCharacters } from "./UserAvatar";
import ThemeToggle from "./preferences/ThemeToggle";
import Button from "../Button";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";

dayjs.extend(utc);

const filter = createFilterOptions<any>();

const AVATAR_SIZE = 128;
const FIELDS_WIDTH = "30rem";
const CARD_FIELDS_WIDTH = `calc(${AVATAR_SIZE}px + 16px + ${FIELDS_WIDTH})`;

const PUBLIC_FIELDS: Record<string, boolean> = {
  affiliations: true,
  bio: true,
  contact_email: false,
  contact_phone: false,
  roles: false,
  groups: false,
};

export const getUserRealName = (firstName: any, lastName: any) => {
  // Korean names are generally written in last->first name order with no space in between
  if (
    isAllKoreanCharacters(firstName || "") &&
    isAllKoreanCharacters(lastName || "")
  ) {
    return `${lastName}${firstName}`;
  }
  return [firstName, lastName].filter(Boolean).join(" ");
};

const UserProfileInfo = () => {
  const profile = useGetProfileQuery().data as any;
  const groups = useGetGroupsQuery().data?.user;
  const dispatch = useAppDispatch();
  const [updateBasicUserInfo] = useUpdateBasicUserInfoMutation();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const [testNotifications] = useTestNotificationsMutation();
  const [editing, setEditing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [welcomeDialogOpen, setWelcomeDialogOpen] = useState(
    new URL(window.location as any).searchParams.get("newUser") === "true",
  );
  const {
    handleSubmit,
    register,
    reset,
    control,
    formState: { errors },
  } = useForm();

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

  if (!profile) return <div data-testid="tour-profile-info" />;

  const groupNames = (groups ?? [])
    .filter((group) => !group["single_user_group"])
    .map((group) => group.name)
    .sort();

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
      setEditing(false);
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

  const field = (label: any, value: any) => (
    <Typography variant="body2">
      <b>{label}:</b> {value}
    </Typography>
  );

  const chips = (values: string[]) => (
    <Box
      component="span"
      sx={{ display: "inline-flex", flexWrap: "wrap", gap: 0.5 }}
    >
      {values.map((value) => (
        <Chip key={value} label={value} size="small" />
      ))}
    </Box>
  );

  const alwaysShowPublicIcons =
    profile.preferences?.alwaysShowPublicIcons ?? true;

  const publicEye = (key: string) => {
    const shared =
      profile.preferences?.publicProfile?.[key] ?? PUBLIC_FIELDS[key];
    return (
      <Tooltip
        placement="right"
        title={
          shared
            ? "Shown on your public profile"
            : "Hidden from your public profile"
        }
      >
        <IconButton
          size="small"
          aria-label={`Toggle ${key} on public profile`}
          data-testid={`public-toggle-${key}`}
          onClick={() =>
            updateUserPreferences({ publicProfile: { [key]: !shared } })
          }
          sx={{ p: 0, color: "text.secondary" }}
        >
          {shared ? (
            <VisibilityIcon fontSize="small" />
          ) : (
            <VisibilityOffIcon fontSize="small" />
          )}
        </IconButton>
      </Tooltip>
    );
  };

  const publicRow = (key: string, node: any) =>
    editing ? (
      node
    ) : (
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          width: "fit-content",
          gap: 0.5,
          ...(!alwaysShowPublicIcons && {
            "& .MuiIconButton-root": { opacity: 0 },
            "&:hover .MuiIconButton-root": { opacity: 1 },
            "@media (hover: none)": {
              "& .MuiIconButton-root": { opacity: 1 },
            },
          }),
        }}
      >
        {node}
        {publicEye(key)}
      </Box>
    );

  const helpIcon = (title: string) => (
    <Tooltip title={title}>
      <HelpOutlineOutlinedIcon
        fontSize="small"
        sx={{ verticalAlign: "text-bottom", mx: 0.3 }}
      />
    </Tooltip>
  );

  const input = (
    name: string,
    label: string,
    id: string,
    rules?: any,
    props?: any,
    test?: { type: string; id: string },
  ) => (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        width: "100%",
        minWidth: 0,
      }}
    >
      <TextField
        {...register(name, rules)}
        name={name}
        id={id}
        label={label}
        size="small"
        fullWidth
        sx={{ maxWidth: CARD_FIELDS_WIDTH }}
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
    </Box>
  );

  return (
    <Card data-testid="tour-profile-info">
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              alignItems: "center",
              gap: 2,
            }}
          >
            <UserAvatar
              size={AVATAR_SIZE}
              firstName={profile.first_name}
              lastName={profile.last_name}
              username={profile.username}
              gravatarUrl={profile.gravatar_url}
              isBot={profile?.is_bot || false}
            />
            {editing ? (
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 1.5,
                  flexGrow: 1,
                  width: "100%",
                  maxWidth: FIELDS_WIDTH,
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: { xs: "column", sm: "row" },
                    gap: 1.5,
                  }}
                >
                  {input("firstName", "First name", "firstName_id", {
                    required: true,
                  })}
                  {input("lastName", "Last name", "lastName_id")}
                </Box>
                {input(
                  "username",
                  "Username (normalized upon save)",
                  "usernameInput",
                  { required: true },
                )}
                <Controller
                  name="affiliations"
                  control={control}
                  defaultValue={profile.affiliations ?? []}
                  render={({ field: { onChange, value } }) => (
                    <Autocomplete
                      multiple
                      freeSolo
                      size="small"
                      onChange={(_e, data) => onChange(data)}
                      value={value ?? []}
                      options={profile.affiliations ?? []}
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
                          label="Affiliations"
                        />
                      )}
                    />
                  )}
                />
              </Box>
            ) : (
              <div>
                <Typography variant="h5" id="userRealname">
                  {getUserRealName(profile.first_name, profile.last_name)}
                </Typography>
                <Typography variant="subtitle1" color="textSecondary">
                  @{profile.username}
                </Typography>
                {!!profile.affiliations?.length &&
                  publicRow(
                    "affiliations",
                    <Typography variant="body2" id="userAffiliations">
                      <em>{profile.affiliations.join(", ")}</em>
                    </Typography>,
                  )}
              </div>
            )}
            <Box
              sx={{
                order: { xs: -1, sm: 0 },
                ml: { sm: "auto" },
                alignSelf: { xs: "flex-end", sm: "flex-start" },
              }}
            >
              <ThemeToggle />
            </Box>
          </Box>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mt: 2 }}>
            {editing
              ? input(
                  "bio",
                  "Bio (min 10, max 1000 chars)",
                  "bio_id",
                  undefined,
                  {
                    multiline: true,
                    slotProps: { htmlInput: { maxLength: 1000 } },
                  },
                )
              : profile.bio &&
                publicRow(
                  "bio",
                  <Typography variant="body2" color="textSecondary">
                    {profile.bio}
                  </Typography>,
                )}
            {editing
              ? input(
                  "email",
                  "Preferred contact email",
                  "email_id",
                  { pattern: /^\S+@\S+$/i },
                  { type: "email" },
                  { type: "email", id: "testEmailButton" },
                )
              : profile.contact_email &&
                publicRow(
                  "contact_email",
                  field(
                    "Contact email",
                    <Link href={`mailto:${profile.contact_email}`}>
                      {profile.contact_email}
                    </Link>,
                  ),
                )}
            {editing
              ? input(
                  "phone",
                  "Contact phone (include country code)",
                  "phone_id",
                  { maxLength: 16 },
                  { type: "tel" },
                  { type: "SMS", id: "testSMSButton" },
                )
              : profile.contact_phone &&
                publicRow(
                  "contact_phone",
                  field("Contact phone", profile.contact_phone),
                )}
            {!!profile.roles?.length &&
              publicRow("roles", field("Roles", chips(profile.roles)))}
            {!!groupNames.length &&
              publicRow("groups", field("Groups", chips(groupNames)))}
            {field(
              "Member since",
              dayjs.utc(`${profile.created_at}Z`).format("MMMM D, YYYY"),
            )}
            {!!profile.acls?.length &&
              field(
                <>
                  Additional user ACLs
                  {helpIcon("Separate from role-level ACLs")}
                </>,
                chips(profile.acls),
              )}
            {profile.oauth_uid &&
              field(
                <>
                  Authentication email
                  {helpIcon(
                    "This is the email address used to log in. Unlike the contact_email shown to other users, this cannot be edited. If you wish to change this, please contact a system administrator.",
                  )}
                </>,
                profile.oauth_uid,
              )}
            {editing && (
              <Controller
                name="is_bot"
                control={control}
                defaultValue={profile.is_bot}
                render={({ field: { onChange, value } }) => (
                  <FormControlLabel
                    label="Is this a bot account (used only from the API)?"
                    slotProps={{ typography: { variant: "body2" } }}
                    control={
                      <Switch
                        id="is_bot_id"
                        size="small"
                        checked={!!value}
                        onChange={(e) => onChange(e.target.checked)}
                      />
                    }
                  />
                )}
              />
            )}
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              {editing ? (
                <>
                  <Button
                    primary
                    type="submit"
                    id="updateProfileButton"
                    disabled={isSubmitting}
                  >
                    Save
                  </Button>
                  <Button
                    secondary
                    onClick={() => {
                      reset();
                      setEditing(false);
                    }}
                  >
                    Cancel
                  </Button>
                </>
              ) : (
                <Button
                  secondary
                  endIcon={<EditIcon fontSize="small" />}
                  onClick={() => setEditing(true)}
                  id="editProfileButton"
                  data-testid="tour-profile-details"
                >
                  Edit
                </Button>
              )}
              <Button
                secondary
                component={RouterLink}
                to={`/user/${profile.id}`}
                data-testid="profile-public-view"
                endIcon={<OpenInNewIcon fontSize="small" />}
              >
                View public profile
              </Button>
              {!editing && (
                <FormControlLabel
                  label="Always show visibility icons"
                  sx={{
                    ml: "auto",
                    mr: 0,
                    "@media (hover: none)": { display: "none" },
                  }}
                  slotProps={{ typography: { variant: "body2" } }}
                  control={
                    <Switch
                      size="small"
                      checked={alwaysShowPublicIcons}
                      onChange={(e) =>
                        updateUserPreferences({
                          alwaysShowPublicIcons: e.target.checked,
                        })
                      }
                    />
                  }
                />
              )}
            </Box>
          </Box>
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

export default UserProfileInfo;
