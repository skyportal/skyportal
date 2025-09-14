import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import makeStyles from "@mui/styles/makeStyles";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import DialogTitle from "@mui/material/DialogTitle";
import * as profileActions from "../../../ducks/profile";

const useStyles = makeStyles(() => ({
  tooltip: {
    fontSize: "1rem",
    maxWidth: "30rem",
  },
}));

const CustomizeOpenAIParameters = () => {
  const dispatch = useDispatch();
  const [aiopen, setAIOpen] = useState(false);
  const classes = useStyles();

  const site_openai_summary_parameters = useSelector(
    (state) => state.config.openai_summary_parameters,
  );
  const user_openai_summary_parameters = useSelector(
    (state) => state.profile.preferences.summary.OpenAI,
  );

  const default_openai_summary_parameters = {
    ...site_openai_summary_parameters,
    ...user_openai_summary_parameters,
  };

  const handleAIClickOpen = () => {
    setAIOpen(true);
  };

  const handleAIClose = () => {
    setAIOpen(false);
  };

  const handleAISubmit = ({ formData }) => {
    const prefs = {
      summary: {
        OpenAI: {
          active: user_openai_summary_parameters.active,
          ...formData,
        },
      },
    };
    dispatch(profileActions.updateUserPreferences(prefs));
    handleAIClose();
  };

  const formSchema = {
    type: "object",
    properties: {
      model: {
        type: "string",
        title: "model",
        examples: [
          "gpt-4",
          "gpt-3.5-turbo",
          "text-davinci-003",
          "davinci",
          "gpt-4-32k",
        ],
      },
      prompt: {
        type: "string",
        title: "prompt",
      },
      temperature: {
        type: "number",
        title: "Temperature",
        minimum: 0.0,
        maximum: 1.0,
        multipleOf: 0.05,
      },
      max_tokens: {
        type: "integer",
        title: "max_tokens",
        minimum: 10,
        maximum: 1000,
        multipleOf: 10,
      },
      top_p: {
        type: "number",
        title: "top_p",
        minimum: 0.0,
        maximum: 1.0,
        multipleOf: 0.05,
      },
      frequency_penalty: {
        type: "number",
        title: "frequency_penalty",
        minimum: -2.0,
        maximum: 2.0,
        multipleOf: 0.05,
      },
      presence_penalty: {
        type: "number",
        title: "presence_penalty",
        minimum: -2.0,
        maximum: 2.0,
        multipleOf: 0.05,
      },
    },
    required: [
      "temperature",
      "max_tokens",
      "top_p",
      "frequency_penalty",
      "model",
      "presence_penalty",
      "prompt",
    ],
  };

  const uiSchema = {
    temperature: {
      "ui:widget": "updown",
      "ui:help":
        "What sampling temperature to use, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.",
    },
    top_p: {
      "ui:widget": "updown",
      "ui:help":
        "An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered.",
    },
    prompt: {
      "ui:widget": "textarea",
    },
    max_tokens: {
      "ui:widget": "range",
      "ui:help":
        "The maximum number of tokens to generate in the summary. For reference, 100 tokens is about 75 words. Must be between 10 and 1000.",
    },
    frequency_penalty: {
      "ui:widget": "updown",
      "ui:help":
        "Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim.",
    },
    presence_penalty: {
      "ui:widget": "updown",
      "ui:help":
        "Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics.",
    },
  };
  Object.keys(formSchema.properties).forEach((key) => {
    formSchema.properties[key].default = default_openai_summary_parameters[key];
  });

  const validate = (formData, errors) => {
    if (formData.temperature < 0.0 || formData.temperature > 1.0) {
      errors.temperature.addError("Temperature must be between 0.0 and 1.0");
    }

    if (formData.max_tokens < 10 || formData.max_tokens > 1000) {
      errors.max_tokens.addError("max_tokens must be between 10 and 1000");
    }

    if (formData.top_p < 0.0 || formData.top_p > 1.0) {
      errors.top_p.addError("top_p must be between 0.0 and 1.0");
    }
    if (formData.frequency_penalty < -2.0 || formData.frequency_penalty > 2.0) {
      errors.frequency_penalty.addError(
        "frequency_penalty must be between -2 and 2",
      );
    }
    if (
      !(formData.model.includes("gpt") || formData.model.includes("davinci"))
    ) {
      errors.model.addError(
        "must be an Open AI gpt model. See https://platform.openai.com/docs/models/overview for more information.",
      );
    }
    if (formData.presence_penalty < -2.0 || formData.presence_penalty > 2.0) {
      errors.presence_penalty.addError(
        "presence_penalty must be between -2 and 2",
      );
    }

    if (formData.prompt.length < 10) {
      errors.prompt.addError("prompt must be at least 10 characters long");
    }

    return errors;
  };

  return (
    <div>
      <Tooltip
        title="Expert mode: click here to edit the OpenAI summary settings."
        placement="right"
        classes={{ tooltip: classes.tooltip }}
      >
        <IconButton
          primary
          size="small"
          type="submit"
          onClick={handleAIClickOpen}
          data-testid="UpdateOpenAI"
        >
          <EditOutlinedIcon />
        </IconButton>
      </Tooltip>
      <Dialog open={aiopen} onClose={handleAIClose}>
        <DialogTitle>Edit OpenAI Summary Settings</DialogTitle>
        <DialogContent>
          <Form
            schema={formSchema}
            validator={validator}
            uiSchema={uiSchema}
            data-testid="UpdateOpenAIform"
            onSubmit={handleAISubmit}
            customValidate={validate}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CustomizeOpenAIParameters;
