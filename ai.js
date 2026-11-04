"use strict";

const element = id => document.getElementById("ai-" + id);
const mode = element("mode");
const catalog = [window.AUTO_DATA, window.BENIF_DATA, window.EXTRA_DATA, window.LIBRARY_DATA]
  .flatMap(dataset => dataset?.items || []);
const pending = catalog.filter(item => item.material === "待分类");

for (const item of pending) {
  element("item").add(new Option(item.label || item.name, item.id));
}

function updateFields() {
  element("file-label").hidden = mode.value === "search";
  element("item-label").hidden = mode.value !== "classify";
  element("brand-label").hidden = mode.value !== "brand";
  element("preview").hidden = true;
}

function showMatches(keywords) {
  const terms = [...new Set(keywords.filter(term => typeof term === "string")
    .map(term => term.trim().toLowerCase()).filter(term => term.length >= 2))].slice(0, 20);
  const scored = catalog.map(item => {
    const fields = [item.name, item.label, item.material, ...[item.colors, item.tags, item.styles].flat()]
      .join(" ").toLowerCase();
    return { item, score: terms.filter(term => fields.includes(term)).length };
  }).filter(row => row.score > 0).sort((a, b) => b.score - a.score);
  if (!scored.length) element("output").append("\n没有找到匹配的图库条目。");
  for (const {item} of scored.slice(0, 16)) {
    const link = document.createElement("a");
    link.href = item.image;
    link.target = "_blank";
    link.rel = "noopener";
    const thumbnail = document.createElement("img");
    thumbnail.src = item.thumb;
    thumbnail.alt = "";
    thumbnail.loading = "lazy";
    link.append(thumbnail, document.createTextNode(item.label || item.name));
    element("results").append(link);
  }
}

async function encodeImage(blob) {
  const bitmap = await createImageBitmap(blob);
  try {
    const scale = Math.min(1, 768 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.82);
  } finally {
    bitmap.close();
  }
}

element("form").addEventListener("submit", async event => {
  event.preventDefault();
  const operation = mode.value;
  let input = element("text").value.trim();
  element("results").replaceChildren();
  element("output").textContent = "正在处理，请稍候…";
  element("run").disabled = true;
  try {
    let photo = operation === "search" ? null : element("file").files[0];
    if (!photo && operation === "classify") {
      const selected = pending.find(item => item.id === element("item").value);
      if (selected) {
        const response = await fetch(selected.thumb);
        if (!response.ok) throw new Error("无法读取选中的贴图。");
        photo = await response.blob();
      }
    }
    if (["classify", "similar"].includes(operation) && !photo) throw new Error("请选择一张参考图。");
    if (!photo && !input) throw new Error("请填写需求或材料说明。");
    if (operation === "brand") input = "项目品牌：" + element("brand").value + "\n" + input;
    const image = photo ? await encodeImage(photo) : "";
    element("preview").hidden = !image;
    if (image) element("preview").src = image;
    const response = await fetch("/api/ai", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({mode: operation, text: input, image: image.split(",")[1]})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    const keywords = Array.isArray(result.keywords) ? result.keywords : [];
    element("output").textContent = [
      typeof result.summary === "string" ? result.summary : "",
      keywords.filter(word => typeof word === "string").join(" · ")
    ].filter(Boolean).join("\n");
    if (["search", "similar"].includes(operation)) showMatches(keywords);
    else element("output").append("\n建议稿，请核对后再录入图库。");
  } catch (error) {
    element("output").textContent = error.message;
  } finally {
    element("run").disabled = false;
  }
});

async function initialize() {
  updateFields();
  mode.addEventListener("change", updateFields);
  if (location.origin !== "http://127.0.0.1:8100") {
    element("status").textContent = "AI 功能由本机千问运行。请在已启动模型服务的电脑打开本机工作台。";
    const link = document.createElement("a");
    link.href = "http://127.0.0.1:8100/ai.html";
    link.textContent = "打开本机 AI 工作台";
    element("status").after(link);
    return;
  }
  try {
    const response = await fetch("/api/ai");
    const status = await response.json();
    element("status").textContent = status.ready ? "已连接本机千问视觉模型 " + status.model :
      "千问视觉模型尚未就绪，请先启动 Ollama 并下载 qwen3-vl:2b，然后刷新。";
    element("form").hidden = !status.ready;
  } catch {
    element("status").textContent = "无法连接本机模型服务。";
  }
}
initialize();
