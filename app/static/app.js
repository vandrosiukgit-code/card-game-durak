const wsProtocol = location.protocol === "https:" ? "wss:" : "ws:";
const socket = new WebSocket(`${wsProtocol}//${location.host}/ws`);

const authScreen = document.getElementById("auth-screen");
const gameScreen = document.getElementById("game-screen");
const currentUserLabel = document.getElementById("current-user");
const logContainer = document.getElementById("log");
const authError = document.getElementById("auth-error");

function addLog(text) {
    const p = document.createElement("div");
    p.textContent = text;
    logContainer.appendChild(p);
    logContainer.scrollTop = logContainer.scrollHeight;
}

socket.onopen = () => addLog("🟢 Соединение с сервером установлено.");
socket.onclose = () => addLog("🔴 Соединение с сервером разорвано.");

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "AUTH_SUCCESS") {
        currentUserLabel.textContent = data.username;
        authScreen.classList.add("hidden");
        gameScreen.classList.remove("hidden");
        addLog(`Успешный вход в систему под именем: ${data.username}`);
    } else if (data.type === "AUTH_FAIL") {
        authError.textContent = data.message;
    } else if (data.type === "SYSTEM_LOG") {
        addLog(data.text);
    } else if (data.type === "ERROR") {
        alert(data.message);
    }
};

document.getElementById("btn-login").onclick = () => {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    socket.send(JSON.stringify({ type: "AUTH", username, password }));
};

document.getElementById("btn-move").onclick = () => {
    socket.send(JSON.stringify({ type: "ACTION_MOVE" }));
};
