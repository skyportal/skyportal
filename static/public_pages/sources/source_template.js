function handleImageLoad(image) {
    image.onload=null;
    disableLoader(image)
    if (image.getAttribute('data-thumbnail-type') !== 'sdss') {
        image.parentElement.getElementsByClassName('crosshair')[0].style.display = 'block';
    }
}
function handleImageError(image) {
    image.onload=null;
    image.onerror=null;
    disableLoader(image)
    if(image.getAttribute('data-thumbnail-public-url') !== '#'){
        const imgName = image.getAttribute('data-thumbnail-type') === 'ls' ? 'outside_survey.png' : 'currently_unavailable.png';
        image.src = `/static/images/${imgName}`;
    }
}
function disableLoader(image) {
    image.closest('div[class="imageAndTitle"]').getElementsByClassName('loader')[0].style.display = 'none';
}

function handleClassificationTag(classificationId) {
    const element = document.getElementById(classificationId);
    element.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
        inline: 'center'
    });
    if(!element.classList.contains('active'))
    {
        element.classList.add('active');
        setTimeout(function() {
            element.classList.remove('active');
        }, 3000);
    }
}