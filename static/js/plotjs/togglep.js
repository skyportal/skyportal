/* eslint-disable */
for (let i = 0; i < toggle.labels.length; i++) {
  eval(`folda${i}`).visible = toggle.active.includes(i);
  eval(`foldb${i}`).visible = toggle.active.includes(i);
  eval(`foldaerr${i}`).visible = toggle.active.includes(i);
  eval(`foldberr${i}`).visible = toggle.active.includes(i);
}
