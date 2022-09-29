import React from "react";
import { useDispatch } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/material-ui/v5";

import * as profileActions from "../ducks/profile";

const UserAvatarUpload = () => {
  const dispatch = useDispatch();
  const handleSubmit = async ({ formData }) => {
    const prefs = {
      avatar: formData.avatar,
    };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const profileFormSchema = {
    type: "object",
    properties: {
      avatar: {
        type: "string",
        format: "data-url",
        title: "Profile picture",
        description: "Profile picture",
      },
    },
    required: ["avatar"],
  };

  return <Form schema={profileFormSchema} onSubmit={handleSubmit} />;
};

export default UserAvatarUpload;
