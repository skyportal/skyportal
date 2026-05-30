import React from "react";
import { makeStyles } from "tss-react/mui";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { useAppSelector } from "../../../types/hooks";

interface IsElements {
  summary?: boolean;
  photometry?: boolean;
  spectroscopy?: boolean;
  classifications?: boolean;
  [key: string]: boolean | undefined;
}

export const sourcePublishOptionsSchema = (
  streams: { id: number; name: string }[],
  groups: { id: number; name: string }[],
  is_elements: IsElements | null | undefined,
) => {
  const schema: any = { type: "object", properties: {} };
  const includeProperty = (text: string) => ({
    type: "boolean",
    default: true,
    title: text,
  });
  const selectProperty = (
    text: string,
    items: { id: number; name: string }[],
  ): any => ({
    type: "array",
    items: {
      type: "integer",
      anyOf: items.map((item) => ({
        enum: [item.id],
        type: "integer",
        title: item.name,
      })),
    },
    uniqueItems: true,
    default: [],
    title: text,
  });
  if (is_elements == null || is_elements.summary) {
    schema.properties.include_summary = includeProperty("Include summary?");
  }
  if (is_elements == null || is_elements.photometry) {
    schema.properties.include_photometry = includeProperty(
      "Include photometry?",
    );
  }
  if (is_elements == null || is_elements.spectroscopy) {
    schema.properties.include_spectroscopy = includeProperty(
      "Include spectroscopy?",
    );
  }
  if (is_elements == null || is_elements.classifications) {
    schema.properties.include_classifications = includeProperty(
      "Include classifications?",
    );
  }
  if (streams?.length > 0 && (is_elements == null || is_elements?.photometry)) {
    schema.properties.streams = selectProperty(
      "Streams to restrict photometry from",
      streams,
    );
  }
  if (
    groups?.length > 0 &&
    (is_elements == null ||
      is_elements?.classifications ||
      is_elements?.spectroscopy ||
      is_elements?.photometry)
  ) {
    schema.properties.groups = selectProperty(
      "Groups to restrict data from",
      groups,
    );
  }
  return schema;
};

const useStyles = makeStyles()(() => ({
  sourcePublishOptions: {
    marginBottom: "1rem",
    display: "flex",
    flexDirection: "column",
    padding: "0 0.3rem",
    "& .MuiGrid-item": {
      paddingTop: "0",
    },
  },
}));

interface PublishOptions {
  include_summary?: boolean;
  include_photometry?: boolean;
  include_spectroscopy?: boolean;
  include_classifications?: boolean;
  groups?: number[];
  streams?: number[];
}

interface SourcePublishOptionsProps {
  options: PublishOptions;
  setOptions: (options: any) => void;
  isElements: IsElements;
}

const SourcePublishOptions = ({
  options,
  setOptions,
  isElements,
}: SourcePublishOptionsProps) => {
  const { classes: styles } = useStyles();
  const streams = useAppSelector((state) => state.streams);
  const groups = useAppSelector((state) => state.groups.userAccessible);

  return (
    <div className={styles.sourcePublishOptions}>
      <Form
        formData={options}
        onChange={
          (({ formData }: { formData: any }) => setOptions(formData)) as any
        }
        schema={
          sourcePublishOptionsSchema(
            streams as any,
            groups as any,
            isElements,
          ) as any
        }
        liveValidate
        validator={validator}
        uiSchema={{
          "ui:submitButtonOptions": { norender: true },
        }}
      />
    </div>
  );
};

export default SourcePublishOptions;
