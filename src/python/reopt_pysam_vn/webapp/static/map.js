/* Map helpers for the Vietnam DPPA web app.
 *
 * Exposes:
 *   window.initSitePicker(opts)
 *   window.initContextMap(opts)
 *
 * All map logic is vanilla JS + Leaflet loaded via CDN. If Leaflet fails to
 * load (CDN blocked), the functions return early and the underlying numeric
 * fields remain usable.
 */
(function () {
  "use strict";

  function regionForLatitude(lat) {
    if (lat >= 20.0) return "north";
    if (lat >= 14.0) return "central";
    return "south";
  }

  function formatCoord(value) {
    var n = parseFloat(value);
    if (isNaN(n)) return "";
    return n.toFixed(4);
  }

  function readCoords(latInput, lonInput) {
    var lat = parseFloat(latInput.value);
    var lon = parseFloat(lonInput.value);
    if (isNaN(lat) || isNaN(lon)) return null;
    return [lat, lon];
  }

  function setRegion(regionSelect, lat) {
    if (!regionSelect) return;
    var region = regionForLatitude(lat);
    for (var i = 0; i < regionSelect.options.length; i++) {
      if (regionSelect.options[i].value === region) {
        regionSelect.selectedIndex = i;
        break;
      }
    }
  }

  function renderProjectMarkers(map, projects) {
    projects.forEach(function (p) {
      if (!p.location || p.location.lat == null || p.location.lon == null) return;
      var color = p.technology === "wind" ? "#3388ff" : "#f0a000";
      var marker = L.circleMarker([p.location.lat, p.location.lon], {
        radius: 6,
        fillColor: color,
        color: "#fff",
        weight: 1,
        opacity: 1,
        fillOpacity: 0.85,
      }).addTo(map);
      var strike = p.indicative_strike_usc_kwh != null ? p.indicative_strike_usc_kwh + " US¢/kWh" : "";
      var lines = [
        "<strong>" + (p.name || p.project_id) + "</strong>",
        "Technology: " + (p.technology || "n/a"),
        "Capacity: " + (p.capacity_mw != null ? p.capacity_mw + " MW" : "n/a"),
        strike ? "Indicative strike: " + strike : "",
        "Status: " + (p.status || "n/a"),
      ];
      marker.bindPopup(lines.filter(Boolean).join("<br>"));
    });
  }

  function fetchProjects(url, callback) {
    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (body) {
        callback(body.projects || []);
      })
      .catch(function () {
        callback([]);
      });
  }

  window.initSitePicker = function (opts) {
    opts = opts || {};
    if (typeof L === "undefined") return;

    var latInput = document.getElementById(opts.latInputId || "site_latitude");
    var lonInput = document.getElementById(opts.lonInputId || "site_longitude");
    var regionSelect = document.getElementById(opts.regionSelectId || "site_region");
    var mapEl = document.getElementById(opts.mapElementId || "site-map");
    var searchInput = document.getElementById(opts.searchInputId || "site-search");
    var searchBtn = document.getElementById(opts.searchButtonId || "site-search-btn");
    var searchMsg = document.getElementById(opts.searchMessageId || "site-search-msg");
    var projectsUrl = opts.projectsUrl || "/api/projects";

    if (!mapEl || !latInput || !lonInput) return;

    var center = [16.0, 106.0];
    var zoom = 5;
    var initial = readCoords(latInput, lonInput);
    if (initial) {
      center = initial;
      zoom = 10;
    }

    var map = L.map(mapEl).setView(center, zoom);
    window._sitePickerMap = map;
    window._sitePickerMarker = null;
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
    }).addTo(map);

    var marker = null;
    if (initial) {
      marker = L.marker(initial, { draggable: true }).addTo(map);
      window._sitePickerMarker = marker;
      marker.on("dragend", function (e) {
        var ll = e.target.getLatLng();
        latInput.value = formatCoord(ll.lat);
        lonInput.value = formatCoord(ll.lng);
        setRegion(regionSelect, ll.lat);
      });
    }

    map.on("click", function (e) {
      var lat = e.latlng.lat;
      var lon = e.latlng.lng;
      latInput.value = formatCoord(lat);
      lonInput.value = formatCoord(lon);
      setRegion(regionSelect, lat);
      if (marker) {
        marker.setLatLng([lat, lon]);
      } else {
        marker = L.marker([lat, lon], { draggable: true }).addTo(map);
        window._sitePickerMarker = marker;
        marker.on("dragend", function (ev) {
          var ll = ev.target.getLatLng();
          latInput.value = formatCoord(ll.lat);
          lonInput.value = formatCoord(ll.lng);
          setRegion(regionSelect, ll.lat);
        });
      }
    });

    function onFieldChange() {
      var coords = readCoords(latInput, lonInput);
      if (!coords) return;
      if (marker) {
        marker.setLatLng(coords);
      } else {
        marker = L.marker(coords, { draggable: true }).addTo(map);
        window._sitePickerMarker = marker;
        marker.on("dragend", function (e) {
          var ll = e.target.getLatLng();
          latInput.value = formatCoord(ll.lat);
          lonInput.value = formatCoord(ll.lng);
          setRegion(regionSelect, ll.lat);
        });
      }
      map.panTo(coords);
    }

    latInput.addEventListener("change", onFieldChange);
    lonInput.addEventListener("change", onFieldChange);

    function doSearch() {
      if (!searchInput || !searchMsg) return;
      var q = searchInput.value.trim();
      if (!q) return;
      searchMsg.textContent = "Searching…";
      var url =
        "https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=vn&q=" +
        encodeURIComponent(q);
      fetch(url, { headers: { "Accept-Language": "en" } })
        .then(function (r) {
          if (!r.ok) throw new Error("Search service unavailable");
          return r.json();
        })
        .then(function (results) {
          if (!results || !results.length) {
            searchMsg.textContent = "No results found.";
            return;
          }
          searchMsg.textContent = "";
          var lat = parseFloat(results[0].lat);
          var lon = parseFloat(results[0].lon);
          if (isNaN(lat) || isNaN(lon)) return;
          latInput.value = formatCoord(lat);
          lonInput.value = formatCoord(lon);
          setRegion(regionSelect, lat);
          if (marker) {
            marker.setLatLng([lat, lon]);
          } else {
            marker = L.marker([lat, lon], { draggable: true }).addTo(map);
        window._sitePickerMarker = marker;
            marker.on("dragend", function (e) {
              var ll = e.target.getLatLng();
              latInput.value = formatCoord(ll.lat);
              lonInput.value = formatCoord(ll.lng);
              setRegion(regionSelect, ll.lat);
            });
          }
          map.setView([lat, lon], 12);
        })
        .catch(function (err) {
          searchMsg.textContent = err.message || "Search failed.";
        });
    }

    if (searchBtn) searchBtn.addEventListener("click", doSearch);
    if (searchInput) {
      searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          e.preventDefault();
          doSearch();
        }
      });
    }

    fetchProjects(projectsUrl, function (projects) {
      renderProjectMarkers(map, projects);
    });
  };

  window.initContextMap = function (opts) {
    opts = opts || {};
    if (typeof L === "undefined") return;
    if (opts.lat == null || opts.lon == null) return;

    var mapEl = document.getElementById(opts.mapElementId || "context-map");
    var projectsUrl = opts.projectsUrl || "/api/projects";
    if (!mapEl) return;

    var map = L.map(mapEl, {
      dragging: false,
      touchZoom: false,
      scrollWheelZoom: false,
      doubleClickZoom: false,
      boxZoom: false,
      keyboard: false,
      tap: false,
    }).setView([opts.lat, opts.lon], 6);
    window._contextMap = map;

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
    }).addTo(map);

    var bounds = L.latLngBounds([[opts.lat, opts.lon]]);
    L.marker([opts.lat, opts.lon], {
      icon: L.divIcon({
        className: "site-marker",
        html: "<span style='background:#e60000;width:14px;height:14px;display:block;border-radius:50%;border:2px solid #fff;box-shadow:0 0 4px rgba(0,0,0,0.4);'></span>",
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      }),
    }).addTo(map).bindPopup("Modeled site");

    fetchProjects(projectsUrl, function (projects) {
      projects.forEach(function (p) {
        if (!p.location || p.location.lat == null || p.location.lon == null) return;
        L.circleMarker([p.location.lat, p.location.lon], {
          radius: 5,
          fillColor: "#888",
          color: "#fff",
          weight: 1,
          opacity: 0.8,
          fillOpacity: 0.6,
        }).addTo(map);
        bounds.extend([p.location.lat, p.location.lon]);
      });
      if (projects.length) {
        map.fitBounds(bounds, { padding: [20, 20], maxZoom: 8 });
      }
    });
  };
})();
