import { useState } from "react";
import { asNumber } from "@rjsf/utils";

// rjsf's NumberField minus its locale reformatting ("2,8"), rejected by type=number inputs.
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

// Keep stable: an inline object rebuilds rjsf's registry and erases "2.5" mid-typing.
export const localeSafeFields = { NumberField: LocaleSafeNumberField };
