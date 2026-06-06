import { useGetGroupsQuery } from "../../ducks/groups";
import { useState } from "react";
import { makeStyles } from "tss-react/mui";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import * as spectraActions from "../../ducks/spectra";
import { useGetEnumTypesQuery } from "../../ducks/enum_types";

const useStyles = makeStyles()(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

interface SyntheticPhotometryFormProps {
  spectrum_id: number;
}

const SyntheticPhotometryForm = ({
  spectrum_id,
}: SyntheticPhotometryFormProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const groups = useGetGroupsQuery().data?.userAccessible ?? [];
  const { data: enum_types } = useGetEnumTypesQuery();

  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);
  const groupIDToName: Record<number, string> = {};
  groups?.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

  const filters = [...(enum_types?.["ALLOWED_BANDPASSES"] ?? [])].sort();

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setSubmissionRequestInProcess(true);
    // Get the classification without the context
    const result: any = await dispatch(
      spectraActions.addSyntheticPhotometry(spectrum_id, formData),
    );
    setSubmissionRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("Synthetic photometry saved"));
    }
  };

  const formSchema = {
    description: "Add Synthetic Photometry",
    type: "object",
    required: ["filters"],
    properties: {
      filters: {
        type: "array",
        items: {
          type: "string",
          enum: filters,
        },
        uniqueItems: true,
        title: "Filter list",
      },
    },
  };

  return (
    <div className={classes.container}>
      <div>
        <Form
          schema={formSchema as any}
          validator={validator}
          onSubmit={handleSubmit as any}
          disabled={submissionRequestInProcess}
        />
      </div>
    </div>
  );
};

export default SyntheticPhotometryForm;
