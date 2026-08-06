document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector(".camera-detail");
  if (!root) return;

  const locationSlug = root.dataset.locationSlug;
  const slug = root.dataset.cameraSlug;
  const strip = document.getElementById("strip");
  const loadingEl = document.getElementById("strip-loading");
  const mainImg = document.getElementById("main-image");
  const mainTs = document.getElementById("main-timestamp");

  let loading = false;
  let hasMore = true;

  function swapMain(thumb) {
    if (!mainImg || !mainTs) return;
    mainImg.src = thumb.dataset.full;
    mainTs.textContent = new Date(thumb.dataset.takenAt).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    mainTs.dataset.takenAt = thumb.dataset.takenAt;
    mainTs.classList.toggle("stale", thumb.classList.contains("stale"));
  }

  strip.addEventListener("click", (e) => {
    const thumb = e.target.closest(".thumb");
    if (thumb) swapMain(thumb);
  });

  async function loadMore() {
    if (loading || !hasMore) return;
    loading = true;
    loadingEl.hidden = false;

    const thumbs = strip.querySelectorAll(".thumb");
    const lastId = thumbs.length ? thumbs[thumbs.length - 1].dataset.id : "";

    try {
      const resp = await fetch(`/${locationSlug}/${slug}/images/?before_id=${lastId}`);
      const data = await resp.json();

      data.images.forEach((img) => {
        const el = document.createElement("img");
        el.className = "thumb" + (img.stale ? " stale" : "");
        el.src = img.url;
        el.dataset.id = img.id;
        el.dataset.takenAt = img.taken_at;
        el.dataset.full = img.url;
        strip.insertBefore(el, loadingEl);
      });

      hasMore = data.has_more;
    } finally {
      loading = false;
      loadingEl.hidden = true;
    }
  }

  strip.addEventListener("scroll", () => {
    const nearEnd = strip.scrollLeft + strip.clientWidth >= strip.scrollWidth - 200;
    if (nearEnd) loadMore();
  });
});
