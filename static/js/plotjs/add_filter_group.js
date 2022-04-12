/* eslint-disable */
const makeErrorMessage = (msg) => {
  let p = document.createElement("p");
  p.innerHTML = msg;
  p.style = "color: red;";
  document.getElementsByClassName(`error_${panel_name}`)[0].appendChild(p);
  setTimeout(() => {
    p.remove();
  }, 5000);
};
if (
  (multichoice_filter.value.length != 0 ||
    multichoice_origin.value.length != 0) &&
  name.value_input !== ""
) {
  if (!("custom_filter_groups" in preferences)) {
    preferences["custom_filter_groups"] = {};
  }
  if (name.value_input in preferences["custom_filter_groups"]) {
    makeErrorMessage("Filter group with that name already exists.");
  } else {
    preferences["custom_filter_groups"][name.value_input] =
      multichoice_filter.value;
    const temp = multichoice_origin.value;
    preferences["custom_filter_groups"][name.value_input] =
      preferences["custom_filter_groups"][name.value_input].concat(temp);
    fetch("/api/internal/profile", {
      method: "PATCH",
      body: JSON.stringify({
        preferences: preferences,
      }),
      headers: {
        "Content-type": "application/json; charset=UTF-8",
      },
    }).then(() => location.reload());
  }
} else if (
  multichoice_filter.value.length === 0 &&
  multichoice_origin.value.length === 0
) {
  makeErrorMessage("Error: please select at least one filter.");
} else {
  makeErrorMessage("Error: please enter a name for the filter group.");
}
