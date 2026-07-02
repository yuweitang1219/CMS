// Global State
let state = {
    hasUsers: false,
    loggedIn: false,
    username: "",
    todos: [],
    events: [],
    todoFilter: "all", // 'all', 'active', 'completed'
    selectedDate: new Date(),
    currentCalendarMonth: new Date(),
    settings: null,
    syncInterval: null
};

// Page Init
document.addEventListener("DOMContentLoaded", () => {
    checkAuthStatus();
    startClock();
    updateWeather();
    setInterval(updateWeather, 900000); // Update every 15 minutes
    initClockCollapseState();
});

// Clock Logic
function startClock() {
    const timeDisplay = document.getElementById("clock-time");
    const dateDisplay = document.getElementById("clock-date");
    const miniClockDisplay = document.getElementById("mini-calendar-clock");
    
    const weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
    
    function updateClock() {
        const now = new Date();
        
        // Format Time
        let hours = String(now.getHours()).padStart(2, '0');
        let minutes = String(now.getMinutes()).padStart(2, '0');
        let seconds = String(now.getSeconds()).padStart(2, '0');
        const timeStr = `${hours}:${minutes}:${seconds}`;
        
        if (timeDisplay) timeDisplay.textContent = timeStr;
        if (miniClockDisplay) miniClockDisplay.textContent = timeStr;
        
        // Format Date
        let year = now.getFullYear();
        let month = String(now.getMonth() + 1).padStart(2, '0');
        let date = String(now.getDate()).padStart(2, '0');
        let day = weekdays[now.getDay()];
        if (dateDisplay) dateDisplay.textContent = `${year}年${month}月${date}日 ${day}`;
    }
    
    updateClock();
    setInterval(updateClock, 1000);
}

// Weather Widget Logic
async function updateWeather() {
    try {
        const response = await fetch("https://api.open-meteo.com/v1/forecast?latitude=24.957&longitude=121.225&current_weather=true&timezone=Asia%2FTaipei");
        if (response.ok) {
            const data = await response.json();
            const temp = Math.round(data.current_weather.temperature);
            const code = data.current_weather.weathercode;
            
            let conditionText = "晴時多雲";
            let iconClass = "fa-solid fa-cloud-sun";
            
            // Map WMO Weather Interpretation Codes (WMO code)
            if (code === 0) {
                conditionText = "晴天";
                iconClass = "fa-solid fa-sun text-yellow";
            } else if ([1, 2, 3].includes(code)) {
                conditionText = "多雲";
                iconClass = "fa-solid fa-cloud-sun";
            } else if ([45, 48].includes(code)) {
                conditionText = "有霧";
                iconClass = "fa-solid fa-smog";
            } else if ([51, 53, 55, 56, 57].includes(code)) {
                conditionText = "毛毛雨";
                iconClass = "fa-solid fa-cloud-rain";
            } else if ([61, 63, 65, 66, 67].includes(code)) {
                conditionText = "下雨";
                iconClass = "fa-solid fa-cloud-showers-heavy text-blue";
            } else if ([71, 73, 75, 77].includes(code)) {
                conditionText = "下雪";
                iconClass = "fa-solid fa-snowflake";
            } else if ([80, 81, 82].includes(code)) {
                conditionText = "陣雨";
                iconClass = "fa-solid fa-cloud-showers-water";
            } else if ([95, 96, 99].includes(code)) {
                conditionText = "雷陣雨";
                iconClass = "fa-solid fa-cloud-bolt text-purple";
            }
            
            const tempEl = document.getElementById("weather-temp");
            const condEl = document.getElementById("weather-cond");
            if (tempEl) tempEl.textContent = `${temp}°C`;
            if (condEl) condEl.innerHTML = `<i class="${iconClass}"></i> ${conditionText}`;
        }
    } catch (error) {
        console.error("Failed to fetch weather data:", error);
    }
}

// --- AUTHENTICATION ---

async function checkAuthStatus() {
    try {
        const response = await fetch("/api/auth/status");
        const data = await response.json();
        
        state.hasUsers = data.has_users;
        state.loggedIn = data.logged_in;
        state.username = data.username || "";
        
        const loginView = document.getElementById("login-view");
        const dashboardView = document.getElementById("dashboard-view");
        
        if (!state.loggedIn) {
            loginView.classList.remove("hidden");
            dashboardView.classList.add("hidden");
            
            // Adjust form for Register vs Login
            const title = document.getElementById("auth-title");
            const subtitle = document.getElementById("auth-subtitle");
            const btnText = document.querySelector("#auth-submit-btn span");
            
            if (!state.hasUsers) {
                title.textContent = "初始化管理員帳號";
                subtitle.textContent = "這是系統第一次啟動，請設定一組主管理員帳密以保護您的資料。";
                btnText.textContent = "建立帳密並登入";
            } else {
                title.textContent = "登入儀表板";
                subtitle.textContent = "請輸入密碼以進入您的個人生活儀表板。";
                btnText.textContent = "登入";
            }
        } else {
            loginView.classList.add("hidden");
            dashboardView.classList.remove("hidden");
            const userDisplayNameEl = document.getElementById("user-display-name");
            if (userDisplayNameEl) {
                userDisplayNameEl.textContent = state.username;
            }
            
            // Render default calendar structure immediately to prevent blank UI while fetching
            renderMiniCalendar();
            
            // Initial data fetch
            await loadSettings();
            await fetchTodos();
            await fetchEvents();
            
            // Start background sync every 4 seconds for real-time updates (prevents lagging on tablets)
            if (state.syncInterval) clearInterval(state.syncInterval);
            state.syncInterval = setInterval(() => {
                fetchTodos(false); // fetch silently without resetting UI state
                fetchEvents(false);
            }, 4000);
        }
    } catch (error) {
        console.error("Auth check failed:", error);
        showToast("無法連接至伺服器。");
    }
}

async function handleAuthSubmit(event) {
    event.preventDefault();
    const usernameInput = document.getElementById("username").value.trim();
    const passwordInput = document.getElementById("password").value;
    const errorEl = document.getElementById("auth-error");
    
    errorEl.classList.add("hidden");
    
    const endpoint = !state.hasUsers ? "/api/auth/register" : "/api/auth/login";
    
    try {
        if (!state.hasUsers) {
            // First register
            const regResponse = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: usernameInput, password: passwordInput })
            });
            if (!regResponse.ok) {
                const data = await regResponse.json();
                throw new Error(data.detail || "註冊失敗");
            }
            // Auto login after registration
            const loginResponse = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: usernameInput, password: passwordInput })
            });
            if (loginResponse.ok) {
                showToast("帳密建立成功並已登入！");
                checkAuthStatus();
            } else {
                throw new Error("自動登入失敗，請手動登入");
            }
        } else {
            // Standard login
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: usernameInput, password: passwordInput })
            });
            if (response.ok) {
                showToast("登入成功！");
                checkAuthStatus();
            } else {
                const data = await response.json();
                throw new Error(data.detail || "帳號或密碼錯誤");
            }
        }
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.remove("hidden");
    }
}

async function handleLogout() {
    try {
        await fetch("/api/auth/logout", { method: "POST" });
        if (state.syncInterval) clearInterval(state.syncInterval);
        showToast("已成功登出。");
        checkAuthStatus();
    } catch (error) {
        showToast("登出失敗。");
    }
}

// --- TODO LIST MANAGER ---

async function fetchTodos(showLoading = true) {
    try {
        const response = await fetch("/api/todos");
        if (response.ok) {
            const newTodos = await response.json();
            if (!areTodosEqual(state.todos, newTodos)) {
                state.todos = newTodos;
                renderTodos();
            }
        }
    } catch (error) {
        console.error("Failed to fetch todos:", error);
    }
}

function renderTodos() {
    const todoList = document.getElementById("todo-list");
    const emptyState = document.getElementById("todo-list-empty");
    todoList.innerHTML = "";
    
    // Filter
    let filteredTodos = state.todos;
    if (state.todoFilter === "active") {
        filteredTodos = state.todos.filter(t => t.completed === 0);
    } else if (state.todoFilter === "completed") {
        filteredTodos = state.todos.filter(t => t.completed === 1);
    }
    
    if (filteredTodos.length === 0) {
        emptyState.classList.remove("hidden");
    } else {
        emptyState.classList.add("hidden");
        
        filteredTodos.forEach(todo => {
            const li = document.createElement("li");
            li.className = `todo-item ${todo.completed ? 'completed' : ''}`;
            
            // Format due date if exists
            let dueHtml = "";
            if (todo.due_date) {
                dueHtml = `<span class="todo-due"><i class="fa-regular fa-clock"></i> ${todo.due_date}</span>`;
            }
            
            li.innerHTML = `
                <div class="todo-item-left" onclick="toggleTodo(${todo.id}, ${todo.completed})">
                    <div class="custom-checkbox">
                        <i class="fa-solid fa-check"></i>
                    </div>
                    <div class="todo-item-content">
                        <span class="todo-item-title">${escapeHTML(todo.title)}</span>
                        <div class="todo-item-details">
                            <span class="badge-priority ${todo.priority}">${getPriorityLabel(todo.priority)}</span>
                            ${dueHtml}
                        </div>
                    </div>
                </div>
                <button class="btn-delete-todo" onclick="deleteTodo(${todo.id})" title="刪除任務">
                    <i class="fa-regular fa-trash-can"></i>
                </button>
            `;
            todoList.appendChild(li);
        });
    }
    
    // Update Progress Circular Ring
    const total = state.todos.length;
    const completed = state.todos.filter(t => t.completed === 1).length;
    document.getElementById("todo-progress-count").textContent = `${completed} / ${total} 完成`;
    
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
    document.getElementById("todo-progress-percentage").textContent = `${percentage}%`;
    
    // SVG DashOffset Update
    // Radius of circle is 18. Circumference is 2 * pi * r = 113.1
    const offset = 113.1 - (113.1 * percentage) / 100;
    document.getElementById("todo-progress-circle").style.strokeDashoffset = offset;
}

async function handleAddTodo(event) {
    event.preventDefault();
    const titleInput = document.getElementById("todo-input-title");
    const prioritySelect = document.getElementById("todo-input-priority");
    const dateSelect = document.getElementById("todo-input-date");
    
    const payload = {
        title: titleInput.value.trim(),
        priority: prioritySelect.value,
        due_date: dateSelect.value || null
    };
    
    try {
        const response = await fetch("/api/todos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (response.ok) {
            titleInput.value = "";
            dateSelect.value = "";
            prioritySelect.value = "medium";
            showToast("任務新增成功！");
            fetchTodos();
        } else {
            showToast("新增任務失敗。");
        }
    } catch (error) {
        showToast("連線錯誤。");
    }
}

async function toggleTodo(id, currentCompleted) {
    try {
        const response = await fetch(`/api/todos/${id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ completed: !currentCompleted })
        });
        if (response.ok) {
            fetchTodos();
        } else {
            showToast("更新狀態失敗。");
        }
    } catch (error) {
        showToast("連線錯誤。");
    }
}

async function deleteTodo(id) {
    if (!confirm("確定要刪除此待辦事項嗎？")) return;
    try {
        const response = await fetch(`/api/todos/${id}`, { method: "DELETE" });
        if (response.ok) {
            showToast("任務已刪除。");
            fetchTodos();
        } else {
            showToast("刪除任務失敗。");
        }
    } catch (error) {
        showToast("連線錯誤。");
    }
}

function setTodoFilter(filter) {
    state.todoFilter = filter;
    document.querySelectorAll(".todo-filters button").forEach(btn => btn.classList.remove("active"));
    document.getElementById(`filter-${filter}`).classList.add("active");
    renderTodos();
}

function getPriorityLabel(p) {
    switch(p) {
        case 'high': return '高';
        case 'medium': return '中';
        case 'low': return '低';
        default: return '中';
    }
}

// --- GOOGLE CALENDAR ---

async function fetchEvents(showLoading = true) {
    const disconnectedEl = document.getElementById("calendar-disconnected-state");
    const connectedEl = document.getElementById("calendar-connected-state");
    
    try {
        const response = await fetch("/api/calendar/events");
        const data = await response.json();
        
        if (data.error === "not_authorized" || data.error === "unauthorized_by_google") {
            disconnectedEl.classList.remove("hidden");
            connectedEl.classList.add("hidden");
            updateGoogleBadge(false);
        } else if (data.events || data.items) {
            disconnectedEl.classList.add("hidden");
            connectedEl.classList.remove("hidden");
            updateGoogleBadge(true);
            
            const newEvents = data.items || [];
            if (!areEventsEqual(state.events, newEvents)) {
                state.events = newEvents;
                renderMiniCalendar();
                renderEvents();
            }
        }
    } catch (error) {
        console.error("Failed to fetch calendar events:", error);
    }
}

function updateGoogleBadge(isConnected) {
    const badge = document.getElementById("status-google");
    if (isConnected) {
        badge.className = "status-badge connected";
        badge.querySelector("span").textContent = "Google 日曆已同步";
    } else {
        badge.className = "status-badge disconnected";
        badge.querySelector("span").textContent = "Google 日曆未連線";
    }
}

function formatEventSummaryForCell(summary) {
    if (!summary) return "";
    let clean = summary.replace(/[\u2300-\u27BF]|📋|⚡|🔥|⭐/g, "").trim();
    if (clean.includes("私人行程：")) {
        return clean.replace("私人行程：", "私人 ");
    }
    if (clean.includes("私人行程:")) {
        return clean.replace("私人行程:", "私人 ");
    }
    let name = "";
    let type = "";
    if (clean.includes("家訪：") || clean.includes("家訪:")) {
        let part = clean.includes("家訪：") ? clean.split("家訪：")[1] : clean.split("家訪:")[1];
        part = part.trim();
        name = part.split("(")[0].split(" ")[0].trim();
        if (part.includes("(")) {
            let inside = part.split("(")[1].split(")")[0];
            if (inside.includes("AA01")) type = "AA01";
            else if (inside.includes("複評") || inside.includes("ReEval")) type = "複評";
            else if (inside.includes("共訪") || inside.includes("CoVisit")) type = "共訪";
            else if (inside.includes("新案") || inside.includes("NewCase")) type = "新案";
            else if (inside.includes("準新案") || inside.includes("PreNewCase")) type = "準新案";
            else if (inside.includes("計畫異動") || inside.includes("PlanChange")) type = "異動";
            else type = inside.split(" ")[0].trim();
        }
    }
    if (name && type) return `${name} ${type}`;
    if (name) return name;
    return clean;
}

function renderMiniCalendar() {
    const container = document.getElementById("mini-calendar-days");
    const monthYearLabel = document.getElementById("mini-calendar-month-year");
    container.innerHTML = "";
    
    const year = state.currentCalendarMonth.getFullYear();
    const month = state.currentCalendarMonth.getMonth();
    
    monthYearLabel.textContent = `${year}年${month + 1}月`;
    
    // First day of month
    const firstDay = new Date(year, month, 1).getDay();
    // Total days in month
    const totalDays = new Date(year, month + 1, 0).getDate();
    // Total days in previous month
    const prevTotalDays = new Date(year, month, 0).getDate();
    
    // Renders previous month padded days
    for (let i = firstDay - 1; i >= 0; i--) {
        const dayDiv = document.createElement("div");
        dayDiv.className = "mini-day prev-month";
        
        const thisDate = new Date(year, month - 1, prevTotalDays - i);
        const dayOfWeek = thisDate.getDay();
        if (dayOfWeek === 6) dayDiv.classList.add("weekend-sat");
        if (dayOfWeek === 0) dayDiv.classList.add("weekend-sun");
        
        const dayNumSpan = document.createElement("span");
        dayNumSpan.className = "day-number";
        dayNumSpan.textContent = prevTotalDays - i;
        dayDiv.appendChild(dayNumSpan);
        
        container.appendChild(dayDiv);
    }
    
    // Renders current month days
    const today = new Date();
    for (let d = 1; d <= totalDays; d++) {
        const dayDiv = document.createElement("div");
        dayDiv.className = "mini-day";
        
        const thisDate = new Date(year, month, d);
        const dayOfWeek = thisDate.getDay();
        
        // Highlight weekends
        if (dayOfWeek === 6) {
            dayDiv.classList.add("weekend-sat");
        } else if (dayOfWeek === 0) {
            dayDiv.classList.add("weekend-sun");
        }
        
        // Highlight today
        if (thisDate.toDateString() === today.toDateString()) {
            dayDiv.classList.add("today");
        }
        
        // Highlight selected
        if (thisDate.toDateString() === state.selectedDate.toDateString()) {
            dayDiv.classList.add("selected");
        }
        
        // Day number header
        const dayNumSpan = document.createElement("span");
        dayNumSpan.className = "day-number";
        dayNumSpan.textContent = d;
        dayDiv.appendChild(dayNumSpan);
        
        // Render events directly inside the day cell
        const eventsContainer = document.createElement("div");
        eventsContainer.className = "day-events-container";
        
        const dayEvents = getEventsOnDay(thisDate);
        dayEvents.forEach(event => {
            const eventDiv = document.createElement("div");
            eventDiv.className = "day-event-item";
            
            // Format start time
            let timeStr = "全天";
            if (event.start.dateTime) {
                const eventTime = new Date(event.start.dateTime);
                const hrs = String(eventTime.getHours()).padStart(2, '0');
                const mins = String(eventTime.getMinutes()).padStart(2, '0');
                timeStr = `${hrs}:${mins}`;
            }
            eventDiv.textContent = `${timeStr} ${formatEventSummaryForCell(event.summary)}`;
            eventDiv.title = `${timeStr} ${event.summary}${event.description ? '\n' + event.description : ''}`;
            
            eventsContainer.appendChild(eventDiv);
        });
        
        dayDiv.appendChild(eventsContainer);
        
        dayDiv.onclick = (e) => {
            state.selectedDate = thisDate;
            renderMiniCalendar();
            renderEvents();
        };
        
        container.appendChild(dayDiv);
    }
    
    // Renders next month padded days (fill grid of 42 cells)
    const totalCells = firstDay + totalDays;
    const nextPad = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
    for (let i = 1; i <= nextPad; i++) {
        const dayDiv = document.createElement("div");
        dayDiv.className = "mini-day next-month";
        
        const thisDate = new Date(year, month + 1, i);
        const dayOfWeek = thisDate.getDay();
        if (dayOfWeek === 6) dayDiv.classList.add("weekend-sat");
        if (dayOfWeek === 0) dayDiv.classList.add("weekend-sun");
        
        const dayNumSpan = document.createElement("span");
        dayNumSpan.className = "day-number";
        dayNumSpan.textContent = i;
        dayDiv.appendChild(dayNumSpan);
        
        container.appendChild(dayDiv);
    }
}

function changeMonth(direction) {
    state.currentCalendarMonth.setMonth(state.currentCalendarMonth.getMonth() + direction);
    renderMiniCalendar();
}

function hasEventsOnDay(date) {
    const events = state.events || [];
    return events.some(event => {
        if (!event || !event.start) return false;
        const start = event.start.dateTime || event.start.date;
        if (!start) return false;
        const eventDate = new Date(start);
        return eventDate.toDateString() === date.toDateString();
    });
}

function getEventsOnDay(date) {
    const events = state.events || [];
    return events.filter(event => {
        if (!event || !event.start) return false;
        const start = event.start.dateTime || event.start.date;
        if (!start) return false;
        const eventDate = new Date(start);
        return eventDate.toDateString() === date.toDateString();
    });
}

function renderEvents() {
    const listEl = document.getElementById("events-list");
    const emptyEl = document.getElementById("events-list-empty");
    const eventsContainer = document.querySelector('.events-timeline');
    const todoContainer = document.querySelector('.todo-card');
    listEl.innerHTML = "";

    // Filter events for selected day
    const events = state.events || [];
    const dayEvents = events.filter(event => {
        if (!event || !event.start) return false;
        const start = event.start.dateTime || event.start.date;
        if (!start) return false;
        const eventDate = new Date(start);
        return eventDate.toDateString() === state.selectedDate.toDateString();
    });

    const isFullscreen = !!document.fullscreenElement;

    if (isFullscreen) {
        // Fullscreen mode: hide todo-card when calendar events exist, show it when they don't (like original behavior)
        if (dayEvents.length === 0) {
            eventsContainer.classList.add('hidden');
            todoContainer.classList.remove('hidden');
            emptyEl.classList.add('hidden');
            renderTodos();
        } else {
            eventsContainer.classList.remove('hidden');
            todoContainer.classList.add('hidden');
            emptyEl.classList.add('hidden');
            renderEventsList(dayEvents, listEl);
        }
    } else {
        // Normal mode: keep both cards visible, toggle empty state placeholder inside eventsContainer
        eventsContainer.classList.remove('hidden');
        todoContainer.classList.remove('hidden');
        if (dayEvents.length === 0) {
            emptyEl.classList.remove('hidden');
        } else {
            emptyEl.classList.add('hidden');
            renderEventsList(dayEvents, listEl);
        }
    }
}

function renderEventsList(dayEvents, listEl) {
    dayEvents.forEach(event => {
        const div = document.createElement("div");
        div.className = "event-item";

        // Format time range
        let timeStr = "整天";
        if (event.start.dateTime) {
            const start = new Date(event.start.dateTime);
            const end = new Date(event.end.dateTime);

            const startHour = String(start.getHours()).padStart(2, '0');
            const startMin = String(start.getMinutes()).padStart(2, '0');
            const endHour = String(end.getHours()).padStart(2, '0');
            const endMin = String(end.getMinutes()).padStart(2, '0');

            timeStr = `${startHour}:${startMin} - ${endHour}:${endMin}`;
        }

        div.innerHTML = `
            <div class="event-item-left">
                <span class="event-title">${escapeHTML(event.summary)}</span>
                <span class="event-desc">${escapeHTML(event.description || "無詳細備註")}</span>
                <span class="event-time"><i class="fa-regular fa-clock"></i> ${timeStr}</span>
            </div>
            <button class="btn-delete-event" onclick="deleteEvent('${event.id}')" title="刪除行程">
                <i class="fa-regular fa-trash-can"></i>
            </button>
        `;
        listEl.appendChild(div);
    });
}

async function deleteEvent(eventId) {
    if (!confirm("確定要將此日程從 Google 日曆刪除嗎？")) return;
    try {
        const response = await fetch(`/api/calendar/events/${eventId}`, { method: "DELETE" });
        if (response.ok) {
            showToast("行程已成功刪除。");
            fetchEvents();
        } else {
            showToast("刪除行程失敗。");
        }
    } catch (error) {
        showToast("連線錯誤。");
    }
}

// Modal open with date pre-filled
function openAddEventModal() {
    const modal = document.getElementById("add-event-modal");
    modal.classList.remove("hidden");
    
    // Format selectedDate in local timezone to avoid UTC day shifts
    const y = state.selectedDate.getFullYear();
    const m = String(state.selectedDate.getMonth() + 1).padStart(2, '0');
    const d = String(state.selectedDate.getDate()).padStart(2, '0');
    const dateStr = `${y}-${m}-${d}`;
    
    const now = new Date();
    const hour = String(now.getHours()).padStart(2, '0');
    const startStr = `${dateStr}T${hour}:00`;
    
    // End time is +1 hour
    const endHour = String((now.getHours() + 1) % 24).padStart(2, '0');
    const endStr = `${dateStr}T${endHour}:00`;
    
    try {
        document.getElementById("event-start").value = startStr;
        document.getElementById("event-end").value = endStr;
    } catch (e) {
        console.error("Error setting input values for datetime-local:", e);
        // Fallback: clear the inputs if the browser rejects the string pattern
        document.getElementById("event-start").value = "";
        document.getElementById("event-end").value = "";
    }
}

function closeAddEventModal() {
    document.getElementById("add-event-modal").classList.add("hidden");
    document.getElementById("event-form").reset();
}

function closeAddEventModalOnOverlay(event) {
    if (event.target === document.getElementById("add-event-modal")) {
        closeAddEventModal();
    }
}

async function handleCreateEvent(event) {
    event.preventDefault();
    
    const summary = document.getElementById("event-summary").value.trim();
    const description = document.getElementById("event-description").value.trim();
    const startTime = document.getElementById("event-start").value;
    const endTime = document.getElementById("event-end").value;
    
    // Check end time > start time
    if (new Date(endTime) <= new Date(startTime)) {
        alert("結束時間必須大於開始時間！");
        return;
    }
    
    const payload = {
        summary: summary,
        description: description,
        start_time: startTime,
        end_time: endTime
    };
    
    try {
        const response = await fetch("/api/calendar/events", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (response.ok) {
            showToast("新日程建立成功！");
            closeAddEventModal();
            fetchEvents();
        } else {
            showToast("建立日程失敗，請檢查設定與權限。");
        }
    } catch (error) {
        showToast("連線錯誤。");
    }
}

// --- SETTINGS MODAL & API SAVE ---

async function loadSettings() {
    try {
        const response = await fetch("/api/settings");
        if (response.ok) {
            const data = await response.json();
            state.settings = data;
            
            // Populating Google Settings Form & Status
            document.getElementById("google-client-id").value = data.google.client_id || "";
            document.getElementById("google-calendar-id").value = data.google.calendar_id || "primary";
            document.getElementById("google-drive-folder-id").value = data.google.drive_folder_id || "";
            document.getElementById("google-starting-address").value = data.google.starting_address || "";
            const gConnectedEl = document.getElementById("google-status-connected");
            const gDisconnectedEl = document.getElementById("google-status-disconnected");
            
            if (data.google.connected) {
                gConnectedEl.classList.remove("hidden");
                gDisconnectedEl.classList.add("hidden");
                document.getElementById("google-user-email").textContent = data.google.email || "已連結帳號";
                updateGoogleBadge(true);
            } else {
                gConnectedEl.classList.add("hidden");
                gDisconnectedEl.classList.remove("hidden");
                updateGoogleBadge(false);
            }
            
            // Populating Line Webhook & Settings Form & Status
            document.getElementById("line-webhook-url").value = data.line.webhook_url;
            document.getElementById("line-user-id").value = data.line.authorized_user_id || "";
            document.getElementById("gemini-api-key").value = data.line.gemini_api_key || "";
            
            const lConnectedEl = document.getElementById("line-status-connected");
            const lDisconnectedEl = document.getElementById("line-status-disconnected");
            const lineBadge = document.getElementById("status-line");
            
            if (data.line.token_configured && data.line.secret_configured) {
                lConnectedEl.classList.remove("hidden");
                lDisconnectedEl.classList.add("hidden");
                lineBadge.className = "status-badge connected";
                lineBadge.querySelector("span").textContent = "Line 遠端已啟用";
            } else {
                lConnectedEl.classList.add("hidden");
                lDisconnectedEl.classList.remove("hidden");
                lineBadge.className = "status-badge disconnected";
                lineBadge.querySelector("span").textContent = "Line 遠端未啟用";
            }
            
            // Dynamic Webhook details for setup instruction page
            document.getElementById("local-ip-address").textContent = window.location.origin;
            document.getElementById("google-redirect-uri-display").textContent = `${window.location.origin}/oauth2callback`;
        }
    } catch (error) {
        console.error("Failed to load settings:", error);
    }
}

async function handleSaveGoogleSettings(event) {
    event.preventDefault();
    const clientId = document.getElementById("google-client-id").value.trim();
    const clientSecret = document.getElementById("google-client-secret").value.trim();
    const calendarId = document.getElementById("google-calendar-id").value.trim();
    const driveFolderId = document.getElementById("google-drive-folder-id").value.trim();
    const startingAddress = document.getElementById("google-starting-address").value.trim();
    
    try {
        const response = await fetch("/api/settings/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                client_id: clientId, 
                client_secret: clientSecret, 
                calendar_id: calendarId,
                drive_folder_id: driveFolderId,
                starting_address: startingAddress
            })
        });
        if (response.ok) {
            const data = await response.json();
            showToast("正在導向至 Google 授權畫面...");
            // Redirect user to Google OAuth Concent Page
            setTimeout(() => {
                window.location.href = data.auth_url;
            }, 1000);
        } else {
            showToast("儲存 Google 設定失敗。");
        }
    } catch (error) {
        showToast("網路錯誤。");
    }
}

async function handleSaveLineSettings(event) {
    event.preventDefault();
    const token = document.getElementById("line-channel-token").value.trim();
    const secret = document.getElementById("line-channel-secret").value.trim();
    const userId = document.getElementById("line-user-id").value.trim();
    const geminiKey = document.getElementById("gemini-api-key").value.trim();
    
    try {
        const response = await fetch("/api/settings/line", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                channel_access_token: token,
                channel_secret: secret,
                authorized_line_user_id: userId,
                gemini_api_key: geminiKey
            })
        });
        if (response.ok) {
            showToast("Line 設定儲存成功！");
            loadSettings();
            // Clear inputs for security display
            document.getElementById("line-channel-token").value = "";
            document.getElementById("line-channel-secret").value = "";
            document.getElementById("gemini-api-key").value = "";
        } else {
            showToast("儲存 Line 設定失敗。");
        }
    } catch (error) {
        showToast("網路錯誤。");
    }
}

function copyWebhookUrl() {
    const urlInput = document.getElementById("line-webhook-url");
    urlInput.select();
    urlInput.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(urlInput.value);
    showToast("已將 Webhook 網址複製到剪貼簿！");
}

async function disconnectGoogle() {
    if (!confirm("確定要解除 Google 日曆的授權與設定嗎？")) return;
    try {
        const response = await fetch("/api/settings/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ client_id: "", client_secret: "" })
        });
        if (response.ok) {
            showToast("Google 帳號已解除授權。");
            loadSettings();
            fetchEvents();
        }
    } catch (error) {
        showToast("網路錯誤。");
    }
}

// Modal Toggle Functions
function openSettingsModal() {
    document.getElementById("settings-modal").classList.remove("hidden");
    loadSettings();
    loadServiceAccountEmail();
}

function closeSettingsModal() {
    document.getElementById("settings-modal").classList.add("hidden");
    document.getElementById("google-settings-form").reset();
    document.getElementById("line-settings-form").reset();
}

function closeSettingsModalOnOverlay(event) {
    if (event.target === document.getElementById("settings-modal")) {
        closeSettingsModal();
    }
}

// --- UTILITIES ---

function showToast(message) {
    const toast = document.getElementById("toast");
    const toastMsg = document.getElementById("toast-message");
    
    toastMsg.textContent = message;
    toast.classList.remove("hidden");
    
    // Clear old timer if running
    if (window.toastTimer) clearTimeout(window.toastTimer);
    
    window.toastTimer = setTimeout(() => {
        toast.classList.add("hidden");
    }, 3500);
}

function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

// Fullscreen API Helper
function toggleFullscreen() {
    const btn = document.getElementById("fullscreen-btn");
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen()
            .then(() => {
                if (btn) {
                    btn.innerHTML = '<i class="fa-solid fa-compress"></i> <span>視窗模式</span>';
                }
            })
            .catch(err => {
                showToast("無法啟動全螢幕模式：" + err.message);
            });
    } else {
        document.exitFullscreen()
            .then(() => {
                if (btn) {
                    btn.innerHTML = '<i class="fa-solid fa-expand"></i> <span>全螢幕</span>';
                }
            });
    }
}

// Sync fullscreen button status (in case user exits with ESC key)
document.addEventListener("fullscreenchange", () => {
    const btn = document.getElementById("fullscreen-btn");
    if (btn) {
        if (document.fullscreenElement) {
            btn.innerHTML = '<i class="fa-solid fa-compress"></i> <span>視窗模式</span>';
        } else {
            btn.innerHTML = '<i class="fa-solid fa-expand"></i> <span>全螢幕</span>';
        }
    }
    renderEvents();
});

// Helper to compare if two lists of events are equal
function areEventsEqual(ev1, ev2) {
    if (!ev1 || !ev2) return false;
    if (ev1.length !== ev2.length) return false;
    for (let i = 0; i < ev1.length; i++) {
        const e1 = ev1[i];
        const e2 = ev2[i];
        if (e1.id !== e2.id ||
            e1.summary !== e2.summary ||
            e1.description !== e2.description ||
            (e1.start?.dateTime || e1.start?.date) !== (e2.start?.dateTime || e2.start?.date) ||
            (e1.end?.dateTime || e1.end?.date) !== (e2.end?.dateTime || e2.end?.date)) {
            return false;
        }
    }
    return true;
}

// Helper to compare if two lists of todos are equal
function areTodosEqual(td1, td2) {
    if (!td1 || !td2) return false;
    if (td1.length !== td2.length) return false;
    for (let i = 0; i < td1.length; i++) {
        const t1 = td1[i];
        const t2 = td2[i];
        if (t1.id !== t2.id ||
            t1.title !== t2.title ||
            t1.priority !== t2.priority ||
            t1.due_date !== t2.due_date ||
            t1.completed !== t2.completed) {
            return false;
        }
    }
    return true;
}

// Fetch the service account email from backend to display it
async function loadServiceAccountEmail() {
    try {
        const response = await fetch("/api/settings/service_account_email");
        if (response.ok) {
            const data = await response.json();
            const displayEl = document.getElementById("service-account-email-display");
            if (displayEl) {
                displayEl.textContent = data.email || "未設定 Service Account 憑證，請聯絡系統管理員設定 GOOGLE_SERVICE_ACCOUNT_JSON";
            }
        }
    } catch (e) {
        console.error("Failed to load service account email:", e);
    }
}

// Clock Collapse Logic
function toggleClockCollapse() {
    const header = document.querySelector(".dashboard-header");
    const miniClock = document.getElementById("mini-calendar-clock");
    const btn = document.getElementById("clock-toggle-btn");
    
    if (!header) return;
    const isCollapsed = header.classList.toggle("header-collapsed");
    
    if (isCollapsed) {
        if (miniClock) miniClock.classList.remove("hidden");
        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-eye"></i> <span>顯示時鐘</span>';
        }
        localStorage.setItem("clock_collapsed", "true");
    } else {
        if (miniClock) miniClock.classList.add("hidden");
        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-eye-slash"></i> <span>隱藏時鐘</span>';
        }
        localStorage.setItem("clock_collapsed", "false");
    }
}

function initClockCollapseState() {
    const collapsed = localStorage.getItem("clock_collapsed");
    if (collapsed === "true") {
        const header = document.querySelector(".dashboard-header");
        const miniClock = document.getElementById("mini-calendar-clock");
        const btn = document.getElementById("clock-toggle-btn");
        
        if (header) header.classList.add("header-collapsed");
        if (miniClock) miniClock.classList.remove("hidden");
        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-eye"></i> <span>顯示時鐘</span>';
        }
    }
}
