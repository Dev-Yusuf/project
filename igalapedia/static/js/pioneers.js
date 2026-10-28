// Keep the initial visible if a portrait is missing or cannot be delivered.
document.querySelectorAll('.person-portrait img').forEach(image => {
    const fallback = () => { image.hidden = true; };
    image.addEventListener('error', fallback);
    if (image.complete && !image.naturalWidth) fallback();
});
