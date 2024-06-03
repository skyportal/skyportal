/* eslint-disable no-unused-vars */

// Add animation on the classification select by the classification tag
function handleClassificationTag(classificationId) {
  const element = document.getElementById(classificationId);
  element.scrollIntoView({
    behavior: "smooth",
    block: "center",
    inline: "center",
  });
  if (!element.classList.contains("active")) {
    element.classList.add("active");
    setTimeout(() => {
      element.classList.remove("active");
    }, 3000);
  }
}

// Disable loader when image is loaded
function disableLoader(image) {
  image
    .closest('div[class="imageAndTitle"]')
    .getElementsByClassName("loader")[0].style.display = "none";
}

function handleImageLoad(image) {
  image.onload = null;
  disableLoader(image);
  if (image.getAttribute("data-thumbnail-type") !== "sdss") {
    image.parentElement.getElementsByClassName("crosshair")[0].style.display =
      "block";
  }
}

function handleImageError(image) {
  image.onload = null;
  image.onerror = null;
  disableLoader(image);
  if (image.getAttribute("data-thumbnail-public-url") !== "#") {
    const imgName =
      image.getAttribute("data-thumbnail-type") === "ls"
        ? "outside_survey.png"
        : "currently_unavailable.png";
    image.src = `/static/images/${imgName}`;
  }
}

const ra_to_hours = (ra, sep = null) => {
  const ra_h = String(Math.floor(ra / 15)).padStart(2, "0");
  const ra_m = String(Math.floor((ra % 15) * 4)).padStart(2, "0");
  const ra_s = String(((((ra % 15) * 4) % 1) * 60).toFixed(2)).padStart(5, "0");
  if (sep !== null) {
    return `${ra_h}${sep}${ra_m}${sep}${ra_s}`;
  }
  return `${ra_h}h${ra_m}m${ra_s}s`;
};

const dec_to_dms = (deci, sep = null, signed = true) => {
  const dec = Math.abs(deci);
  const deg = String(Math.floor(dec)).padStart(2, "0");
  const min = String(Math.floor((dec - deg) * 60)).padStart(2, "0");
  const sec = ((dec - deg - min / 60) * 3600).toFixed(2).padStart(5, "0");

  // this is for the case where the '+' sign needs to be omitted
  let sign = "";
  if (signed) {
    sign = deci < 0 ? "-" : "+";
  }

  if (!(sep == null)) {
    return `${sign}${deg}${sep}${min}${sep}${sec}`;
  }
  return `${sign}${deg}d${min}m${sec}s`;
};

const radec_hhmmss = (ra, dec) =>
  `${ra_to_hours(ra, ":")} ${dec_to_dms(dec, ":")}`;
