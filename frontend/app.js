const API_BASE_URL = "http://localhost:8000/api";
const API_URL = `${API_BASE_URL}/recommend`;

const state = {
  scenario: "auto",
  latitude: null,
  longitude: null,
  requestId: null,
};

const scenarioButtons = document.querySelectorAll(".scenario");
const input = document.querySelector("#messageInput");
const submitBtn = document.querySelector("#submitBtn");
const locateBtn = document.querySelector("#locateBtn");
const radiusInput = document.querySelector("#radiusInput");
const recentMealTagsInput = document.querySelector("#recentMealTagsInput");
const tasteInput = document.querySelector("#tasteInput");
const avoidInput = document.querySelector("#avoidInput");
const travelStyleInput = document.querySelector("#travelStyleInput");
const locationStatus = document.querySelector("#locationStatus");
const statusPanel = document.querySelector("#statusPanel");
const intentSummary = document.querySelector("#intentSummary");
const healthSummary = document.querySelector("#healthSummary");
const aigcSummary = document.querySelector("#aigcSummary");
const planList = document.querySelector("#planList");
const recommendationList = document.querySelector("#recommendationList");
const providerSummary = document.querySelector("#providerSummary");

loadProviderCapabilities();

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
        user_id: "u001",
        latitude: state.latitude,
        longitude: state.longitude,
        radius_km: Number(radiusInput.value || 3),
        recent_meal_tags: parseList(recentMealTagsInput.value),
        taste: parseList(tasteInput.value),
        avoid: parseList(avoidInput.value),
        allergies: parseList(avoidInput.value),
        travel_style: parseList(travelStyleInput.value),
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

function renderResult(data) {
  state.requestId = data.request_id;
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
        user_id: "u001",
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
    button.textContent = "已记录";
    setStatus("反馈已保存，下一次推荐会参考你的偏好。", "ready");
  } catch (error) {
    button.disabled = false;
    setStatus("反馈保存失败，请确认后端已启动。", "error");
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
  };
  return map[key] || key;
}

function parseList(value) {
  return value
    .split(/[,，、\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
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
