// Add animation on the classification select by the classification tag
/* eslint-disable no-unused-vars */
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

/* eslint-disable no-unused-vars */
function handleImageLoad(image) {
  image.onload = null;
  disableLoader(image);
  if (image.getAttribute("data-thumbnail-type") !== "sdss") {
    image.parentElement.getElementsByClassName("crosshair")[0].style.display =
      "block";
  }
}

/* eslint-disable no-unused-vars */
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
