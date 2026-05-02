const uploadForm = document.getElementById("pdf-upload-form");
const fileInput = document.getElementById("pdf-file");
const submitButton = document.getElementById("upload-submit");
const statusMessage = document.getElementById("upload-status");
const resultList = document.getElementById("upload-result");

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = fileInput.files[0];
  if (!file) {
    showStatus("Choose a PDF before uploading.", "error");
    return;
  }

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    showStatus("Upload a PDF file.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  submitButton.disabled = true;
  resultList.classList.add("hidden");
  resultList.replaceChildren();
  showStatus("Uploading PDF...", "loading");

  try {
    const response = await fetch("/api/content/upload-pdf", {
      method: "POST",
      body: formData,
    });
    const result = await response.json();

    if (!response.ok) {
      showStatus(result.error || "Upload failed.", "error");
      renderResult(result);
      return;
    }

    uploadForm.reset();
    showStatus("PDF uploaded to Pinecone.", "success");
    renderResult(result);
  } catch (error) {
    console.error("Upload failed:", error);
    showStatus("Upload failed. Check that the server is still running.", "error");
  } finally {
    submitButton.disabled = false;
  }
});

function showStatus(message, type) {
  statusMessage.textContent = message;
  statusMessage.className = `upload-status ${type}`;
}

function renderResult(result) {
  const fields = [
    ["Filename", result.filename],
    ["Document ID", result.documentId],
    ["Chunks", result.chunkCount],
    ["Index", result.indexName],
    ["Namespace", result.namespace],
    ["Saved path", result.savedPath],
  ];

  const visibleFields = fields.filter(([, value]) => value !== undefined && value !== null);
  if (!visibleFields.length) {
    resultList.classList.add("hidden");
    return;
  }

  resultList.replaceChildren();
  for (const [label, value] of visibleFields) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = value;
    resultList.append(term, detail);
  }
  resultList.classList.remove("hidden");
}
