// Preserve readable initials if a contributor photo is unavailable.
document.querySelectorAll('[data-avatar-image]').forEach((image) => {
    const hideUnavailableImage = () => { image.hidden = true; };
    image.addEventListener('error', hideUnavailableImage);
    if (image.complete && image.naturalWidth === 0) hideUnavailableImage();
});
