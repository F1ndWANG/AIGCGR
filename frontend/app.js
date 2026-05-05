const DEFAULT_API_BASE_URL = "http://localhost:8000/api";

const state = {
  scenario: "auto",
  latitude: null,
  longitude: null,
  locationLabel: null,
  locationLandmarks: null,
  map: null,
  mapMarker: null,
  mapCircle: null,
  mapRadiusTooltip: null,
  requestId: null,
  preferences: null,
  userId: localStorage.getItem("liferec:userId") || "u001",
  apiBaseUrl: normalizeApiBaseUrl(localStorage.getItem("liferec:apiBaseUrl") || DEFAULT_API_BASE_URL),
};

const scenarioButtons = document.querySelectorAll(".scenario");
const apiBaseInput = document.querySelector("#apiBaseInput");
const saveApiBaseBtn = document.querySelector("#saveApiBaseBtn");
const userIdInput = document.querySelector("#userIdInput");
const switchUserBtn = document.querySelector("#switchUserBtn");
const input = document.querySelector("#messageInput");
const submitBtn = document.querySelector("#submitBtn");
const locateBtn = document.querySelector("#locateBtn");
const customLocationInput = document.querySelector("#customLocationInput");
const useCustomLocationBtn = document.querySelector("#useCustomLocationBtn");
const refreshBtn = document.querySelector("#refreshBtn");
const radiusInput = document.querySelector("#radiusInput");
const recentMealTagsInput = document.querySelector("#recentMealTagsInput");
const mealNameInput = document.querySelector("#mealNameInput");
const mealTagsInput = document.querySelector("#mealTagsInput");
const saveMealBtn = document.querySelector("#saveMealBtn");
const wellnessTagsInput = document.querySelector("#wellnessTagsInput");
const sleepHoursInput = document.querySelector("#sleepHoursInput");
const exerciseMinutesInput = document.querySelector("#exerciseMinutesInput");
const stressLevelInput = document.querySelector("#stressLevelInput");
const saveWellnessBtn = document.querySelector("#saveWellnessBtn");
const tasteInput = document.querySelector("#tasteInput");
const avoidInput = document.querySelector("#avoidInput");
const travelStyleInput = document.querySelector("#travelStyleInput");
const defaultLocationInput = document.querySelector("#defaultLocationInput");
const defaultBudgetInput = document.querySelector("#defaultBudgetInput");
const profileTasteInput = document.querySelector("#profileTasteInput");
const profileAvoidInput = document.querySelector("#profileAvoidInput");
const profileAllergiesInput = document.querySelector("#profileAllergiesInput");
const profileHealthGoalsInput = document.querySelector("#profileHealthGoalsInput");
const profileTravelStyleInput = document.querySelector("#profileTravelStyleInput");
const savePreferencesBtn = document.querySelector("#savePreferencesBtn");
const locationStatus = document.querySelector("#locationStatus");
const currentLocationMap = document.querySelector("#currentLocationMap");
const mapPlaceName = document.querySelector("#mapPlaceName");
const mapCoordinateText = document.querySelector("#mapCoordinateText");
const mapViewport = document.querySelector("#mapViewport");
const mapFallback = document.querySelector("#mapFallback");
const statusPanel = document.querySelector("#statusPanel");
const intentSummary = document.querySelector("#intentSummary");
const healthSummary = document.querySelector("#healthSummary");
const aigcSummary = document.querySelector("#aigcSummary");
const planList = document.querySelector("#planList");
const recommendationList = document.querySelector("#recommendationList");
const providerSummary = document.querySelector("#providerSummary");
const memorySummary = document.querySelector("#memorySummary");
const lifeStateSummary = document.querySelector("#lifeStateSummary");
const exportMemoryBtn = document.querySelector("#exportMemoryBtn");
const recommendationHistory = document.querySelector("#recommendationHistory");
const dailyBriefPanel = document.querySelector("#dailyBriefPanel");
const dailyBriefBtn = document.querySelector("#dailyBriefBtn");
const planSummary = document.querySelector("#planSummary");
const exportPlansBtn = document.querySelector("#exportPlansBtn");
const exportPlansIcsBtn = document.querySelector("#exportPlansIcsBtn");

apiBaseInput.value = state.apiBaseUrl;
userIdInput.value = state.userId;
loadProviderCapabilities();
loadUserContext();

scenarioButtons.forEach((button) => {
  button.addEventListener("click", () => {
    scenarioButtons.forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    state.scenario = button.dataset.scenario;
  });
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
  });
});

submitBtn.addEventListener("click", async () => {
  await requestRecommendation();
});

refreshBtn.addEventListener("click", async () => {
  await refreshRecommendation();
});

saveMealBtn.addEventListener("click", async () => {
  await saveMealLog();
});

saveApiBaseBtn.addEventListener("click", async () => {
  await saveApiBaseUrl();
});

apiBaseInput.addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    await saveApiBaseUrl();
  }
});

saveWellnessBtn.addEventListener("click", async () => {
  await saveWellnessLog();
});

exportPlansBtn.addEventListener("click", async () => {
  await exportPlans();
});

exportPlansIcsBtn.addEventListener("click", async () => {
  await exportPlansIcs();
});

exportMemoryBtn.addEventListener("click", async () => {
  await exportUserMemory();
});

dailyBriefBtn.addEventListener("click", async () => {
  await generateDailyBrief();
});

savePreferencesBtn.addEventListener("click", async () => {
  await savePreferences();
});

switchUserBtn.addEventListener("click", async () => {
  await switchUser();
});

userIdInput.addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    await switchUser();
  }
});

useCustomLocationBtn.addEventListener("click", async () => {
  await useCustomLocation();
});

customLocationInput.addEventListener("keydown", async (event) => {
  if (event.key === "Enter") {
    await useCustomLocation();
  }
});

radiusInput.addEventListener("input", () => {
  if (state.latitude !== null && state.longitude !== null) {
    updateCurrentLocationMap(state.latitude, state.longitude);
  }
});

locateBtn.addEventListener("click", () => {
  if (!navigator.geolocation) {
    locationStatus.textContent = "当前浏览器不支持定位。";
    return;
  }

  locationStatus.textContent = "正在请求浏览器位置权限...";
  navigator.geolocation.getCurrentPosition(
    (position) => {
      state.latitude = position.coords.latitude;
      state.longitude = position.coords.longitude;
      state.locationLabel = getNearbyPlaceLabel(state.latitude, state.longitude);
      state.locationLandmarks = null;
      locationStatus.textContent = `已启用动态位置：${state.latitude.toFixed(4)}, ${state.longitude.toFixed(4)}`;
      updateCurrentLocationMap(state.latitude, state.longitude);
    },
    () => {
      locationStatus.textContent = "定位未启用，继续使用示例地点。";
    },
    {
      enableHighAccuracy: false,
      timeout: 8000,
      maximumAge: 300000,
    },
  );
});

async function useCustomLocation() {
  const query = customLocationInput.value.trim();
  if (!query) {
    locationStatus.textContent = "请输入自定义位置，例如：北京海淀北京理工大学。";
    return;
  }

  useCustomLocationBtn.disabled = true;
  locationStatus.textContent = `正在识别位置：${query}...`;

  try {
    const location = await resolveLocation(query);
    state.latitude = location.latitude;
    state.longitude = location.longitude;
    state.locationLabel = location.label;
    state.locationLandmarks = location.landmarks || null;
    defaultLocationInput.value = location.label;
    locationStatus.textContent = `已启用自定义位置：${state.latitude.toFixed(4)}, ${state.longitude.toFixed(4)}`;
    updateCurrentLocationMap(state.latitude, state.longitude);
  } catch (error) {
    locationStatus.textContent = "暂时无法识别该位置，请换成更完整的地址或学校/商圈名称。";
    console.error(error);
  } finally {
    useCustomLocationBtn.disabled = false;
  }
}

async function resolveLocation(query) {
  const knownLocation = findKnownLocation(query);
  if (knownLocation) {
    return knownLocation;
  }

  const endpoint = new URL("https://nominatim.openstreetmap.org/search");
  endpoint.searchParams.set("format", "jsonv2");
  endpoint.searchParams.set("limit", "1");
  endpoint.searchParams.set("accept-language", "zh-CN");
  endpoint.searchParams.set("q", query);

  const response = await fetch(endpoint.toString());
  if (!response.ok) {
    throw new Error(`Geocoding returned ${response.status}`);
  }
  const results = await response.json();
  if (!results.length) {
    throw new Error("No geocoding result");
  }

  return {
    latitude: Number(results[0].lat),
    longitude: Number(results[0].lon),
    label: results[0].display_name || query,
    landmarks: [query, "自定义位置", "附近生活圈"],
  };
}

function findKnownLocation(query) {
  const normalized = query.replace(/\s+/g, "");
  const knownLocations = [
    {
      keywords: ["北京理工大学", "北京海淀北京理工大学", "北理工", "bit"],
      latitude: 39.9608,
      longitude: 116.3162,
      label: "北京市海淀区北京理工大学附近",
      landmarks: ["北京理工大学", "中关村南大街", "海淀生活圈"],
    },
    {
      keywords: ["西北大学图书馆", "西北大学长安校区", "西安长安西北大学"],
      latitude: 34.1455,
      longitude: 108.8695,
      label: "陕西省西安市长安区西北大学图书馆附近",
      landmarks: ["西北大学图书馆", "长安校区", "校园绿地"],
    },
  ];

  return knownLocations.find((location) =>
    location.keywords.some((keyword) => normalized.toLowerCase().includes(keyword.toLowerCase())),
  );
}

function updateCurrentLocationMap(latitude, longitude) {
  if (!currentLocationMap || !mapPlaceName || !mapCoordinateText) {
    return;
  }

  const radius = Number(radiusInput.value || 3);
  const label = state.locationLabel || getNearbyPlaceLabel(latitude, longitude);
  mapPlaceName.textContent = label;
  mapCoordinateText.textContent = `当前位置：${latitude.toFixed(4)}, ${longitude.toFixed(4)} · 推荐半径 ${radius} km`;
  renderInteractiveMap(latitude, longitude, radius, label);
  currentLocationMap.classList.remove("is-empty");
}

function renderInteractiveMap(latitude, longitude, radiusKm, label) {
  if (!mapViewport || !window.L) {
    if (mapFallback) {
      const fallbackTitle = mapFallback.querySelector("strong");
      const fallbackText = mapFallback.querySelector("span");
      if (fallbackTitle) fallbackTitle.textContent = "在线地图暂不可用";
      if (fallbackText) fallbackText.textContent = "请检查网络后刷新页面，位置坐标仍会用于推荐。";
    }
    return;
  }

  const center = [latitude, longitude];
  if (!state.map) {
    state.map = L.map(mapViewport, {
      center,
      zoom: 15,
      zoomControl: true,
      scrollWheelZoom: true,
      attributionControl: true,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      crossOrigin: true,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(state.map);
    if (mapFallback) {
      mapFallback.setAttribute("aria-hidden", "true");
      mapFallback.style.display = "none";
    }
  }

  if (!state.mapMarker) {
    const pinIcon = L.divIcon({
      className: "",
      html: '<span class="liferec-map-pin" aria-hidden="true"></span>',
      iconSize: [34, 34],
      iconAnchor: [17, 31],
    });
    state.mapMarker = L.marker(center, {
      draggable: true,
      icon: pinIcon,
      title: "拖动调整位置",
    })
      .addTo(state.map)
      .bindTooltip("你在这里", {
        permanent: true,
        direction: "right",
        offset: [16, -12],
        className: "liferec-map-tooltip",
      });
    state.mapMarker.on("dragend", () => {
      const next = state.mapMarker.getLatLng();
      state.latitude = next.lat;
      state.longitude = next.lng;
      state.locationLabel = "已微调的位置";
      state.locationLandmarks = null;
      locationStatus.textContent = `已微调位置：${next.lat.toFixed(4)}, ${next.lng.toFixed(4)}`;
      updateCurrentLocationMap(next.lat, next.lng);
    });
  }

  state.map.setView(center, state.map.getZoom() || 15, { animate: true });
  state.mapMarker.setLatLng(center);
  state.mapMarker.setTooltipContent(label === "已微调的位置" ? "已微调" : "你在这里");

  const radiusMeters = Math.max(1, radiusKm) * 1000;
  if (!state.mapCircle) {
    state.mapCircle = L.circle(center, {
      radius: radiusMeters,
      color: "#0c7c67",
      weight: 2,
      dashArray: "8 7",
      fillColor: "#0c7c67",
      fillOpacity: 0.08,
      interactive: false,
    }).addTo(state.map);
  } else {
    state.mapCircle.setLatLng(center);
    state.mapCircle.setRadius(radiusMeters);
  }

  if (!state.mapRadiusTooltip) {
    state.mapRadiusTooltip = L.tooltip({
      permanent: true,
      direction: "top",
      offset: [0, -8],
      className: "liferec-radius-label",
    }).addTo(state.map);
  }
  state.mapRadiusTooltip.setLatLng(getRadiusLabelPosition(latitude, longitude, radiusKm));
  state.mapRadiusTooltip.setContent(`${radiusKm} km`);

  setTimeout(() => state.map.invalidateSize(), 0);
}

function getRadiusLabelPosition(latitude, longitude, radiusKm) {
  const latitudeOffset = (radiusKm / 111) * 0.62;
  const longitudeOffset = (radiusKm / (111 * Math.max(Math.cos((latitude * Math.PI) / 180), 0.2))) * 0.52;
  return [latitude + latitudeOffset, longitude + longitudeOffset];
}

function getMapLandmarks(latitude, longitude, label) {
  const matched = findKnownLocation(label || "");
  if (matched?.landmarks) {
    return matched.landmarks;
  }
  const isNorthwestUniversityArea =
    Math.abs(latitude - 34.1455) < 0.08 && Math.abs(longitude - 108.8695) < 0.08;
  if (isNorthwestUniversityArea) {
    return ["西北大学图书馆", "长安校区", "校园绿地"];
  }
  return ["目标位置", "附近街区", "生活服务点"];
}

function getNearbyPlaceLabel(latitude, longitude) {
  const isNorthwestUniversityArea =
    Math.abs(latitude - 34.1455) < 0.08 && Math.abs(longitude - 108.8695) < 0.08;
  if (isNorthwestUniversityArea) {
    return "陕西省西安市长安区西北大学图书馆附近";
  }
  return "当前位置附近";
}

async function requestRecommendation() {
  const message = input.value.trim();
  if (!message) {
    setStatus("请输入生活需求。", "error");
    return;
  }

  submitBtn.disabled = true;
  setStatus("正在生成推荐方案...", "loading");

  try {
    const response = await fetch(apiUrl("/recommend"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        scenario: state.scenario,
        user_id: currentUserId(),
        latitude: state.latitude,
        longitude: state.longitude,
        radius_km: Number(radiusInput.value || 3),
        recent_meal_tags: parseList(recentMealTagsInput.value),
        location: state.locationLabel || customLocationInput.value.trim() || defaultLocationInput.value.trim() || null,
        budget: defaultBudgetInput.value ? Number(defaultBudgetInput.value) : null,
        taste: mergeLists(parseList(tasteInput.value), parseList(profileTasteInput.value)),
        avoid: mergeLists(parseList(avoidInput.value), parseList(profileAvoidInput.value)),
        allergies: mergeLists(parseList(avoidInput.value), parseList(profileAllergiesInput.value)),
        health_goals: parseList(profileHealthGoalsInput.value),
        travel_style: mergeLists(parseList(travelStyleInput.value), parseList(profileTravelStyleInput.value)),
      }),
    });

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    const data = await response.json();
    renderResult(data);
    await loadUserContext();
    setStatus("推荐已生成。", "ready");
  } catch (error) {
    setStatus("无法连接后端，请确认 FastAPI 已在 localhost:8000 启动。", "error");
    console.error(error);
  } finally {
    submitBtn.disabled = false;
  }
}

async function refreshRecommendation() {
  if (!state.requestId) {
    setStatus("请先生成一次推荐，再使用换一批。", "error");
    return;
  }

  refreshBtn.disabled = true;
  setStatus("正在排除上一批结果并重新生成...", "loading");

  try {
    const response = await fetch(apiUrl("/recommend/refresh"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: currentUserId(),
        request_id: state.requestId,
      }),
    });

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    const data = await response.json();
    renderResult(data);
    await loadUserContext();
    setStatus("已生成替代推荐。", "ready");
  } catch (error) {
    setStatus("换一批失败，可能是当前候选不足或后端未启动。", "error");
    console.error(error);
  } finally {
    refreshBtn.disabled = !state.requestId;
  }
}

async function saveMealLog() {
  const mealName = mealNameInput.value.trim();
  const tags = parseList(mealTagsInput.value);
  if (!mealName) {
    setStatus("请输入要记录的饮食名称。", "error");
    return;
  }
  if (!tags.length) {
    setStatus("请至少填写一个饮食标签，例如高油、高盐、蔬菜少。", "error");
    return;
  }

  saveMealBtn.disabled = true;
  setStatus("正在保存饮食记录...", "loading");

  try {
    const response = await fetch(apiUrl("/user/meals"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: currentUserId(),
        meal_name: mealName,
        tags,
      }),
    });

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    const data = await response.json();
    recentMealTagsInput.value = data.recent_meal_tags.join(", ");
    mealNameInput.value = "";
    mealTagsInput.value = "";
    await loadUserContext();
    setStatus("饮食记录已保存，下一次推荐会参考真实饮食历史。", "ready");
  } catch (error) {
    setStatus("饮食记录保存失败，请确认后端已启动。", "error");
    console.error(error);
  } finally {
    saveMealBtn.disabled = false;
  }
}

async function saveWellnessLog() {
  const tags = parseList(wellnessTagsInput.value);
  const sleepHours = sleepHoursInput.value ? Number(sleepHoursInput.value) : null;
  const exerciseMinutes = exerciseMinutesInput.value ? Number(exerciseMinutesInput.value) : null;
  const stressLevel = stressLevelInput.value ? Number(stressLevelInput.value) : null;
  if (!tags.length && sleepHours === null && exerciseMinutes === null && stressLevel === null) {
    setStatus("请至少填写一个生活状态标签或数值。", "error");
    return;
  }

  saveWellnessBtn.disabled = true;
  setStatus("正在保存生活状态...", "loading");

  try {
    const response = await fetch(apiUrl("/user/wellness"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: currentUserId(),
        tags,
        sleep_hours: sleepHours,
        exercise_minutes: exerciseMinutes,
        stress_level: stressLevel,
      }),
    });

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    wellnessTagsInput.value = "";
    sleepHoursInput.value = "";
    exerciseMinutesInput.value = "";
    stressLevelInput.value = "";
    await loadUserContext();
    setStatus("生活状态已保存，后续推荐会参考这些信号。", "ready");
  } catch (error) {
    setStatus("生活状态保存失败，请确认后端已启动。", "error");
    console.error(error);
  } finally {
    saveWellnessBtn.disabled = false;
  }
}

async function savePreferences() {
  savePreferencesBtn.disabled = true;
  setStatus("正在保存长期偏好...", "loading");

  try {
    const response = await fetch(apiUrl("/user/preferences"), {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: currentUserId(),
        default_location: defaultLocationInput.value.trim() || null,
        default_budget: defaultBudgetInput.value ? Number(defaultBudgetInput.value) : null,
        taste: parseList(profileTasteInput.value),
        avoid: parseList(profileAvoidInput.value),
        allergies: parseList(profileAllergiesInput.value),
        health_goals: parseList(profileHealthGoalsInput.value),
        travel_style: parseList(profileTravelStyleInput.value),
      }),
    });

    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }

    const data = await response.json();
    state.preferences = data;
    fillPreferenceInputs(data);
    await loadUserContext();
    setStatus("长期偏好已保存，后续推荐会自动使用。", "ready");
  } catch (error) {
    setStatus("长期偏好保存失败，请确认后端已启动。", "error");
    console.error(error);
  } finally {
    savePreferencesBtn.disabled = false;
  }
}

async function switchUser() {
  const nextUserId = userIdInput.value.trim() || "u001";
  state.userId = nextUserId;
  state.requestId = null;
  state.preferences = null;
  localStorage.setItem("liferec:userId", nextUserId);
  refreshBtn.disabled = true;
  clearUserScopedInputs();
  setStatus(`已切换到用户 ${nextUserId}，正在读取上下文...`, "loading");
  await loadUserContext();
  setStatus(`当前用户：${nextUserId}`, "ready");
}

async function saveApiBaseUrl() {
  const nextApiBaseUrl = normalizeApiBaseUrl(apiBaseInput.value || DEFAULT_API_BASE_URL);
  state.apiBaseUrl = nextApiBaseUrl;
  apiBaseInput.value = nextApiBaseUrl;
  localStorage.setItem("liferec:apiBaseUrl", nextApiBaseUrl);
  state.requestId = null;
  refreshBtn.disabled = true;
  setStatus(`API 地址已切换为 ${nextApiBaseUrl}，正在重新读取 Provider 状态...`, "loading");
  await loadProviderCapabilities();
  await loadUserContext();
  setStatus("API 地址已保存。", "ready");
}

function currentUserId() {
  return state.userId || "u001";
}

function apiUrl(path) {
  return `${state.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

function normalizeApiBaseUrl(value) {
  return String(value || DEFAULT_API_BASE_URL).trim().replace(/\/+$/, "");
}

function clearUserScopedInputs() {
  recentMealTagsInput.value = "";
  defaultLocationInput.value = "";
  defaultBudgetInput.value = "";
  profileTasteInput.value = "";
  profileAvoidInput.value = "";
  profileAllergiesInput.value = "";
  profileHealthGoalsInput.value = "";
  profileTravelStyleInput.value = "";
  wellnessTagsInput.value = "";
  sleepHoursInput.value = "";
  exerciseMinutesInput.value = "";
  stressLevelInput.value = "";
  planSummary.innerHTML = "<span>正在读取计划...</span>";
  memorySummary.innerHTML = "<span>正在读取用户上下文...</span>";
  lifeStateSummary.innerHTML = "<span>正在编码当前用户生活状态...</span>";
  recommendationHistory.innerHTML = "<span>正在读取推荐历史...</span>";
  dailyBriefPanel.innerHTML = "<span>点击生成，系统会读取当前用户的真实记录。</span>";
}

async function loadMealHistory() {
  try {
    const response = await fetch(apiUrl(`/user/meals?user_id=${encodeURIComponent(currentUserId())}&limit=20`));
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    const data = await response.json();
    if (data.recent_meal_tags?.length) {
      recentMealTagsInput.value = data.recent_meal_tags.join(", ");
    }
  } catch (error) {
    console.debug("Meal history unavailable", error);
  }
}

async function loadUserContext() {
  try {
    const response = await fetch(apiUrl(`/user/context?user_id=${encodeURIComponent(currentUserId())}&limit=20`));
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    const data = await response.json();
    state.preferences = data.preferences || null;
    renderUserContext(data);
    if (data.preferences) {
      fillPreferenceInputs(data.preferences);
    }
    if (data.recent_meal_tags?.length) {
      recentMealTagsInput.value = data.recent_meal_tags.join(", ");
    }
  } catch (error) {
    memorySummary.innerHTML = "<span>用户上下文暂不可用</span>";
    lifeStateSummary.innerHTML = "<span>生活状态编码暂不可用</span>";
    recommendationHistory.innerHTML = "<span>推荐历史暂不可用</span>";
    console.debug("User context unavailable", error);
    await loadMealHistory();
  }
}

function renderUserContext(data) {
  const positiveEvents = data.feedback?.events?.filter((event) => ["like", "save", "plan"].includes(event.action)).length || 0;
  const negativeEvents = data.feedback?.events?.filter((event) => ["dislike", "skip"].includes(event.action)).length || 0;
  const mealTags = data.recent_meal_tags?.length
    ? data.recent_meal_tags.slice(0, 6).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")
    : "<span>暂无饮食标签</span>";
  const wellnessTags = data.recent_wellness_tags?.length
    ? data.recent_wellness_tags.slice(0, 6).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")
    : "<span>暂无生活状态</span>";
  const preferenceCount = countPreferences(data.preferences);

  memorySummary.innerHTML = `
    <div class="memory-stats">
      <div class="memory-stat"><strong>${data.meals?.length || 0}</strong><small>饮食记录</small></div>
      <div class="memory-stat"><strong>${data.wellness?.length || 0}</strong><small>生活状态</small></div>
      <div class="memory-stat"><strong>${positiveEvents}</strong><small>正反馈</small></div>
    </div>
    <div class="memory-stats">
      <div class="memory-stat"><strong>${negativeEvents}</strong><small>负反馈</small></div>
      <div class="memory-stat"><strong>${preferenceCount}</strong><small>长期偏好</small></div>
    </div>
    <div class="profile-tags">${mealTags}</div>
    <div class="profile-tags wellness-tags">${wellnessTags}</div>
  `;
  renderLifeState(data.life_state);
  renderRecommendationHistory(data.recent_recommendations || []);
  renderPlanSummary(data.plans || []);
}

function renderLifeState(lifeState) {
  if (!lifeState) {
    lifeStateSummary.innerHTML = "<span>暂无生活状态编码</span>";
    return;
  }
  const confidence = toPercent(lifeState.confidence);
  const completeness = toPercent(lifeState.context_completeness);
  const tags = lifeState.short_term_tags?.length
    ? lifeState.short_term_tags.slice(0, 8).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")
    : "<span>暂无短期标签</span>";
  const constraints = lifeState.constraints?.length
    ? lifeState.constraints.slice(0, 6).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")
    : "<span>暂无显式约束</span>";
  const warnings = lifeState.warnings?.length
    ? lifeState.warnings.slice(0, 4).map((item) => `<span>${escapeHtml(item)}</span>`).join("")
    : "<span>context_ready</span>";
  lifeStateSummary.innerHTML = `
    <div class="life-state-metrics">
      <div><strong>${confidence}</strong><small>置信度</small></div>
      <div><strong>${completeness}</strong><small>完整度</small></div>
      <div><strong>${lifeState.active_plan_count || 0}</strong><small>计划</small></div>
      <div><strong>${lifeState.recommendation_count || 0}</strong><small>历史</small></div>
    </div>
    <div class="life-state-bar" aria-label="上下文完整度">
      <span style="width: ${completeness};"></span>
    </div>
    <div class="life-state-section">
      <small>短期信号</small>
      <div class="life-state-tags">${tags}</div>
    </div>
    <div class="life-state-section">
      <small>约束</small>
      <div class="life-state-tags">${constraints}</div>
    </div>
    <div class="life-state-section">
      <small>缺口</small>
      <div class="life-state-tags warning-tags">${warnings}</div>
    </div>
  `;
}

function renderRecommendationHistory(history) {
  if (!history.length) {
    recommendationHistory.innerHTML = "<span>暂无推荐历史</span>";
    return;
  }

  recommendationHistory.innerHTML = "";
  history.slice(0, 5).forEach((event) => {
    const itemNames = event.top_items?.length
      ? event.top_items.map((item) => escapeHtml(item.name)).join(" / ")
      : "未返回候选项";
    const card = document.createElement("article");
    card.className = "history-chip";
    card.innerHTML = `
      <div>
        <strong>${escapeHtml(formatScenarioLabel(event.scenario))}</strong>
        <small>${escapeHtml(formatPlanDateTime(event.created_at))} · ${event.item_count || 0} 个候选</small>
      </div>
      <p>${escapeHtml(trimText(event.message, 42))}</p>
      <small>Top：${itemNames}</small>
    `;
    card.addEventListener("click", () => {
      input.value = event.message;
      state.requestId = event.request_id;
      refreshBtn.disabled = false;
      setStatus(`已载入历史请求 ${event.request_id}，可直接换一批。`, "ready");
    });
    recommendationHistory.appendChild(card);
  });
}

async function generateDailyBrief() {
  dailyBriefBtn.disabled = true;
  dailyBriefPanel.innerHTML = "<span>正在生成今日简报...</span>";
  setStatus("正在基于真实用户上下文生成今日简报...", "loading");
  try {
    const response = await fetch(apiUrl(`/user/daily-brief?user_id=${encodeURIComponent(currentUserId())}&limit=20`));
    if (!response.ok) {
      throw new Error(`Daily brief API returned ${response.status}`);
    }
    const data = await response.json();
    renderDailyBrief(data);
    setStatus("今日简报已生成。", "ready");
  } catch (error) {
    dailyBriefPanel.innerHTML = "<span>今日简报生成失败，请确认后端已启动。</span>";
    setStatus("今日简报生成失败。", "error");
    console.error(error);
  } finally {
    dailyBriefBtn.disabled = false;
  }
}

function renderDailyBrief(data) {
  dailyBriefPanel.innerHTML = `
    <article class="daily-brief-card">
      <div>
        <strong>${escapeHtml(data.provider || "unknown")}</strong>
        <small>${escapeHtml(formatPlanDateTime(data.generated_at))}</small>
      </div>
      <p>${escapeHtml(data.summary || "暂无简报内容。")}</p>
      ${renderBriefLifeState(data.life_state)}
      ${renderBriefList("优先事项", data.priorities)}
      ${renderBriefList("风险信号", data.risk_flags)}
      ${renderBriefList("下一步", data.next_actions)}
    </article>
  `;
}

function renderBriefLifeState(lifeState) {
  if (!lifeState) {
    return "";
  }
  return `
    <div class="brief-life-state">
      <span>Life State ${toPercent(lifeState.confidence)} confidence</span>
      <span>${escapeHtml((lifeState.short_term_tags || []).slice(0, 3).join(" / ") || "no short-term tags")}</span>
    </div>
  `;
}

function renderBriefList(title, items) {
  if (!items?.length) {
    return "";
  }
  return `
    <div class="brief-list">
      <small>${escapeHtml(title)}</small>
      <ul>${items.slice(0, 5).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
  `;
}

function fillPreferenceInputs(preferences) {
  defaultLocationInput.value = preferences.default_location || "";
  defaultBudgetInput.value = preferences.default_budget || "";
  profileTasteInput.value = (preferences.taste || []).join(", ");
  profileAvoidInput.value = (preferences.avoid || []).join(", ");
  profileAllergiesInput.value = (preferences.allergies || []).join(", ");
  profileHealthGoalsInput.value = (preferences.health_goals || []).join(", ");
  profileTravelStyleInput.value = (preferences.travel_style || []).join(", ");
}

function renderPlanSummary(plans) {
  if (!plans.length) {
    planSummary.innerHTML = "<span>暂无计划项</span>";
    return;
  }

  planSummary.innerHTML = "";
  plans.slice(0, 8).forEach((plan) => {
    const chip = document.createElement("article");
    chip.className = "plan-chip";
    const scheduledValue = toDateTimeLocalValue(plan.scheduled_for);
    const scheduledLabel = plan.scheduled_for
      ? formatPlanDateTime(plan.scheduled_for)
      : "未设置时间，导出 ICS 时会自动顺延";
    chip.innerHTML = `
      <div>
        <strong>${escapeHtml(plan.title || plan.item_name)}</strong>
        <small>${escapeHtml(plan.item_type)} · ${escapeHtml(plan.source || "unknown")}</small>
        <small>计划时间：${escapeHtml(scheduledLabel)}</small>
      </div>
      <label class="plan-schedule">
        <span>执行时间</span>
        <input type="datetime-local" value="${escapeHtml(scheduledValue)}">
      </label>
      <div class="plan-actions">
        <button data-action="schedule">保存时间</button>
        <button data-status="done">完成</button>
        <button data-status="canceled">取消</button>
      </div>
    `;
    const scheduleInput = chip.querySelector("input[type='datetime-local']");
    const scheduleButton = chip.querySelector("[data-action='schedule']");
    scheduleButton.addEventListener("click", async () => {
      await updatePlanSchedule(plan.id, scheduleInput, scheduleButton);
    });
    chip.querySelectorAll("[data-status]").forEach((button) => {
      button.addEventListener("click", async () => {
        await updatePlanStatus(plan.id, button.dataset.status, button);
      });
    });
    planSummary.appendChild(chip);
  });
}

function renderResult(data) {
  state.requestId = data.request_id;
  refreshBtn.disabled = false;
  if (data.life_state) {
    renderLifeState(data.life_state);
  }
  intentSummary.textContent = data.intent_summary;
  healthSummary.textContent = `${data.health_summary} ${data.strategy}`;
  aigcSummary.textContent = data.aigc_summary || "未生成 AIGC 摘要。";

  planList.innerHTML = "";
  data.plan.forEach((step) => {
    const li = document.createElement("li");
    li.textContent = step;
    planList.appendChild(li);
  });

  recommendationList.classList.remove("empty-state");
  recommendationList.innerHTML = "";
  data.recommendations.forEach((item) => {
    recommendationList.appendChild(createCard(item));
  });
}

async function loadProviderCapabilities() {
  try {
    const response = await fetch(apiUrl("/providers/capabilities"));
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    const data = await response.json();
    renderProviderCapabilities(data);
  } catch (error) {
    providerSummary.innerHTML = "<span>无法读取 Provider 状态，请确认后端已启动。</span>";
  }
}

function renderProviderCapabilities(data) {
  const items = [
    ["地点", data.places?.active, data.places?.source],
    ["天气", data.weather?.active, data.weather?.source],
    ["路线", data.routes?.active, data.routes?.source],
    ["AIGC", data.aigc?.active, data.aigc?.source],
    ["商品", data.shopping?.active, data.shopping?.source],
    ["严格真实数据", data.strict_real_data?.active, data.strict_real_data?.fallback],
    ["Provider 缓存", data.provider_cache?.active, data.provider_cache?.source],
  ];
  providerSummary.innerHTML = items
    .map(([label, active, source]) => `
      <span class="${active ? "is-on" : "is-off"}">
        ${label}：${active ? "已启用" : "未启用"} · ${source || "unknown"}
      </span>
    `)
    .join("");
}

function createCard(item) {
  const card = document.createElement("article");
  card.className = "recommendation-card";

  const meta = Object.entries(item.meta || {})
    .filter(([, value]) => value !== "" && value !== null && value !== undefined)
    .map(([key, value]) => `<span>${escapeHtml(formatMetaKey(key))}：${escapeHtml(String(value))}</span>`)
    .join("");

  const tags = item.tags
    .slice(0, 6)
    .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
    .join("");

  const reasons = item.reasons
    .map((reason) => `<li>${escapeHtml(reason)}</li>`)
    .join("");

  const suggested = item.suggested_items.length
    ? `<div class="suggested">建议：${escapeHtml(item.suggested_items.join(" / "))}</div>`
    : "";
  const execution = renderExecutionScore(item.execution);
  const planSignal = renderPlanSignal(item.plan_signal);
  const realness = renderRealnessCheck(item.realness);
  const trace = renderRecommendationTrace(item.trace);

  card.innerHTML = `
    <div class="card-header">
      <div>
        <p class="eyebrow">${escapeHtml(item.type)}</p>
        <h3>${escapeHtml(item.name)}</h3>
      </div>
      <div class="score">${escapeHtml(String(item.score))}</div>
    </div>
    <div class="meta-row">${meta}</div>
    <div class="tag-row">${tags}</div>
    <ol class="reason-list">${reasons}</ol>
    ${suggested}
    ${realness}
    ${execution}
    ${planSignal}
    ${trace}
    <div class="feedback-row">
      <button data-action="like">喜欢</button>
      <button data-action="dislike">不喜欢</button>
      <button data-action="plan">加入计划</button>
    </div>
  `;

  card.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      await sendFeedback(item, button.dataset.action, button);
    });
  });

  return card;
}

function renderRealnessCheck(realness) {
  if (!realness) {
    return "";
  }
  const realnessScore = toPercent(realness.realness_score);
  const risk = toPercent(realness.hallucination_risk);
  const flags = realness.risk_flags?.length
    ? realness.risk_flags.slice(0, 5).map((item) => `<span>${escapeHtml(item)}</span>`).join("")
    : "<span>grounded</span>";
  const forbidden = realness.forbidden_claims?.length
    ? `<div class="realness-forbidden">${realness.forbidden_claims.slice(0, 4).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`
    : "";
  return `
    <div class="realness-panel">
      <div class="realness-head">
        <span>${escapeHtml(realness.label || "unknown")}</span>
        <strong>${realnessScore}</strong>
      </div>
      <div class="realness-cost-row">
        <span>幻觉风险 ${risk}</span>
        <span>${realness.passed ? "Guard passed" : "Guard blocked"}</span>
      </div>
      <div class="realness-tags">${flags}</div>
      ${forbidden}
    </div>
  `;
}

function renderPlanSignal(planSignal) {
  if (!planSignal || (!planSignal.adjustment && !planSignal.evidence?.length)) {
    return "";
  }
  const adjustment = Number(planSignal.adjustment || 0);
  const label = adjustment > 0 ? `+${adjustment.toFixed(1)}` : adjustment.toFixed(1);
  const evidence = planSignal.evidence?.length
    ? planSignal.evidence.slice(0, 5).map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : "<li>暂无计划证据</li>";
  const blockers = planSignal.blockers?.length
    ? planSignal.blockers.slice(0, 5).map((item) => `<span>${escapeHtml(item)}</span>`).join("")
    : "<span>plan_context_ready</span>";
  return `
    <div class="plan-signal-panel">
      <div class="plan-signal-head">
        <span>计划感知排序</span>
        <strong>${escapeHtml(label)}</strong>
      </div>
      <div class="plan-signal-tags">${blockers}</div>
      <ol class="plan-signal-evidence">${evidence}</ol>
    </div>
  `;
}

function renderExecutionScore(execution) {
  if (!execution) {
    return "";
  }
  const score = toPercent(execution.executable_score);
  const cost = toPercent(execution.execution_cost);
  const blockers = execution.blockers?.length
    ? execution.blockers.slice(0, 5).map((item) => `<span>${escapeHtml(item)}</span>`).join("")
    : "<span>no_major_blocker</span>";
  const evidence = execution.evidence?.length
    ? execution.evidence.slice(0, 5).map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : "<li>暂无执行证据</li>";
  return `
    <div class="execution-panel">
      <div class="execution-head">
        <span>可执行性</span>
        <strong>${score}</strong>
      </div>
      <div class="execution-bar" aria-label="可执行性分数">
        <span style="width: ${score};"></span>
      </div>
      <div class="execution-cost-row">
        <span>执行成本 ${cost}</span>
        <span>置信度 ${toPercent(execution.confidence)}</span>
      </div>
      <div class="execution-tags">${blockers}</div>
      <ol class="execution-evidence">${evidence}</ol>
    </div>
  `;
}

function renderRecommendationTrace(trace) {
  if (!trace) {
    return "";
  }
  const sources = trace.data_sources?.length
    ? trace.data_sources.map((source) => `<span>${escapeHtml(source)}</span>`).join("")
    : "<span>ranker.local_context</span>";
  const evidence = trace.evidence?.length
    ? trace.evidence.slice(0, 6).map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : "<li>暂无证据链</li>";
  const penalties = trace.penalties?.length
    ? trace.penalties.map((item) => `<span class="trace-penalty">${escapeHtml(item)}</span>`).join("")
    : "<span>no_major_penalty</span>";
  return `
    <details class="trace-panel">
      <summary>
        <span>算法追踪</span>
        <strong>${escapeHtml(String(trace.confidence ?? 0.5))}</strong>
      </summary>
      <div class="trace-grid">
        <div>
          <small>Ranker</small>
          <p>${escapeHtml(trace.ranker || "life_rec_weighted_v0")}</p>
        </div>
        <div>
          <small>Data Sources</small>
          <div class="trace-tags">${sources}</div>
        </div>
        <div>
          <small>Penalties</small>
          <div class="trace-tags">${penalties}</div>
        </div>
      </div>
      <ol class="trace-evidence">${evidence}</ol>
    </details>
  `;
}

async function sendFeedback(item, action, button) {
  button.disabled = true;
  try {
    const response = await fetch(apiUrl("/feedback"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: currentUserId(),
        request_id: state.requestId,
        item_id: item.id,
        item_name: item.name,
        item_type: item.type,
        action,
        tags: item.tags,
        source: item.meta?.source || item.meta?.provider || "unknown",
      }),
    });
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    if (action === "plan") {
      await savePlanItem(item);
    }
    button.textContent = "已记录";
    await loadUserContext();
    setStatus(action === "plan" ? "已加入计划，后续可以在侧栏查看。" : "反馈已保存，下一次推荐会参考你的偏好。", "ready");
  } catch (error) {
    button.disabled = false;
    setStatus("反馈保存失败，请确认后端已启动。", "error");
    console.error(error);
  }
}

async function savePlanItem(item) {
  const response = await fetch(apiUrl("/user/plans"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: currentUserId(),
      request_id: state.requestId,
      item_id: item.id,
      item_name: item.name,
      item_type: item.type,
      title: item.name,
      tags: item.tags,
      source: item.meta?.source || item.meta?.provider || "unknown",
      note: item.reasons?.[0] || null,
    }),
  });
  if (!response.ok) {
    throw new Error(`Plan API returned ${response.status}`);
  }
  return response.json();
}

async function updatePlanStatus(planId, status, button) {
  button.disabled = true;
  try {
    const response = await fetch(apiUrl(`/user/plans/${planId}`), {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: currentUserId(),
        status,
      }),
    });
    if (!response.ok) {
      throw new Error(`Plan status API returned ${response.status}`);
    }
    await loadUserContext();
    setStatus(status === "done" ? "计划已标记完成。" : "计划已取消。", "ready");
  } catch (error) {
    button.disabled = false;
    setStatus("计划状态更新失败，请确认后端已启动。", "error");
    console.error(error);
  }
}

async function updatePlanSchedule(planId, input, button) {
  const scheduledFor = dateTimeLocalToIso(input.value);
  if (input.value && !scheduledFor) {
    setStatus("计划时间格式无效，请重新选择。", "error");
    return;
  }

  button.disabled = true;
  try {
    const response = await fetch(apiUrl(`/user/plans/${planId}`), {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: currentUserId(),
        scheduled_for: scheduledFor,
      }),
    });
    if (!response.ok) {
      throw new Error(`Plan schedule API returned ${response.status}`);
    }
    await loadUserContext();
    setStatus(scheduledFor ? "计划时间已保存。" : "计划时间已清空。", "ready");
  } catch (error) {
    button.disabled = false;
    setStatus("计划时间保存失败，请确认后端已启动。", "error");
    console.error(error);
  }
}

async function exportUserMemory() {
  exportMemoryBtn.disabled = true;
  setStatus("正在导出完整用户记忆...", "loading");
  try {
    const response = await fetch(apiUrl(`/user/export?user_id=${encodeURIComponent(currentUserId())}&limit=300`));
    if (!response.ok) {
      throw new Error(`User memory export API returned ${response.status}`);
    }
    const data = await response.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `liferec-memory-${currentUserId()}-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setStatus(`用户记忆已导出：${data.summary?.recommendations || 0} 条推荐历史。`, "ready");
  } catch (error) {
    setStatus("用户记忆导出失败，请确认后端已启动。", "error");
    console.error(error);
  } finally {
    exportMemoryBtn.disabled = false;
  }
}

async function exportPlans() {
  exportPlansBtn.disabled = true;
  setStatus("正在导出计划...", "loading");
  try {
    const response = await fetch(apiUrl(`/user/plans/export?user_id=${encodeURIComponent(currentUserId())}&limit=200`));
    if (!response.ok) {
      throw new Error(`Plan export API returned ${response.status}`);
    }
    const data = await response.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `liferec-plans-${currentUserId()}-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setStatus(`计划已导出：${data.summary?.total || 0} 项。`, "ready");
  } catch (error) {
    setStatus("计划导出失败，请确认后端已启动。", "error");
    console.error(error);
  } finally {
    exportPlansBtn.disabled = false;
  }
}

async function exportPlansIcs() {
  exportPlansIcsBtn.disabled = true;
  setStatus("正在导出日历文件...", "loading");
  try {
    const response = await fetch(apiUrl(`/user/plans/export.ics?user_id=${encodeURIComponent(currentUserId())}&status=active&limit=200`));
    if (!response.ok) {
      throw new Error(`Plan ICS export API returned ${response.status}`);
    }
    const text = await response.text();
    const blob = new Blob([text], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `liferec-plans-${currentUserId()}-${new Date().toISOString().slice(0, 10)}.ics`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setStatus("日历文件已导出。", "ready");
  } catch (error) {
    setStatus("日历导出失败，请确认后端已启动。", "error");
    console.error(error);
  } finally {
    exportPlansIcsBtn.disabled = false;
  }
}

function setStatus(message, type) {
  statusPanel.classList.remove("is-ready", "is-error");
  if (type === "ready") {
    statusPanel.classList.add("is-ready");
  }
  if (type === "error") {
    statusPanel.classList.add("is-error");
  }

  const strong = statusPanel.querySelector("strong");
  const text = statusPanel.querySelector("p");
  strong.textContent = type === "loading" ? "生成中" : type === "error" ? "需要处理" : "状态";
  text.textContent = message;
}

function formatMetaKey(key) {
  const map = {
    avg_price: "人均",
    distance_km: "距离 km",
    location: "地点",
    address: "地址",
    latitude: "纬度",
    longitude: "经度",
    price: "价格",
    category: "分类",
    budget: "预算",
    duration: "时长",
    route_distance_meters: "步行距离 m",
    route_duration_minutes: "步行时间 min",
    route_source: "路线来源",
    provider: "Provider",
    source: "来源",
    data_type: "数据类型",
    recent_meal_tags_source: "饮食标签来源",
    recent_meal_tag_count: "饮食标签数",
  };
  return map[key] || key;
}

function parseList(value) {
  return value
    .split(/[,，、\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function mergeLists(primary, fallback) {
  const seen = new Set();
  return [...primary, ...fallback].filter((item) => {
    if (seen.has(item)) {
      return false;
    }
    seen.add(item);
    return true;
  });
}

function countPreferences(preferences) {
  if (!preferences) {
    return 0;
  }
  let count = 0;
  if (preferences.default_location) count += 1;
  if (preferences.default_budget) count += 1;
  ["taste", "avoid", "allergies", "health_goals", "travel_style"].forEach((key) => {
    count += preferences[key]?.length || 0;
  });
  return count;
}

function toPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "0%";
  }
  return `${Math.round(Math.max(0, Math.min(1, number)) * 100)}%`;
}

function formatScenarioLabel(value) {
  const map = {
    auto: "自动识别",
    diet: "饮食健康",
    restaurant: "饮食餐厅",
    shopping: "生活购物",
    travel: "旅行规划",
  };
  return map[value] || value || "未知场景";
}

function trimText(value, maxLength) {
  const text = String(value || "").trim();
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength)}...`;
}

function formatPlanDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function toDateTimeLocalValue(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value).slice(0, 16);
  }
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return localDate.toISOString().slice(0, 16);
}

function dateTimeLocalToIso(value) {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const map = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return map[char];
  });
}
