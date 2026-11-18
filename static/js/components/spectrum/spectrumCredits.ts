import SearchableSelectWidget from "../SearchableSelectWidget";

export interface UserEnumOptions {
  enum: number[];
  enumNames: string[];
}

const usersField = (title: string, userIds: number[], required = true) => ({
  type: "array",
  title,
  items: {
    type: "integer",
    enum: userIds,
  },
  uniqueItems: true,
  ...(required && { minItems: 1 }),
});

const creditDependency = (
  mode: string,
  field: string,
  contactField: string,
  title: string,
  contactTitle: string,
  userIds: number[],
) => [
  {
    properties: {
      [mode]: { enum: ["User"] },
      [field]: usersField(title, userIds),
    },
    required: [mode, field],
  },
  {
    properties: {
      [mode]: { enum: ["External"] },
      [field]: { type: "string", title },
      [contactField]: usersField(contactTitle, userIds, false),
    },
    required: [mode, field, contactField],
  },
];

export const spectrumCreditsSchema = (
  userIds: number[],
  formData: any,
  roboticObserver: string,
) => ({
  properties: {
    observer_mode: {
      type: "string",
      default: "User",
      title: "Observer type",
      enum: ["User", "External", "Robotic"],
      ...(formData?.observer_mode === "Robotic" && {
        description: `Credited as ${roboticObserver}`,
      }),
    },
    reducer_mode: {
      type: "string",
      default: "User",
      title: "Reducer type",
      enum: ["User", "External"],
    },
    pi_mode: {
      type: "string",
      default: "User",
      title: "PI type",
      enum: ["User", "External"],
    },
    auto_report_to_tns: {
      type: "boolean",
      title: "Report its classification to TNS automatically",
      default: false,
    },
  },
  dependencies: {
    pi_mode: {
      oneOf: creditDependency(
        "pi_mode",
        "pi",
        "pi_point_of_contact",
        "PI(s)",
        "Point of contact user for PI(s)",
        userIds,
      ),
    },
    reducer_mode: {
      oneOf: creditDependency(
        "reducer_mode",
        "reduced_by",
        "reducer_point_of_contact",
        "Reducers",
        "Point of contact user for reducers",
        userIds,
      ),
    },
    observer_mode: {
      oneOf: [
        ...creditDependency(
          "observer_mode",
          "observed_by",
          "observer_point_of_contact",
          "Observers",
          "Point of contact user for observers",
          userIds,
        ),
        {
          properties: {
            observer_mode: { enum: ["Robotic"] },
          },
          required: ["observer_mode"],
        },
      ],
    },
  },
});

export const spectrumCreditsUiSchema = (
  formData: any,
  userEnumNames: string[],
) => {
  const userSelect = {
    "ui:widget": SearchableSelectWidget,
    "ui:enumNames": userEnumNames,
  };
  const userSelectUnlessExternal = (mode: string) =>
    formData?.[mode] === "External" ? {} : userSelect;
  return {
    observed_by: userSelectUnlessExternal("observer_mode"),
    observer_point_of_contact: userSelect,
    reduced_by: userSelectUnlessExternal("reducer_mode"),
    reducer_point_of_contact: userSelect,
    pi: userSelectUnlessExternal("pi_mode"),
    pi_point_of_contact: userSelect,
  };
};

export const spectrumCreditsOrder = [
  "observer_mode",
  "observer_point_of_contact",
  "observed_by",
  "reducer_mode",
  "reducer_point_of_contact",
  "reduced_by",
  "pi_mode",
  "pi_point_of_contact",
  "pi",
  "auto_report_to_tns",
];

export const spectrumCreditsPayload = (
  formData: any,
  roboticObserver: string,
  roboticContactId: number | undefined,
) => ({
  ...{
    User: {
      observed_by: formData.observed_by,
      external_observer: null,
    },
    External: {
      observed_by: formData.observer_point_of_contact,
      external_observer: formData.observed_by,
    },
    Robotic: {
      observed_by: [roboticContactId],
      external_observer: roboticObserver,
    },
  }[(formData?.observer_mode ?? "User") as "User" | "External" | "Robotic"],
  reduced_by:
    formData?.reducer_mode === "User"
      ? formData.reduced_by
      : formData.reducer_point_of_contact,
  external_reducer:
    formData?.reducer_mode === "External" ? formData.reduced_by : null,
  pi: formData?.pi_mode === "User" ? formData.pi : formData.pi_point_of_contact,
  external_pi: formData?.pi_mode === "External" ? formData.pi : null,
  auto_report_to_tns: Boolean(formData.auto_report_to_tns),
});

const creditFormData = (
  mode: string,
  field: string,
  contactField: string,
  users: any[] | undefined,
  external: string | null | undefined,
) => {
  const ids = (users ?? []).map((user: any) => user.id);
  return external
    ? { [mode]: "External", [field]: external, [contactField]: ids }
    : { [mode]: "User", [field]: ids };
};

export const spectrumCreditsFormData = (
  spectrum: any,
  roboticObserver: string,
) => ({
  ...(spectrum.external_observer &&
  spectrum.external_observer === roboticObserver
    ? { observer_mode: "Robotic" }
    : creditFormData(
        "observer_mode",
        "observed_by",
        "observer_point_of_contact",
        spectrum.observers,
        spectrum.external_observer,
      )),
  ...creditFormData(
    "reducer_mode",
    "reduced_by",
    "reducer_point_of_contact",
    spectrum.reducers,
    spectrum.external_reducer,
  ),
  ...creditFormData(
    "pi_mode",
    "pi",
    "pi_point_of_contact",
    spectrum.pis,
    spectrum.external_pi,
  ),
  auto_report_to_tns: Boolean(spectrum.auto_report_to_tns),
});
