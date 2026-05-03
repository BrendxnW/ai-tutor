// --- Main Application Logic ---

const statusDiv = document.getElementById("status");
const authSection = document.getElementById("auth-section");
const appSection = document.getElementById("app-section");
const sessionEndSection = document.getElementById("session-end-section");
const sessionEndMessage = document.getElementById("session-end-message");
const restartBtn = document.getElementById("restartBtn");
const micBtn = document.getElementById("micBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const connectBtn = document.getElementById("connectBtn");
const topicInput = document.getElementById("topicInput");
const topicPromptLabel = document.getElementById("topicPromptLabel");
const topicRow = document.getElementById("topic-row");
const pdfStatusSpan = document.getElementById("pdf-status");
const canvasStatusSpan = document.getElementById("canvas-status");
const topicError = document.getElementById("topic-error");
const chatLog = document.getElementById("chat-log");
const logoutBtn = document.getElementById("logoutBtn");
const curriculumPanel = document.getElementById("curriculum-panel");
const curriculumEmpty = document.getElementById("curriculum-empty");
const curriculumGoal = document.getElementById("curriculum-goal");
const curriculumDuration = document.getElementById("curriculum-duration");
const curriculumSteps = document.getElementById("curriculum-steps");
const courseIndexSection = document.getElementById("course-index-section");
const courseIndexMessage = document.getElementById("course-index-message");
const courseIndexStatus = document.getElementById("course-index-status");
const courseIndexFiles = document.getElementById("course-index-files");
const courseIndexChunks = document.getElementById("course-index-chunks");
const assignmentPicker = document.getElementById("assignment-picker");
const assignmentSelect = document.getElementById("assignmentSelect");
const assignmentSummary = document.getElementById("assignment-summary");

let currentGeminiMessageDiv = null;
let currentUserMessageDiv = null;
let lastErrorMessage = "";
let currentCurriculum = null;
let pendingSessionTopic = "";
let pendingCanvasUrl = "";
let pendingCanvasToken = "";
let pendingNamespace = "";
let pendingAssignment = null;
let selectedCourseId = getSelectedCourseId();
let courseAssignments = [];
const completedCurriculumSteps = new Set();

function getSelectedCourseId() {
  const match = window.location.pathname.match(/^\/tutor\/([^/]+)$/);
  return match ? decodeURIComponent(match[1]) : "";
}

function updateConnectionStatus(pdfConnected, canvasConnected) {
  pdfStatusSpan.textContent = pdfConnected ? "Connected" : "Not connected";
  pdfStatusSpan.className = pdfConnected ? "status-indicator connected" : "status-indicator disconnected";
  canvasStatusSpan.textContent = canvasConnected ? "Connected" : "Not connected";
  canvasStatusSpan.className = canvasConnected ? "status-indicator connected" : "status-indicator disconnected";
}

function setCanvasConnectionStatus(status) {
  canvasStatusSpan.textContent = status.text;
  canvasStatusSpan.className = `status-indicator ${status.className}`;
}

async function verifyCanvasConnection(canvasUrl, canvasToken) {
  if (!canvasUrl || !canvasToken) {
    return false;
  }

  setCanvasConnectionStatus({
    text: "Checking...",
    className: "connecting",
  });

  try {
    const response = await fetch("/api/canvas/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ canvas_url: canvasUrl, canvas_token: canvasToken }),
    });
    if (!response.ok) {
      return false;
    }

    const data = await response.json();
    return Boolean(data.connected);
  } catch (error) {
    console.error("Canvas validation failed:", error);
    return false;
  }
}

updateConnectionStatus(false, false);


const mediaHandler = new MediaHandler();
const geminiClient = new GeminiClient({
  onOpen: () => {
    statusDiv.textContent = "Planning...";
    statusDiv.className = "status connected";
    authSection.classList.add("hidden");
    appSection.classList.remove("hidden");
    geminiClient.startSession(
      pendingSessionTopic,
      pendingCanvasUrl,
      pendingCanvasToken,
      pendingNamespace,
      pendingAssignment,
    );
    startMicrophoneCaptureAfterConnect();
  },
  onMessage: (event) => {
    if (typeof event.data === "string") {
      try {
        const msg = JSON.parse(event.data);
        handleJsonMessage(msg);
      } catch (e) {
        console.error("Parse error:", e);
      }
    } else {
      mediaHandler.playAudio(event.data);
    }
  },
  onClose: (e) => {
    console.log("WS Closed:", e);
    if (lastErrorMessage) {
      statusDiv.textContent = "Connection Error";
      statusDiv.className = "status error";
    } else {
      statusDiv.textContent = "Disconnected";
      statusDiv.className = "status disconnected";
    }
    showSessionEnd();
  },
  onError: (e) => {
    console.error("WS Error:", e);
    statusDiv.textContent = "Connection Error";
    statusDiv.className = "status error";
  },
});

async function requireTutorAuth() {
  try {
    const response = await fetch("/api/auth/me");
    const result = await response.json();
    if (!result.authenticated) {
      window.location.href = "/";
      return false;
    }
    return true;
  } catch (error) {
    console.error("Could not check auth state:", error);
    window.location.href = "/";
    return false;
  }
}

function handleJsonMessage(msg) {
  if (msg.type === "error") {
    lastErrorMessage = msg.error || "An unknown Gemini API error occurred.";
    statusDiv.textContent = "Connection Error";
    statusDiv.className = "status error";
    appendMessage("error", lastErrorMessage);
  } else if (msg.type === "interrupted") {
    mediaHandler.stopAudioPlayback();
    currentGeminiMessageDiv = null;
    currentUserMessageDiv = null;
  } else if (msg.type === "turn_complete") {
    currentGeminiMessageDiv = null;
    currentUserMessageDiv = null;
  } else if (msg.type === "curriculum") {
    renderCurriculum(msg.curriculum);
  } else if (msg.type === "tool_call") {
    handleToolCall(msg);
  } else if (msg.type === "connection_status") {
    updateConnectionStatus(msg.pdf_connected, msg.canvas_connected);
  } else if (msg.type === "user") {
    if (currentUserMessageDiv) {
      currentUserMessageDiv.textContent += msg.text;
      chatLog.scrollTop = chatLog.scrollHeight;
    } else {
      currentUserMessageDiv = appendMessage("user", msg.text);
    }
  } else if (msg.type === "gemini") {
    if (currentGeminiMessageDiv) {
      currentGeminiMessageDiv.textContent += msg.text;
      chatLog.scrollTop = chatLog.scrollHeight;
    } else {
      currentGeminiMessageDiv = appendMessage("gemini", msg.text);
    }
  }
}

function appendMessage(type, text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${type}`;
  msgDiv.textContent = text;
  chatLog.appendChild(msgDiv);
  chatLog.scrollTop = chatLog.scrollHeight;
  return msgDiv;
}

function renderCurriculum(curriculum) {
  if (!curriculum || !Array.isArray(curriculum.steps)) return;

  currentCurriculum = curriculum;
  completedCurriculumSteps.clear();
  statusDiv.textContent = "Connected";
  statusDiv.className = "status connected";
  curriculumPanel.classList.remove("hidden");
  curriculumEmpty.classList.add("hidden");
  curriculumGoal.textContent = curriculum.session_goal || "";
  curriculumDuration.textContent = curriculum.estimated_minutes
    ? `${curriculum.estimated_minutes} min`
    : "";

  curriculumSteps.innerHTML = "";
  curriculum.steps.forEach((step, index) => {
    const item = document.createElement("li");
    item.className = index === 0 ? "current" : "";
    item.dataset.stepOrder = String(step.order);

    const status = document.createElement("span");
    status.className = "step-status";
    status.textContent = index === 0 ? "•" : "";

    const text = document.createElement("span");
    text.className = "step-text";
    text.textContent = step.title;

    item.append(status, text);
    curriculumSteps.appendChild(item);
  });
}

function handleToolCall(msg) {
  if (msg.name !== "mark_curriculum_step_complete") return;

  const stepOrder = Number(msg.args?.step_order || msg.result?.step_order);
  if (!Number.isInteger(stepOrder)) return;

  markCurriculumStepComplete(stepOrder);

  const coinAward = msg.result?.coin_award;
  if (coinAward && Number(coinAward.awarded) > 0) {
    appendMessage(
      "system",
      `+${coinAward.awarded} coins (${coinAward.multiplier}x streak multiplier)`
    );
  }
}

function markCurriculumStepComplete(stepOrder) {
  completedCurriculumSteps.add(stepOrder);

  const items = [...curriculumSteps.querySelectorAll("li")];
  items.forEach((item) => {
    const itemStepOrder = Number(item.dataset.stepOrder);
    const status = item.querySelector(".step-status");

    item.classList.toggle("complete", completedCurriculumSteps.has(itemStepOrder));
    if (completedCurriculumSteps.has(itemStepOrder)) {
      status.textContent = "\u2713";
    }
    item.classList.remove("current");
  });

  const nextItem = items.find((item) => {
    return !completedCurriculumSteps.has(Number(item.dataset.stepOrder));
  });
  if (nextItem) {
    nextItem.classList.add("current");
    const status = nextItem.querySelector(".step-status");
    if (status && !status.textContent) status.textContent = "•";
  }
}

async function prepareSelectedCourse() {
  if (!selectedCourseId) {
    return;
  }

  authSection.classList.add("hidden");
  courseIndexSection.classList.remove("hidden");
  statusDiv.textContent = "Preparing...";
  statusDiv.className = "status connecting";
  setCourseIndexStatus({
    status: "indexing",
    indexedFileCount: 0,
    chunkCount: 0,
    message: "Checking Canvas course PDFs...",
  });

  try {
    const response = await fetch(`/api/canvas/courses/${encodeURIComponent(selectedCourseId)}/index`, {
      method: "POST",
    });
    const result = await response.json();

    if (response.status === 401) {
      window.location.href = "/";
      return;
    }

    if (!response.ok) {
      throw new Error(result.error || "Could not prepare this Canvas course.");
    }

    handleCourseIndexResult(result);
  } catch (error) {
    showCourseIndexError(error.message || "Could not prepare this Canvas course.");
  }
}

async function pollSelectedCourseStatus() {
  if (!selectedCourseId) {
    return;
  }

  try {
    const response = await fetch(`/api/canvas/courses/${encodeURIComponent(selectedCourseId)}/index/status`);
    const result = await response.json();

    if (response.status === 401) {
      window.location.href = "/";
      return;
    }

    if (!response.ok) {
      throw new Error(result.error || "Could not check course indexing status.");
    }

    handleCourseIndexResult(result);
  } catch (error) {
    showCourseIndexError(error.message || "Could not check course indexing status.");
  }
}

function handleCourseIndexResult(result) {
  setCourseIndexStatus(result);

  if (result.status === "ready") {
    pendingNamespace = result.namespace || "";
    courseIndexSection.classList.add("hidden");
    authSection.classList.remove("hidden");
    updateConnectionStatus(true, true);
    statusDiv.textContent = "Ready";
    statusDiv.className = "status connected";
    loadCourseAssignments();
    topicInput.focus();
    return;
  }

  if (result.status === "indexing") {
    window.setTimeout(pollSelectedCourseStatus, 2000);
    return;
  }

  if (result.status === "empty") {
    statusDiv.textContent = "No PDFs Found";
    statusDiv.className = "status disconnected";
    return;
  }

  if (result.status === "failed") {
    showCourseIndexError(result.message || "Canvas course indexing failed.");
  }
}

function setCourseIndexStatus(result) {
  courseIndexStatus.textContent = result.status || "Starting";
  courseIndexFiles.textContent = String(result.indexedFileCount || 0);
  courseIndexChunks.textContent = String(result.chunkCount || 0);
  courseIndexMessage.textContent = result.message || "Preparing course content...";
}

function showCourseIndexError(message) {
  courseIndexMessage.textContent = message;
  courseIndexStatus.textContent = "Failed";
  statusDiv.textContent = "Course Prep Failed";
  statusDiv.className = "status error";
}

function summarizeAssignment(assignment) {
  if (!assignment) return "";

  const details = [];
  if (assignment.due_at) details.push(`Due ${assignment.due_at}`);
  if (assignment.points_possible !== null && assignment.points_possible !== undefined) {
    details.push(`${assignment.points_possible} points`);
  }
  if (assignment.description) {
    const description = assignment.description.length > 180
      ? `${assignment.description.slice(0, 177)}...`
      : assignment.description;
    details.push(description);
  }

  return details.join(" · ");
}

function getSelectedAssignment() {
  if (!assignmentSelect) return null;
  const selectedId = assignmentSelect.value;
  if (!selectedId) return null;
  return courseAssignments.find((assignment) => String(assignment.id) === selectedId) || null;
}

function updateTopicPromptVisibility(assignment) {
  const assignmentSelected = Boolean(assignment);
  if (topicPromptLabel) {
    topicPromptLabel.classList.toggle("hidden", assignmentSelected);
  }
  if (topicInput) {
    topicInput.classList.toggle("hidden", assignmentSelected);
  }
  if (topicRow) {
    topicRow.classList.toggle("assignment-selected", assignmentSelected);
  }
}

function renderCourseAssignments(assignments) {
  courseAssignments = Array.isArray(assignments) ? assignments : [];
  if (!assignmentPicker || !assignmentSelect) return;

  assignmentSelect.innerHTML = "";
  const emptyOption = document.createElement("option");
  emptyOption.value = "";
  emptyOption.textContent = "Choose an assignment...";
  assignmentSelect.appendChild(emptyOption);

  courseAssignments.forEach((assignment) => {
    const option = document.createElement("option");
    option.value = String(assignment.id);
    option.textContent = assignment.name || `Assignment ${assignment.id}`;
    assignmentSelect.appendChild(option);
  });

  assignmentPicker.classList.toggle("hidden", courseAssignments.length === 0);
  if (assignmentSummary) {
    assignmentSummary.textContent = "";
    assignmentSummary.classList.add("hidden");
  }
  updateTopicPromptVisibility(null);
}

async function loadCourseAssignments() {
  if (!selectedCourseId || !assignmentPicker) return;

  try {
    const response = await fetch(`/api/canvas/courses/${encodeURIComponent(selectedCourseId)}/assignments`);
    const result = await response.json();

    if (response.status === 401) {
      window.location.href = "/";
      return;
    }

    if (!response.ok) {
      throw new Error(result.error || "Could not load Canvas assignments.");
    }

    renderCourseAssignments(result.assignments);
  } catch (error) {
    console.error("Could not load Canvas assignments:", error);
    renderCourseAssignments([]);
  }
}

if (assignmentSelect) {
  assignmentSelect.onchange = () => {
    const assignment = getSelectedAssignment();
    if (!assignmentSummary) return;

    const summary = summarizeAssignment(assignment);
    assignmentSummary.textContent = summary;
    assignmentSummary.classList.toggle("hidden", !summary);
    updateTopicPromptVisibility(assignment);
  };
}

// Connect Button Handler
connectBtn.onclick = async () => {
  const assignment = getSelectedAssignment();
  const topic = assignment ? "" : topicInput.value.trim();

  pendingSessionTopic = topic;
  pendingAssignment = assignment;
  topicError.textContent = "";
  topicError.classList.add("hidden");
  statusDiv.textContent = "Connecting...";
  statusDiv.className = "status connecting";
  connectBtn.disabled = true;

  let canvasUrl = "";
  let canvasToken = "";

  if (!pendingNamespace) {
    try {
      const response = await fetch('/api/settings');
      if (response.ok) {
        const data = await response.json();
        const settings = data.settings || {};
        canvasUrl = settings.canvas_url || "";
        canvasToken = settings.canvas_token || "";
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  }

  pendingCanvasUrl = canvasUrl;
  pendingCanvasToken = canvasToken;

  const canvasProvided = Boolean(canvasUrl && canvasToken);
  let canvasConnected = false;

  if (pendingNamespace) {
    setCanvasConnectionStatus({
      text: "Connected",
      className: "connected",
    });
  } else if (canvasProvided) {
    canvasConnected = await verifyCanvasConnection(canvasUrl, canvasToken);
    setCanvasConnectionStatus({
      text: canvasConnected ? "Connected" : "Not connected",
      className: canvasConnected ? "connected" : "disconnected",
    });

    if (!canvasConnected) {
      statusDiv.textContent = "Canvas validation failed";
      statusDiv.className = "status error";
      connectBtn.disabled = false;
      return;
    }
  } else {
    setCanvasConnectionStatus({
      text: "Not connected",
      className: "disconnected",
    });
  }

  try {
    statusDiv.textContent = "Connecting...";
    geminiClient.connect();
  } catch (error) {
    console.error("Connection error:", error);
    mediaHandler.stopAudio();
    micBtn.textContent = "Start Mic";
    topicError.textContent = error.message || "Microphone access is required to start the tutor.";
    topicError.classList.remove("hidden");
    statusDiv.textContent = "Microphone required";
    statusDiv.className = "status error";
    connectBtn.disabled = false;
  }
};

topicInput.onkeypress = (e) => {
  if (e.key === "Enter") connectBtn.click();
};

// UI Controls
disconnectBtn.onclick = () => {
  geminiClient.disconnect();
};

async function startMicrophoneCapture() {
  if (mediaHandler.isRecording) return;

  await mediaHandler.startAudio((data) => {
    if (geminiClient.isConnected()) {
      geminiClient.send(data);
    }
  });
  micBtn.textContent = "Stop Mic";
}

async function startMicrophoneCaptureAfterConnect() {
  try {
    await startMicrophoneCapture();
  } catch (error) {
    console.error("Microphone startup failed:", error);
    mediaHandler.stopAudio();
    micBtn.textContent = "Start Mic";
    topicError.textContent =
      error.message || "Microphone access failed. The tutor is still connected.";
    topicError.classList.remove("hidden");
    appendMessage("error", topicError.textContent);
    if (statusDiv.textContent === "Planning...") {
      statusDiv.textContent = "Connected";
    }
  }
}

micBtn.onclick = async () => {
  if (mediaHandler.isRecording) {
    mediaHandler.stopAudio();
    micBtn.textContent = "Start Mic";
  } else {
    try {
      if (!geminiClient.isConnected()) {
        throw new Error("Connect to the tutor before starting the mic.");
      }
      await startMicrophoneCapture();
    } catch (e) {
      alert(e.message || "Could not start audio capture");
    }
  }
};

function resetUI() {
  authSection.classList.remove("hidden");
  if (courseIndexSection) courseIndexSection.classList.add("hidden");
  appSection.classList.add("hidden");
  sessionEndSection.classList.add("hidden");

  mediaHandler.stopAudio();

  micBtn.textContent = "Start Mic";
  chatLog.innerHTML = "";
  currentCurriculum = null;
  pendingSessionTopic = "";
  pendingCanvasUrl = "";
  pendingCanvasToken = "";
  pendingAssignment = null;
  completedCurriculumSteps.clear();
  curriculumPanel.classList.add("hidden");
  curriculumEmpty.classList.remove("hidden");
  curriculumGoal.textContent = "";
  curriculumDuration.textContent = "";
  curriculumSteps.innerHTML = "";
  topicError.textContent = "";
  topicError.classList.add("hidden");
  lastErrorMessage = "";
  sessionEndMessage.textContent = "";
  sessionEndMessage.classList.add("hidden");
  connectBtn.disabled = false;
}

function showSessionEnd() {
  appSection.classList.add("hidden");
  sessionEndSection.classList.remove("hidden");
  sessionEndMessage.textContent = lastErrorMessage;
  sessionEndMessage.classList.toggle("hidden", !lastErrorMessage);
  mediaHandler.stopAudio();
}

restartBtn.onclick = () => {
  resetUI();
};

if (logoutBtn) {
  logoutBtn.onclick = async () => {
    geminiClient.disconnect();
    resetUI();

    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      window.location.href = "/";
    }
  };
}

async function initializeTutorPage() {
  const authenticated = await requireTutorAuth();
  if (authenticated) {
    prepareSelectedCourse();
  }
}

initializeTutorPage();
