/* ===========================================================
   DriveInOne — shared app logic
   Talks to the FastAPI backend. Token kept in localStorage
   (this is a real deployed frontend, not a sandboxed artifact,
   so browser storage is fine here — unlike Claude-rendered
   HTML artifacts, which can't use it).
=========================================================== */

const API_BASE = "http://127.0.0.1:8000";
const TOKEN_KEY = "driveinone_token";
const USERNAME_KEY = "driveinone_username";

// ---------- Auth storage ----------

function saveSession(token, username) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USERNAME_KEY, username);
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USERNAME_KEY);
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getUsername() {
  return localStorage.getItem(USERNAME_KEY);
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "index.html";
  }
}

function logout() {
  clearSession();
  window.location.href = "index.html";
}

// ---------- API calls ----------

async function apiFetch(path, options = {}) {
  const headers = options.headers || {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (resp.status === 401) {
    clearSession();
    window.location.href = "index.html?expired=1";
    throw new Error("Session expired");
  }

  return resp;
}

async function signup(username, password) {
  const resp = await fetch(`${API_BASE}/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || "Signup failed");
  return data;
}

async function login(username, password) {
  const resp = await fetch(`${API_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || "Login failed");
  return data;
}

async function fetchFiles() {
  const resp = await apiFetch("/files");
  if (!resp.ok) throw new Error("Could not load files");
  return resp.json();
}

async function uploadFile(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.open("POST", `${API_BASE}/upload`);
    xhr.setRequestHeader("Authorization", `Bearer ${getToken()}`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      let data;
      try { data = JSON.parse(xhr.responseText); } catch { data = {}; }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data);
      } else {
        reject(new Error(data.detail || `Upload failed (${xhr.status})`));
      }
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(formData);
  });
}

async function getGdriveAuthorizeUrl() {
  const resp = await apiFetch("/accounts/gdrive/authorize");
  if (!resp.ok) throw new Error("Could not start Google Drive connection");
  return (await resp.json()).authorization_url;
}

async function getDropboxAuthorizeUrl() {
  const resp = await apiFetch("/accounts/dropbox/authorize");
  if (!resp.ok) throw new Error("Could not start Dropbox connection");
  return (await resp.json()).authorization_url;
}

// ---------- Formatting ----------

function formatBytes(bytes) {
  if (bytes === 0 || bytes === null || bytes === undefined) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, i);
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatDate(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return isoString;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

// ---------- Toast ----------

function showToast(message, type = "") {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.className = "toast";
  }, 3500);
}