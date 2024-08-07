// Filter releases based on the search bar value
function filterReleases() {
  const searchValue = document
    .getElementById("search-bar")
    .value.trim()
    .toLowerCase();
  const releases = document.getElementsByClassName("release");
  const includeDescription =
    document.getElementById("includeDescription").checked;

  Array.from(releases).forEach((release) => {
    const releaseName = release.getElementsByClassName("releaseName")[0];
    const releaseDescription =
      release.getElementsByClassName("releaseDescription")[0];
    if (
      releaseName.textContent.toLowerCase().includes(searchValue) ||
      (includeDescription &&
        releaseDescription.textContent.toLowerCase().includes(searchValue))
    ) {
      // Mark the search value in the source name
      const re = new RegExp(searchValue, "gi");
      releaseName.innerHTML = releaseName.textContent.replace(
        re,
        (match) => `<mark>${match}</mark>`,
      );
      releaseDescription.innerHTML = releaseDescription.textContent.replace(
        re,
        (match) => (includeDescription ? `<mark>${match}</mark>` : match),
      );
      release.style.display = "";
    } else {
      release.style.display = "none";
    }
  });
}
