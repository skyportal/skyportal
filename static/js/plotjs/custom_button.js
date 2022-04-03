/* eslint-disable */
const makeErrorMessage = (msg) => {
  let p = document.createElement("p");
  p.innerHTML = msg;
  p.style = "color: red;";
  document
    .getElementsByClassName(`custom_buttons_${panel_name}`)[0]
    .insertAdjacentElement("beforeend", p);
  setTimeout(() => {
    p.remove();
  }, 5000);
};
if (checkboxes.active.length != 0 && name.value_input !== "") {
  let btn = document.createElement("button");
  btn.className = "bk bk-btn bk-btn-default";
  btn.type = "button";
  btn.style = "width: fit-content";
  btn.innerHTML = `Add ${name.value_input} only`;
  let div = document.createElement("div");
  div.className = "bk bk-btn-group";
  div.appendChild(btn);
  let div2 = document.createElement("div");
  div2.className = "bk";
  div2.style = "display: block; width: fit-content;";
  div2.appendChild(div);
  document
    .getElementsByClassName(`custom_buttons_${panel_name}`)[0]
    .appendChild(div2);
  const labels = checkboxes.active.map((c) => checkboxes.labels[c]);
  btn.onclick = () => {
    for (const [key, value] of Object.entries(model_dict)) {
      const [label, extra] = key.split("~");
      if (labels.includes(label)) {
        value.visible = true;
      } else {
        value.visible = false;
      }
    }
  };
} else if (checkboxes.active.length === 0) {
  makeErrorMessage("Error: please select at least one filter.");
} else {
  makeErrorMessage("Error: please enter a name for the filter group.");
}
