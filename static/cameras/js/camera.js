document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector(".camera-detail");
  if (!root) return;

  const locationSlug = root.dataset.locationSlug;
  const slug = root.dataset.cameraSlug;
  const strip = document.getElementById("strip");
  const loadingEl = document.getElementById("strip-loading");
  const sentinel = document.getElementById("strip-sentinel");
  const mainImg = document.getElementById("main-image");
  const mainTs = document.getElementById("main-timestamp");

  let loading = false;
  let hasMore = true;

  function swapMain(thumb) {
    if (!mainImg || !mainTs) return;
    mainImg.src = thumb.dataset.full;
    mainTs.textContent = thumb.dataset.time;
    mainTs.dataset.takenAt = thumb.dataset.takenAt;
    // "Stale" describes the live feed, not a deliberately picked history frame.
    mainTs.classList.remove("stale");
  }

  strip.addEventListener("click", (e) => {
    const thumb = e.target.closest(".thumb");
    if (thumb) swapMain(thumb);
  });

  // Let a vertical mouse wheel scroll the horizontal strip.
  strip.addEventListener("wheel", (e) => {
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX) && strip.scrollWidth > strip.clientWidth) {
      strip.scrollLeft += e.deltaY;
      e.preventDefault();
    }
  }, { passive: false });

  function makeThumb(img) {
    const fig = document.createElement("figure");
    fig.className = "thumb";
    fig.dataset.id = img.id;
    fig.dataset.takenAt = img.taken_at;
    fig.dataset.time = img.time;
    fig.dataset.full = img.url;

    const el = document.createElement("img");
    el.src = img.thumb_url;
    el.loading = "lazy";
    el.alt = "";

    const cap = document.createElement("figcaption");
    cap.textContent = img.time;

    fig.append(el, cap);
    return fig;
  }

  function sentinelVisible() {
    const s = sentinel.getBoundingClientRect();
    const r = strip.getBoundingClientRect();
    return s.left < r.right + 200;
  }

  async function loadMore() {
    if (loading || !hasMore) return;
    loading = true;
    loadingEl.hidden = false;

    const thumbs = strip.querySelectorAll(".thumb");
    const lastId = thumbs.length ? thumbs[thumbs.length - 1].dataset.id : "";

    try {
      const resp = await fetch(`/${locationSlug}/${slug}/images/?before_id=${lastId}`);
      const data = await resp.json();
      data.images.forEach((img) => strip.insertBefore(makeThumb(img), loadingEl));
      hasMore = data.has_more;
    } catch (err) {
      console.error("Failed to load more images", err);
      return;
    } finally {
      loading = false;
      loadingEl.hidden = true;
    }

    // The observer only fires on visibility *changes*, so if the strip still
    // doesn't reach past the viewport (wide screens), keep filling it.
    if (hasMore && sentinelVisible()) loadMore();
  }

  new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) loadMore();
    },
    { root: strip, rootMargin: "0px 200px 0px 0px" }
  ).observe(sentinel);
});
