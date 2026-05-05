const result = document.getElementById("result");
const clearBtn = document.getElementById("clear");

function appendEntry(method, path, status, body, elapsed) {
  if (result.textContent.trim().startsWith("Clique")) {
    result.textContent = "";
  }
  const entry = document.createElement("div");
  entry.className = "entry " + (status >= 200 && status < 400 ? "ok" : "err");
  const ts = new Date().toLocaleTimeString();
  entry.innerHTML =
    `<span class="ts">[${ts}]</span> ` +
    `<strong>${method}</strong> ${path} ` +
    `→ <span class="status">${status}</span> ` +
    `<span class="ts">(${elapsed}ms)</span>\n` +
    JSON.stringify(body, null, 2);
  result.prepend(entry);
}

async function trigger(button) {
  const path = button.dataset.action;
  const method = button.dataset.method || "GET";
  const start = performance.now();
  button.disabled = true;
  try {
    const resp = await fetch(path, { method });
    const elapsed = Math.round(performance.now() - start);
    let body;
    try {
      body = await resp.json();
    } catch {
      body = { mensagem: await resp.text() };
    }
    appendEntry(method, path, resp.status, body, elapsed);
  } catch (err) {
    const elapsed = Math.round(performance.now() - start);
    appendEntry(method, path, 0, { erro: String(err) }, elapsed);
  } finally {
    button.disabled = false;
  }
}

document.querySelectorAll("button[data-action]").forEach((btn) => {
  btn.addEventListener("click", () => trigger(btn));
});

clearBtn.addEventListener("click", () => {
  result.textContent = "Saída limpa.";
});
