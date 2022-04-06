/* eslint-disable */
delete preferences["custom_filter_groups"][name];
fetch("/api/internal/profile", {
  method: "PATCH",
  body: JSON.stringify({
    preferences: preferences,
  }),
  headers: {
    "Content-type": "application/json; charset=UTF-8",
  },
}).then(() => location.reload());
