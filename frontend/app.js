const API = "/api";
const MAX_SIZE = 10 * 1024 * 1024;
const ALLOWED_EXT = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv"];

const $ = (id) => document.getElementById(id);
const dropZone = $("dropZone");
const fileInput = $("fileInput");
const previewArea = $("previewArea");
const previewThumb = $("previewThumb");
const previewName = $("previewName");
const previewSize = $("previewSize");
const titleInput = $("titleInput");
const descInput = $("descInput");
const tagsInput = $("tagsInput");
const uploadBtn = $("uploadBtn");
const cancelBtn = $("cancelBtn");
const uploadProgress = $("uploadProgress");
const progressBar = $("progressBar");
const progressText = $("progressText");
const alertBox = $("alertBox");
const fileList = $("fileList");
const emptyState = $("emptyState");

let selectedFile = null;
let currentFilter = "all";

function showAlert(msg, type = "error") {
  alertBox.textContent = msg;
  alertBox.className = `mt-4 p-3 rounded-lg text-sm ${
    type === "error" ? "bg-red-50 text-red-700 border border-red-200" : "bg-green-50 text-green-700 border border-green-200"
  }`;
  alertBox.classList.remove("hidden");
  setTimeout(() => alertBox.classList.add("hidden"), 4000);
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function getExt(name) {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i).toLowerCase() : "";
}

function validateClient(file) {
  const ext = getExt(file.name);
  if (!ALLOWED_EXT.includes(ext)) return `Extension '${ext}' no permitida`;
  if (file.size > MAX_SIZE) return "El archivo supera los 10MB";
  if (file.size === 0) return "El archivo esta vacio";
  return null;
}

function showPreview(file) {
  const err = validateClient(file);
  if (err) { showAlert(err); return; }

  selectedFile = file;
  previewName.textContent = file.name;
  previewSize.textContent = formatSize(file.size);

  previewThumb.innerHTML = "";
  if (file.type.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    img.className = "w-full h-full object-cover";
    previewThumb.appendChild(img);
  } else {
    const ext = getExt(file.name).replace(".", "").toUpperCase();
    previewThumb.innerHTML = `<span class="text-xs font-bold text-gray-500">${ext || "FILE"}</span>`;
  }

  titleInput.value = "";
  descInput.value = "";
  tagsInput.value = "";
  previewArea.classList.remove("hidden");
}

function hidePreview() {
  selectedFile = null;
  previewArea.classList.add("hidden");
  fileInput.value = "";
}

dropZone.addEventListener("click", (e) => {
  e.preventDefault();
  e.stopPropagation();
  fileInput.click();
});
fileInput.addEventListener("change", (e) => {
  if (e.target.files[0]) showPreview(e.target.files[0]);
});

["dragenter", "dragover"].forEach((ev) =>
  dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.add("dragover"); })
);
["dragleave", "drop"].forEach((ev) =>
  dropZone.addEventListener(ev, (e) => { e.preventDefault(); dropZone.classList.remove("dragover"); })
);
dropZone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) showPreview(file);
});

cancelBtn.addEventListener("click", hidePreview);

uploadBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  uploadBtn.disabled = true;
  uploadProgress.classList.remove("hidden");
  progressBar.style.width = "0%";

  const fd = new FormData();
  fd.append("file", selectedFile);
  fd.append("title", titleInput.value);
  fd.append("description", descInput.value);
  fd.append("tags", tagsInput.value);

  try {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API}/upload`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        progressBar.style.width = pct + "%";
        progressText.textContent = `Subiendo... ${pct}%`;
      }
    };
    xhr.onload = () => {
      uploadProgress.classList.add("hidden");
      uploadBtn.disabled = false;
      if (xhr.status >= 200 && xhr.status < 300) {
        showAlert("Archivo subido correctamente", "success");
        hidePreview();
        loadFiles();
      } else {
        const res = JSON.parse(xhr.responseText);
        showAlert(res.detail || "Error al subir");
      }
    };
    xhr.onerror = () => {
      uploadProgress.classList.add("hidden");
      uploadBtn.disabled = false;
      showAlert("Error de red al subir el archivo");
    };
    xhr.send(fd);
  } catch (err) {
    uploadProgress.classList.add("hidden");
    uploadBtn.disabled = false;
    showAlert("Error inesperado: " + err.message);
  }
});

document.querySelectorAll(".filter-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach((b) => {
      b.className = "filter-btn px-3 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200";
    });
    btn.className = "filter-btn px-3 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-700";
    currentFilter = btn.dataset.filter;
    loadFiles();
  });
});

async function loadFiles() {
  try {
    const url = currentFilter === "all" ? `${API}/files` : `${API}/files?category=${currentFilter}`;
    const res = await fetch(url);
    const data = await res.json();
    renderFiles(data.files);
  } catch (err) {
    showAlert("No se pudo cargar la lista de archivos");
  }
}

function renderFiles(files) {
  fileList.innerHTML = "";
  if (!files.length) {
    fileList.appendChild(emptyState);
    emptyState.classList.remove("hidden");
    return;
  }
  emptyState.classList.add("hidden");

  files.forEach((f) => {
    const card = document.createElement("div");
    card.className = "fade-in border rounded-lg p-3 bg-gray-50 hover:shadow-md transition-shadow";

    const thumbUrl = f.mime_type.startsWith("image/")
      ? `${API}/files/${f.id}/thumbnail`
      : null;

    const iconForDoc = () => {
      const ext = getExt(f.original_name).replace(".", "").toUpperCase();
      return `<div class="w-full h-32 bg-white rounded flex items-center justify-center"><span class="text-lg font-bold text-gray-400">${ext || "FILE"}</span></div>`;
    };

    const thumbHtml = thumbUrl 
      ? `<img src="${thumbUrl}" class="w-full h-full object-cover" />`
      : iconForDoc();

    card.innerHTML = `
      <div class="w-full h-32 bg-white rounded mb-2 overflow-hidden flex items-center justify-center border">
        ${thumbHtml}
      </div>
      <p class="text-sm font-medium text-gray-800 truncate" title="${f.original_name}">${f.title || f.original_name}</p>
      <p class="text-xs text-gray-500">${formatSize(f.size_bytes)} &middot; ${f.category}</p>
      ${f.tags.length ? `<div class="flex flex-wrap gap-1 mt-1">${f.tags.map((t) => `<span class="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">${t}</span>`).join("")}</div>` : ""}
      <div class="flex gap-2 mt-2">
        <a href="${API}/files/${f.id}/download" class="flex-1 text-center text-xs bg-blue-600 text-white py-1.5 rounded hover:bg-blue-700">Descargar</a>
        <button data-id="${f.id}" class="delete-btn flex-1 text-xs bg-red-100 text-red-700 py-1.5 rounded hover:bg-red-200">Eliminar</button>
      </div>
    `;
    fileList.appendChild(card);
  });

  document.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Eliminar este archivo?")) return;
      try {
        const res = await fetch(`${API}/files/${btn.dataset.id}`, { method: "DELETE" });
        if (res.ok) { showAlert("Archivo eliminado", "success"); loadFiles(); }
        else showAlert("Error al eliminar");
      } catch { showAlert("Error de red"); }
    });
  });
}

loadFiles();
