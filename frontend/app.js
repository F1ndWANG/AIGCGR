const API_BASE_URL = "http://localhost:8000/api";
const API_URL = `${API_BASE_URL}/recommend`;

const state = {
  scenario: "auto",
  latitude: null,
  longitude: null,
  requestId: null,
  preferences: null,
  userId: localStorage.getItem("liferec:userId") || "u001",
};

const scenarioButtons = document.querySelectorAll(".scenario");
const userIdInput = document.querySelector("#userIdInput");
const switchUserBtn = document.querySelector("#switchUserBtn");
const input = document.querySelector("#messageInput");
const submitBtn = document.querySelector("#submitBtn");
const locateBtn = document.querySelector("#locateBtn");
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
const statusPanel = document.querySelector("#statusPanel");
const intentSummary = document.querySelector("#intentSummary");
const healthSummary = document.querySelector("#healthSummary");
const aigcSummary = document.querySelector("#aigcSummary");
const planList = document.querySelector("#planList");
const recommendationList = document.querySelector("#recommendationList");
const providerSummary = document.querySelector("#providerSummary");
const memorySummary = document.querySelector("#memorySummary");
const planSummary = document.querySelector("#planSummary");

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

saveWellnessBtn.addEventListener("click", async () => {
  await saveWellnessLog();
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
      locationStatus.textContent = `已启用动态位置：${state.latitude.toFixed(4)}, ${state.longitude.toFixed(4)}`;
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

async function requestRecommendation() {
  const message = input.value.trim();
  if (!message) {
    setStatus("请输入生活需求。", "error");
    return;
  }

  submitBtn.disabled = true;
  setStatus("正在生成推荐方案...", "loading");

  try {
    const response = await fetch(API_URL, {
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
        location: defaultLocationInput.value.trim() || null,
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
    const response = await fetch(`${API_BASE_URL}/recommend/refresh`, {
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
    const response = await fetch(`${API_BASE_URL}/user/meals`, {
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
    const response = await fetch(`${API_BASE_URL}/user/wellness`, {
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
    const response = await fetch(`${API_BASE_URL}/user/preferences`, {
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

function currentUserId() {
  return state.userId || "u001";
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
}

async function loadMealHistory() {
  try {
    const response = await fetch(`${API_BASE_URL}/user/meals?user_id=${encodeURIComponent(currentUserId())}&limit=20`);
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
    const response = await fetch(`${API_BASE_URL}/user/context?user_id=${encodeURIComponent(currentUserId())}&limit=20`);
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
      <strong>${data.meals?.length || 0}</strong><small>饮食记录</small>
      <strong>${data.wellness?.length || 0}</strong><small>生活状态</small>
      <strong>${positiveEvents}</strong><small>正反馈</small>
    </div>
    <div class="memory-stats">
      <strong>${negativeEvents}</strong><small>负反馈</small>
      <strong>${preferenceCount}</strong><small>长期偏好</small>
    </div>
    <div class="profile-tags">${mealTags}</div>
    <div class="profile-tags wellness-tags">${wellnessTags}</div>
  `;
  renderPlanSummary(data.plans || []);
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
    chip.innerHTML = `
      <div>
        <strong>${escapeHtml(plan.title || plan.item_name)}</strong>
        <small>${escapeHtml(plan.item_type)} · ${escapeHtml(plan.source || "unknown")}</small>
      </div>
      <div class="plan-actions">
        <button data-status="done">完成</button>
        <button data-status="canceled">取消</button>
      </div>
    `;
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
    const response = await fetch(`${API_BASE_URL}/providers/capabilities`);
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

async function sendFeedback(item, action, button) {
  button.disabled = true;
  try {
    const response = await fetch(`${API_BASE_URL}/feedback`, {
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
  const response = await fetch(`${API_BASE_URL}/user/plans`, {
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
    const response = await fetch(`${API_BASE_URL}/user/plans/${planId}`, {
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
