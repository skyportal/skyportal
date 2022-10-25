/* eslint-disable */
const period_value = parseFloat(period.value);
const origin_value = origin.value;
fetch("/api/sources/objname/annotations", {
  method: "POST",
  body: JSON.stringify({
    origin: origin_value,
    data: { period: period_value },
  }),
  headers: {
    "Content-Type": "application/json",
  },
});
