import { useState } from "react";
import { asNumber } from "@rjsf/utils";

// rjsf-core's stock NumberField re-formats numeric values using the OS/browser
// locale's decimal separator (e.g. "." -> ",") before writing them back into
// the input. Native <input type="number"> elements always require "."
// regardless of locale, so on comma-locale systems the browser rejects the
// reformatted value ("The specified value "2,8" cannot be parsed") and the
// field renders blank. This is the same field, minus that reformatting step.
const numberTrailingCharMatcherWithPrefix = /\.([0-9]*0)*$/;
const numberTrailingCharMatcher = /[0.]0*$/;

const LocaleSafeNumberField = (props: any) => {
  const { formData, onChange, registry } = props;
  const [lastValue, setLastValue] = useState(formData);
  const { StringField } = registry.fields;

  let value = formData;
  if (typeof lastValue === "string" && typeof value === "number") {
    const escapedValue = String(value).replace(".", "\\.");
    const re = new RegExp(`^(${escapedValue})?\\.?0*$`);
    if (lastValue.match(re)) {
      value = lastValue;
    }
  }

  const handleChange = (
    newValue: any,
    path: any,
    errorSchema: any,
    id: any,
  ) => {
    setLastValue(newValue);
    const normalizedValue =
      typeof newValue === "string" && newValue.startsWith(".")
        ? `0${newValue}`
        : newValue;
    const processed =
      typeof normalizedValue === "string" &&
      numberTrailingCharMatcherWithPrefix.exec(normalizedValue)
        ? asNumber(normalizedValue.replace(numberTrailingCharMatcher, ""))
        : asNumber(normalizedValue);
    onChange(processed, path, errorSchema, id);
  };

  return <StringField {...props} formData={value} onChange={handleChange} />;
};

export default LocaleSafeNumberField;

// Stable reference: a new object literal on every render would make rjsf
// rebuild its registry on every keystroke, resetting fields' local state
// (e.g. this field's in-progress-decimal cache), which erases values like
// "2.5" while typing. Import this directly rather than constructing
// `{ NumberField: LocaleSafeNumberField }` inline in a component body.
export const localeSafeFields = { NumberField: LocaleSafeNumberField };
