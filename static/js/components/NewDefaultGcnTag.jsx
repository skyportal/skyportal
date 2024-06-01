import React, { useState } from "react";
import { useDispatch } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";
import GcnNoticeTypesSelect from "./gcn/GcnNoticeTypesSelect";
import GcnTagsSelect from "./gcn/GcnTagsSelect";
import LocalizationTagsSelect from "./localization/LocalizationTagsSelect";

import * as defaultGcnTagsActions from "../ducks/default_gcn_tags";

import "react-datepicker/dist/react-datepicker-cssmodules.css";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  marginTop: {
    marginTop: "1rem",
  },
  Select: {
    width: "100%",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "100%",
    marginBottom: "1rem",
  },
}));

const NewDefaultGcnTag = () => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const [selectedGcnNoticeTypes, setSelectedGcnNoticeTypes] = useState([]);
  const [selectedGcnTags, setSelectedGcnTags] = useState([]);
  const [selectedLocalizationTags, setSelectedLocalizationTags] = useState([]);

  const handleSubmit = async ({ formData }) => {
    const { default_tag_name } = formData;
    delete formData.default_tag_name;
    const filters = {
      notice_types: selectedGcnNoticeTypes,
      gcn_tags: selectedGcnTags,
      localization_tags: selectedLocalizationTags,
    };
    const json = {
      filters,
      default_tag_name,
    };

    dispatch(defaultGcnTagsActions.submitDefaultGcnTag(json)).then(
      (response) => {
        if (response.status === "success") {
          dispatch(showNotification("Successfully created default gcn tag"));
        }
      },
    );
  };

  const defaultGcnTagFormSchema = {
    type: "object",
    properties: {
      default_tag_name: {
        type: "string",
        title: "Default tag name",
      },
    },
    required: ["default_tag_name"],
  };

  return (
    <div className={classes.container}>
      <Typography variant="h6">Add a New Default GcnTag</Typography>
      <GcnNoticeTypesSelect
        selectedGcnNoticeTypes={selectedGcnNoticeTypes}
        setSelectedGcnNoticeTypes={setSelectedGcnNoticeTypes}
      />
      <GcnTagsSelect
        selectedGcnTags={selectedGcnTags}
        setSelectedGcnTags={setSelectedGcnTags}
      />
      <LocalizationTagsSelect
        selectedLocalizationTags={selectedLocalizationTags}
        setSelectedLocalizationTags={setSelectedLocalizationTags}
      />
      <div data-testid="observationplan-request-form">
        <div>
          <Form
            schema={defaultGcnTagFormSchema}
            validator={validator}
            onSubmit={handleSubmit}
          />
        </div>
      </div>
    </div>
  );
};

export default NewDefaultGcnTag;
