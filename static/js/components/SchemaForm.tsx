import { useState } from "react";
import { withTheme } from "@rjsf/core";
import { Theme as MuiTheme } from "@rjsf/mui";
import type { FieldProps } from "@rjsf/utils";

/** The number this text means, accepting either decimal separator. */
const toNumber = (text: string): number | undefined => {
  const trimmed = String(text ?? "").trim();
  if (trimmed === "") {
    return undefined;
  }
  // A comma is the decimal separator on a French keyboard; treat it as one only
  // when no period is already doing that job.
  const normalized = trimmed.includes(".")
    ? trimmed
    : trimmed.replace(",", ".");
  const value = Number(normalized);
  return Number.isNaN(value) ? undefined : value;
};

/**
 * Numeric input that keeps the characters the user typed.
 *
 * rjsf's own NumberField renders `<input type="number">` and reads the decimal
 * separator from the browser locale. The two disagree: the element validates
 * against the locale the browser UI runs in, so under a French locale a typed
 * "." leaves the element's value behind while rjsf reads a longer number, and
 * the controlled value written back empties the field mid-entry. Holding the
 * raw text and converting it here keeps both separators working whatever the
 * locale.
 */
export function NumberField(props: FieldProps) {
  const { formData, onChange, registry, uiSchema } = props;
  const StringField = registry.fields["StringField"] as any;
  const [typed, setTyped] = useState<string | undefined>(undefined);

  const handleChange = (next: any, ...rest: any[]) => {
    const text = next === undefined || next === null ? "" : String(next);
    setTyped(text);
    (onChange as any)(toNumber(text), ...rest);
  };

  // Show the typed text while it still describes the committed value, so a
  // trailing separator or a lone minus survives the round trip; a value set
  // from elsewhere replaces it.
  const display =
    typed !== undefined && toNumber(typed) === formData ? typed : formData;

  return (
    <StringField
      {...props}
      formData={display}
      onChange={handleChange}
      uiSchema={{
        ...uiSchema,
        "ui:options": {
          ...(uiSchema?.["ui:options"] as object),
          // A text input never discards an entry that is still being typed.
          inputType: "text",
          inputMode: "decimal",
        },
      }}
    />
  );
}

/** rjsf's MUI form, with the numeric input that survives a non-English locale. */
const SchemaForm = withTheme({
  ...MuiTheme,
  fields: { ...MuiTheme.fields, NumberField },
});

export default SchemaForm;
