
/* eslint-disable */
const prefs = {
  photometryDataPointSize: spinner.value,
}
fetch('/api/internal/profile', {
  method: 'PATCH',
  body: JSON.stringify({
    preferences: prefs,
  }),
  headers: {
    'Content-Type': 'application/json',
  },
})
