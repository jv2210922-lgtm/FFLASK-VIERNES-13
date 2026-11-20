document.addEventListener("DOMContentLoaded", () => {
  const mapElement = document.getElementById("plaza-map");
  const dataElement = document.getElementById("plaza-data");
  if (!mapElement || !dataElement || !window.L) return;

  const plazas = JSON.parse(dataElement.textContent);
  const map = L.map(mapElement, { scrollWheelZoom: false }).setView([-32.85, -68.83], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map);

  const markers = [];
  const bounds = [];
  const markerGroup = L.featureGroup().addTo(map);
  const search = document.getElementById("plaza-search");
  const statusFilter = document.getElementById("plaza-status");
  const resultCount = document.createElement("p");
  resultCount.className = "map-result-count";
  resultCount.setAttribute("aria-live", "polite");
  mapElement.before(resultCount);

  function makePopup(plaza) {
    const popup = document.createElement("article");
    popup.className = "map-popup";
    if (plaza.photo) {
      const image = document.createElement("img");
      image.src = `/static/uploads/${encodeURIComponent(plaza.photo)}`;
      image.alt = `Fotografía de ${plaza.name}`;
      image.loading = "lazy";
      popup.append(image);
    }
    const title = document.createElement("h3");
    title.textContent = plaza.name;
    popup.append(title);
    const address = document.createElement("p");
    address.textContent = plaza.address;
    popup.append(address);
    if (plaza.description) {
      const description = document.createElement("p");
      description.textContent = plaza.description;
      popup.append(description);
    }
    const reports = document.createElement("p");
    reports.className = "popup-reports";
    reports.textContent = `Reclamos: ${plaza.report_count}`;
    popup.append(reports);
    const link = document.createElement("a");
    link.className = "button button-primary button-small";
    link.href = `/reclamos?plaza=${encodeURIComponent(plaza.id)}`;
    link.textContent = "Realizar un reclamo";
    popup.append(link);
    return popup;
  }

  plazas.forEach((plaza) => {
    const marker = L.marker([plaza.latitude, plaza.longitude])
      .bindPopup(makePopup(plaza))
      .addTo(markerGroup);
    markers.push({ marker, plaza });
    bounds.push([plaza.latitude, plaza.longitude]);
  });
  if (bounds.length === 1) map.setView(bounds[0], 15);
  else if (bounds.length > 1) map.fitBounds(bounds, { padding: [32, 32] });

  function updateMarkers() {
    const query = search.value.trim().toLocaleLowerCase("es");
    const status = statusFilter.value;
    markerGroup.clearLayers();
    let visible = 0;
    markers.forEach(({ marker, plaza }) => {
      const matchesSearch = `${plaza.name} ${plaza.address}`.toLocaleLowerCase("es").includes(query);
      const counts = {
        Pendiente: plaza.pending_count,
        "En revisión": plaza.review_count,
        "En proceso": plaza.process_count,
        Solucionado: plaza.solved_count,
      };
      const matchesStatus = status === "all" ||
        (status === "none" ? Number(plaza.report_count) === 0 : Number(counts[status]) > 0);
      if (matchesSearch && matchesStatus) {
        markerGroup.addLayer(marker);
        visible += 1;
      }
    });
    resultCount.textContent = `${visible} ${visible === 1 ? "plaza encontrada" : "plazas encontradas"}`;
  }

  search.addEventListener("input", updateMarkers);
  statusFilter.addEventListener("change", updateMarkers);
  updateMarkers();
});
