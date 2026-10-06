document.addEventListener("DOMContentLoaded", () => {
  const strip = document.getElementById("strip");
  if (!strip) return;

  const mainImg = document.getElementById("main-image");
  const mainTs = document.getElementById("main-timestamp");

  function swapMain(thumb) {
    if (!mainImg || !mainTs) return;
    mainImg.src = thumb.dataset.full;
    mainTs.textContent = thumb.dataset.time;
    mainTs.dataset.takenAt = thumb.dataset.takenAt;
    // "Stale" describes the live feed, not a deliberately picked history frame.
    mainTs.classList.remove("stale");
    // The grid can run well below the fold; bring the swapped image into view.
    mainImg.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  strip.addEventListener("click", (e) => {
    const thumb = e.target.closest(".thumb");
    if (thumb) swapMain(thumb);
  });
});
