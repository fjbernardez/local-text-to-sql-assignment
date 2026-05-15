const form = document.querySelector("#ask-form");
const questionInput = document.querySelector("#question");
const maxRowsInput = document.querySelector("#max-rows");
const naturalAnswerToggle = document.querySelector("#natural-answer");
const submitButton = document.querySelector("#submit-button");
const loadingStatus = document.querySelector("#loading-status");
const naturalLoadingNote = document.querySelector("#natural-loading-note");
const questionView = document.querySelector("#question-view");
const resultView = document.querySelector("#result-view");
const responsePanel = document.querySelector("#response-panel");
const responseMessage = document.querySelector("#response-message");
const naturalMessage = document.querySelector("#natural-message");
const sqlSection = document.querySelector("#sql-section");
const sqlOutput = document.querySelector("#sql-output");
const tableSection = document.querySelector("#table-section");
const dataTable = document.querySelector("#data-table");
const errorPanel = document.querySelector("#error-panel");
const errorMessage = document.querySelector("#error-message");
const errorDetails = document.querySelector("#error-details");
const errorTechnical = document.querySelector("#error-technical");
const resetButton = document.querySelector("#reset-button");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionInput.value.trim();
  const maxRows = Number(maxRowsInput.value);
  if (!question) {
    questionInput.focus();
    return;
  }

  if (!Number.isInteger(maxRows) || maxRows < 1 || maxRows > 100) {
    maxRowsInput.focus();
    return;
  }

  setLoading(true);

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        max_rows: maxRows,
        include_natural_answer: naturalAnswerToggle.checked,
      }),
    });

    const payload = await readJson(response);
    if (!response.ok) {
      throw new RequestError(
        payload?.detail || "The request could not be completed.",
        payload,
      );
    }

    renderResponse(payload);
  } catch (error) {
    renderError(error);
  } finally {
    setLoading(false);
    showResultView();
  }
});

resetButton.addEventListener("click", () => {
  form.reset();
  naturalAnswerToggle.checked = true;
  clearResult();
  resultView.hidden = true;
  questionView.hidden = false;
  questionInput.focus();
});

function setLoading(isLoading) {
  questionInput.disabled = isLoading;
  maxRowsInput.disabled = isLoading;
  naturalAnswerToggle.disabled = isLoading;
  submitButton.disabled = isLoading;
  loadingStatus.hidden = !isLoading;
  naturalLoadingNote.hidden = !naturalAnswerToggle.checked;
}

function showResultView() {
  questionView.hidden = true;
  resultView.hidden = false;
}

function clearResult() {
  responsePanel.hidden = true;
  responsePanel.className = "";
  errorPanel.hidden = true;
  errorDetails.hidden = true;
  responseMessage.textContent = "";
  naturalMessage.textContent = "";
  naturalMessage.hidden = true;
  sqlOutput.textContent = "";
  sqlSection.hidden = true;
  dataTable.replaceChildren();
  tableSection.hidden = true;
}

function renderResponse(payload) {
  clearResult();
  responsePanel.hidden = false;
  responsePanel.className = `result-state ${payload.type || ""}`.trim();
  responseMessage.textContent = payload.message || "Request completed.";

  if (payload.natural_message) {
    naturalMessage.textContent = payload.natural_message;
    naturalMessage.hidden = false;
  }

  if (payload.type === "query" && payload.sql) {
    sqlOutput.textContent = payload.sql;
    sqlSection.hidden = false;
  }

  if (Array.isArray(payload.data) && payload.data.length > 0) {
    renderTable(payload.data);
    tableSection.hidden = false;
  }
}

function renderError(error) {
  clearResult();
  errorPanel.hidden = false;
  errorMessage.textContent =
    error instanceof RequestError
      ? error.message
      : "Something went wrong while asking the question.";

  const details = error instanceof RequestError ? error.details : String(error);
  if (details) {
    errorTechnical.textContent =
      typeof details === "string" ? details : JSON.stringify(details, null, 2);
    errorDetails.hidden = false;
  }
}

function renderTable(rows) {
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");

  for (const column of columns) {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = column;
    headerRow.appendChild(th);
  }

  thead.appendChild(headerRow);

  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const column of columns) {
      const td = document.createElement("td");
      td.textContent = row[column] ?? "";
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }

  dataTable.replaceChildren(thead, tbody);
}

async function readJson(response) {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

class RequestError extends Error {
  constructor(message, details) {
    super(message);
    this.details = details;
  }
}
