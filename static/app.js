// Global State
function getApiUrl(path) {
    if (!path) return "";
    if (path.startsWith("http://") || path.startsWith("https://")) {
        return path;
    }
    let origin = window.location.origin;
    if (!origin || origin === "null" || origin.startsWith("file:")) {
        origin = "http://127.0.0.1:8000";
    }
    return origin + (path.startsWith("/") ? path : "/" + path);
}

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
    initChatbotApp();
    
    // Instantly sync data when the user focuses the tab or wakes up the tablet screen
    window.addEventListener("focus", () => {
        if (state.loggedIn) {
            fetchTodos(false);
            fetchEvents(false);
        }
    });
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
    state.hasUsers = true;
    state.loggedIn = true;
    state.username = "yuwei1112";
    
    const loginView = document.getElementById("login-view");
    const dashboardView = document.getElementById("dashboard-view");
    
    if (loginView) loginView.classList.add("hidden");
    if (dashboardView) dashboardView.classList.remove("hidden");
    
    const userDisplayNameEl = document.getElementById("user-display-name");
    if (userDisplayNameEl) {
        userDisplayNameEl.textContent = state.username;
    }
    
    renderMiniCalendar();
    await loadSettings();
    await fetchTodos();
    await fetchEvents();
    
    // Start background sync every 10 seconds for real-time updates without flickering
    if (state.syncInterval) clearInterval(state.syncInterval);
    state.syncInterval = setInterval(() => {
        fetchTodos(false); // fetch silently without resetting UI state
        fetchEvents(false);
    }, 10000);
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
        if (response.status === 401) {
            checkAuthStatus();
            return;
        }
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
    
    // Render all todos directly without category filter buttons
    const filteredTodos = state.todos || [];
    
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
        const status = response.status;
        const text = await response.text();

        if (status === 401) {
            checkAuthStatus();
            return;
        }
        
        const data = JSON.parse(text);
        
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
        fetch('/api/debug/js-error', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: `CAUGHT EXCEPTION in fetchEvents: ${error.message || error}`,
                source: 'fetchEvents',
                lineno: 0,
                colno: 0,
                stack: error.stack || ''
            })
        }).catch(() => {});
    }
}

function updateGoogleBadge(isConnected) {
    const badge = document.getElementById("status-google");
    if (!badge) return;
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
            else if (inside.includes("出準") || inside.includes("ChuZhun")) type = "出準";
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
    try {
        const container = document.getElementById("mini-calendar-days");
        const monthYearLabel = document.getElementById("mini-calendar-month-year");
        container.innerHTML = "";
        
        // Remote JS state reporting for debugging
        try {
            const jul3 = new Date(2026, 6, 3);
            const jul3Events = getEventsOnDay(jul3);
            fetch('/api/debug/js-error', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `DEBUG: state.events count = ${state.events ? state.events.length : 'null'}. Jul 3 events = ${jul3Events.length}. selectedDate = ${state.selectedDate ? state.selectedDate.toDateString() : 'null'}. currentCalendarMonth = ${state.currentCalendarMonth ? state.currentCalendarMonth.toDateString() : 'null'}.`,
                    source: 'renderMiniCalendar',
                    lineno: 0,
                    colno: 0,
                    stack: state.events ? JSON.stringify(state.events.slice(0, 2)) : ''
                })
            }).catch(() => {});
        } catch(e) {}
        
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
            
            dayDiv.onclick = () => {
                state.selectedDate = thisDate;
                renderMiniCalendar();
                renderEvents();
                openInlineCardForDate(thisDate);
            };
            
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
        
        // Renders next month padded days (fill grid to complete the week)
        const totalCells = firstDay + totalDays;
        const nextPad = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
        const totalWeeks = (totalCells + nextPad) / 7;
        // Set dynamic class for CSS to adjust row height
        container.classList.remove('weeks-4', 'weeks-5', 'weeks-6');
        container.classList.add('weeks-' + totalWeeks);
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
    } catch (error) {
        console.error("Error in renderMiniCalendar:", error);
        fetch('/api/debug/js-error', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: `CAUGHT EXCEPTION in renderMiniCalendar: ${error.message || error}`,
                source: 'renderMiniCalendar',
                lineno: 0,
                colno: 0,
                stack: error.stack || ''
            })
        }).catch(() => {});
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
    try {
        const listEl = document.getElementById("events-list");
        const emptyEl = document.getElementById("events-list-empty");
        const eventsContainer = document.querySelector('.events-timeline');
        const todoContainer = document.querySelector('.todo-card');
        listEl.innerHTML = "";

        const now = new Date();
        const isSelectedDateToday = state.selectedDate.toDateString() === now.toDateString();

        // Filter events for selected day
        const events = state.events || [];
        const dayEvents = events.filter(event => {
            if (!event || !event.start) return false;
            const startStr = event.start.dateTime || event.start.date;
            if (!startStr) return false;
            const eventStartDate = new Date(startStr);
            if (eventStartDate.toDateString() !== state.selectedDate.toDateString()) {
                return false;
            }

            // Keep all events of the selected day visible on the electronic signage
            return true;
        });

        // Always keep both upper and lower split card sections visible
        eventsContainer.classList.remove('hidden');
        todoContainer.classList.remove('hidden');

        if (dayEvents.length === 0) {
            emptyEl.classList.remove('hidden');
        } else {
            emptyEl.classList.add('hidden');
            renderEventsList(dayEvents, listEl);
        }
    } catch (error) {
        console.error("Error in renderEvents:", error);
        fetch('/api/debug/js-error', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: `CAUGHT EXCEPTION in renderEvents: ${error.message || error}`,
                source: 'renderEvents',
                lineno: 0,
                colno: 0,
                stack: error.stack || ''
            })
        }).catch(() => {});
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
    const modalInput = document.getElementById("modal-ai-input");
    if (modalInput) modalInput.value = "";
    const modalStatus = document.getElementById("modal-ai-status");
    if (modalStatus) {
        modalStatus.classList.add("hidden");
        modalStatus.innerHTML = "";
    }
}

function closeAddEventModalOnOverlay(event) {
    if (event.target === document.getElementById("add-event-modal")) {
        closeAddEventModal();
    }
}

// --- AI NATURAL LANGUAGE CALENDAR PARSER & VOICE RECOGNITION ---

let currentRecognition = null;
let currentListeningBtnId = null;

function toggleVoiceInput(inputId, micBtnId, onCompleteCallback) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showToast("您的瀏覽器尚不支援原生語音辨識，請使用 Chrome/Edge 瀏覽器或直接打字。");
        return;
    }

    const inputElem = document.getElementById(inputId);
    const btnElem = document.getElementById(micBtnId);
    if (!inputElem || !btnElem) return;

    if (currentRecognition && currentListeningBtnId === micBtnId) {
        try {
            currentRecognition.stop();
        } catch (e) {}
        currentRecognition = null;
        currentListeningBtnId = null;
        btnElem.classList.remove("recording");
        showToast("已停止語音辨識");
        return;
    }

    if (currentRecognition) {
        try { currentRecognition.stop(); } catch(e) {}
        if (currentListeningBtnId) {
            const oldBtn = document.getElementById(currentListeningBtnId);
            if (oldBtn) oldBtn.classList.remove("recording");
        }
    }

    try {
        const recognition = new SpeechRecognition();
        recognition.lang = 'zh-TW';
        recognition.interimResults = true;
        recognition.continuous = false;

        currentRecognition = recognition;
        currentListeningBtnId = micBtnId;
        btnElem.classList.add("recording");
        showToast("🎤 請開始說話（例：「8月20號下午2點到4點個案訪視」）...");

        recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            if (transcript) {
                inputElem.value = transcript;
            }
        };

        recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            btnElem.classList.remove("recording");
            currentRecognition = null;
            currentListeningBtnId = null;
            if (event.error !== 'no-speech') {
                showToast("語音辨識發生錯誤：" + event.error);
            }
        };

        recognition.onend = () => {
            btnElem.classList.remove("recording");
            currentRecognition = null;
            currentListeningBtnId = null;
            if (inputElem.value.trim() && typeof onCompleteCallback === 'function') {
                onCompleteCallback();
            }
        };

        recognition.start();
    } catch (err) {
        console.error("Failed to start speech recognition:", err);
        btnElem.classList.remove("recording");
        showToast("無法開啟語音功能：" + err.message);
    }
}

async function fetchEvents(showLoading = true) {
    const disconnectedEl = document.getElementById("calendar-disconnected-state");
    const connectedEl = document.getElementById("calendar-connected-state");
    
    try {
        const response = await fetch("/api/calendar/events");
        const status = response.status;
        const text = await response.text();

        if (status === 401) {
            checkAuthStatus();
            return;
        }
        
        const data = JSON.parse(text);
        const newEvents = data.items || data.events || [];

        if (data.error === "not_authorized" || data.error === "unauthorized_by_google") {
            updateGoogleBadge(false);
            if (newEvents.length > 0) {
                if (disconnectedEl) disconnectedEl.classList.add("hidden");
                if (connectedEl) connectedEl.classList.remove("hidden");
            } else {
                if (disconnectedEl) disconnectedEl.classList.remove("hidden");
                if (connectedEl) connectedEl.classList.add("hidden");
            }
        } else {
            if (disconnectedEl) disconnectedEl.classList.add("hidden");
            if (connectedEl) connectedEl.classList.remove("hidden");
            updateGoogleBadge(true);
        }

        if (!areEventsEqual(state.events, newEvents)) {
            state.events = newEvents;
            renderMiniCalendar();
            renderEvents();
        }
    } catch (error) {
        console.error("Failed to fetch calendar events:", error);
    }
}

async function parseCalendarTextAPI(text) {
    const response = await fetch("/api/calendar/parse-event", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            text: text,
            client_now: new Date().toISOString()
        })
    });
    if (!response.ok) {
        throw new Error("API call failed");
    }
    return await response.json();
}

let currentInlineParsedEvents = [];
let liveParseTimer = null;

function closeInlineSmartCard() {
    const card = document.getElementById("inline-smart-schedule-card");
    if (card) card.classList.add("hidden");
}

function openInlineCardForDate(targetDate) {
    const card = document.getElementById("inline-smart-schedule-card");
    if (!card) return;
    
    card.classList.remove("hidden");
    const summaryInput = document.getElementById("inline-event-summary");
    const startInput = document.getElementById("inline-event-start");
    const endInput = document.getElementById("inline-event-end");
    
    if (summaryInput && (!summaryInput.value || summaryInput.value === "未命名行程")) {
        summaryInput.value = "個案訪視";
    }
    
    const y = targetDate.getFullYear();
    const m = String(targetDate.getMonth() + 1).padStart(2, '0');
    const d = String(targetDate.getDate()).padStart(2, '0');
    
    if (startInput) startInput.value = `${y}-${m}-${d}T14:00`;
    if (endInput) endInput.value = `${y}-${m}-${d}T15:00`;
    
    currentInlineParsedEvents = [{
        summary: summaryInput ? summaryInput.value : "個案訪視",
        start_time: `${y}-${m}-${d}T14:00:00`,
        end_time: `${y}-${m}-${d}T15:00:00`
    }];
}

function handleAIInputLive(val) {
    if (!val || val.trim().length < 3) return;
    if (liveParseTimer) clearTimeout(liveParseTimer);
    
    liveParseTimer = setTimeout(async () => {
        try {
            const parsedData = await parseCalendarTextAPI(val.trim());
            const eventsList = parsedData.events || [parsedData];
            if (eventsList.length > 0) {
                currentInlineParsedEvents = eventsList;
                const card = document.getElementById("inline-smart-schedule-card");
                if (card) card.classList.remove("hidden");
                
                const firstEv = eventsList[0] || {};
                const summaryInput = document.getElementById("inline-event-summary");
                const startInput = document.getElementById("inline-event-start");
                const endInput = document.getElementById("inline-event-end");
                
                if (summaryInput) summaryInput.value = firstEv.summary || "行程";
                if (startInput && firstEv.start_time) startInput.value = firstEv.start_time.substring(0, 16);
                if (endInput && firstEv.end_time) endInput.value = firstEv.end_time.substring(0, 16);
            }
        } catch (e) {}
    }, 800);
}

async function submitDashboardAIEvent() {
    const inputElem = document.getElementById("dashboard-ai-event-input");
    const statusElem = document.getElementById("dashboard-ai-event-status");
    const submitBtn = document.getElementById("dashboard-ai-submit-btn");
    const card = document.getElementById("inline-smart-schedule-card");
    if (!inputElem) return;

    const text = inputElem.value.trim();
    if (!text) {
        showToast("請先輸入或語音說出要新增的行程內容！");
        inputElem.focus();
        return;
    }

    if (statusElem) {
        statusElem.classList.remove("hidden");
        statusElem.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> AI 智控解析中...`;
    }
    if (submitBtn) submitBtn.disabled = true;

    try {
        const parsedData = await parseCalendarTextAPI(text);
        const eventsList = parsedData.events || [parsedData];
        currentInlineParsedEvents = eventsList;

        if (card) card.classList.remove("hidden");

        const firstEv = eventsList[0] || {};
        const summaryInput = document.getElementById("inline-event-summary");
        const startInput = document.getElementById("inline-event-start");
        const endInput = document.getElementById("inline-event-end");
        const batchContainer = document.getElementById("inline-batch-preview");

        if (summaryInput) summaryInput.value = firstEv.summary || "行程";
        if (startInput && firstEv.start_time) startInput.value = firstEv.start_time.substring(0, 16);
        if (endInput && firstEv.end_time) endInput.value = firstEv.end_time.substring(0, 16);

        if (batchContainer) {
            if (eventsList.length > 1) {
                batchContainer.classList.remove("hidden");
                let batchHtml = `<div style="font-size:0.8rem; font-weight:600; color:#4f46e5; margin-bottom:4px;">✨ 已自動分拆 ${eventsList.length} 筆獨立行程：</div><ul style="margin:0; padding-left:18px; font-size:0.78rem;">`;
                eventsList.forEach(ev => {
                    const s = ev.start_time ? ev.start_time.replace('T', ' ').substring(0, 16) : '';
                    batchHtml += `<li><strong>${ev.summary}</strong> (${s})</li>`;
                });
                batchHtml += `</ul>`;
                batchContainer.innerHTML = batchHtml;
            } else {
                batchContainer.classList.add("hidden");
                batchContainer.innerHTML = "";
            }
        }

        if (statusElem) {
            statusElem.innerHTML = `<span style="color:#10b981;"><i class="fa-solid fa-circle-check"></i> 解析完成！請於下方卡片核對後建立。</span>`;
        }
        showToast("✨ 已開啟即時智控卡片，請核對後建立！");
    } catch (err) {
        console.error("Dashboard AI event error:", err);
        showToast("AI 判讀失敗，請確認網路與金鑰。");
        if (statusElem) {
            statusElem.innerHTML = `<span style="color:#ef4444;"><i class="fa-solid fa-circle-xmark"></i> 解析失敗</span>`;
        }
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

async function confirmSaveInlineSmartCard() {
    const card = document.getElementById("inline-smart-schedule-card");
    const summaryInput = document.getElementById("inline-event-summary");
    const startInput = document.getElementById("inline-event-start");
    const endInput = document.getElementById("inline-event-end");
    const confirmBtn = document.getElementById("inline-confirm-submit-btn");

    let eventsToSave = [];
    if (currentInlineParsedEvents.length > 1) {
        eventsToSave = currentInlineParsedEvents;
    } else {
        const sVal = summaryInput ? summaryInput.value.trim() : "行程";
        const stVal = startInput ? startInput.value : "";
        const etVal = endInput ? endInput.value : "";

        if (!stVal) {
            showToast("請選擇開始時間！");
            return;
        }
        eventsToSave = [{
            summary: sVal || "行程",
            start_time: stVal.length === 16 ? stVal + ":00" : stVal,
            end_time: etVal.length === 16 ? etVal + ":00" : (etVal || stVal + ":00")
        }];
    }

    if (confirmBtn) confirmBtn.disabled = true;

    try {
        const payload = { events: eventsToSave };
        const createRes = await fetch("/api/calendar/events", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (createRes.ok) {
            const resData = await createRes.json();
            const count = resData.count || eventsToSave.length;
            showToast(`✨ 成功將 ${count} 筆行程寫入 Google 日曆與本機！`);
            
            const inputElem = document.getElementById("dashboard-ai-event-input");
            if (inputElem) inputElem.value = "";
            const statusElem = document.getElementById("dashboard-ai-event-status");
            if (statusElem) statusElem.classList.add("hidden");
            
            closeInlineSmartCard();
            fetchEvents();
        } else {
            const errText = await createRes.text();
            showToast(`建立失敗：${errText}`);
        }
    } catch (err) {
        console.error("Save inline smart card error:", err);
        showToast("寫入日曆失敗，請重試。");
    } finally {
        if (confirmBtn) confirmBtn.disabled = false;
    }
}

function applyInlineTimeChip(chipType) {
    const startInput = document.getElementById("inline-event-start");
    const endInput = document.getElementById("inline-event-end");
    if (!startInput || !endInput) return;

    const startDt = new Date();
    const endDt = new Date();

    if (chipType === 'today-pm') {
        startDt.setHours(14, 0, 0, 0);
        endDt.setHours(15, 0, 0, 0);
    } else if (chipType === 'tomorrow-am') {
        startDt.setDate(startDt.getDate() + 1);
        startDt.setHours(9, 0, 0, 0);
        endDt.setDate(endDt.getDate() + 1);
        endDt.setHours(10, 0, 0, 0);
    } else if (chipType === 'tomorrow-pm') {
        startDt.setDate(startDt.getDate() + 1);
        startDt.setHours(14, 0, 0, 0);
        endDt.setDate(endDt.getDate() + 1);
        endDt.setHours(15, 0, 0, 0);
    } else if (chipType === 'next-mon-am') {
        const day = startDt.getDay();
        const diff = (day === 0 ? 1 : 8 - day);
        startDt.setDate(startDt.getDate() + diff);
        startDt.setHours(9, 0, 0, 0);
        endDt.setDate(endDt.getDate() + diff);
        endDt.setHours(10, 0, 0, 0);
    }

    const formatDt = (d) => {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hh = String(d.getHours()).padStart(2, '0');
        const mm = String(d.getMinutes()).padStart(2, '0');
        return `${y}-${m}-${day}T${hh}:${mm}`;
    };

    startInput.value = formatDt(startDt);
    endInput.value = formatDt(endDt);
    showToast("已更新時間！");
}

async function parseModalAIInput() {
    const inputElem = document.getElementById("modal-ai-input");
    const statusElem = document.getElementById("modal-ai-status");
    const parseBtn = document.getElementById("modal-ai-parse-btn");
    if (!inputElem) return;

    const text = inputElem.value.trim();
    if (!text) {
        showToast("請輸入欲解析的行程敘述（如「8/20到8/22每天下午2點開會」）");
        inputElem.focus();
        return;
    }

    if (statusElem) {
        statusElem.classList.remove("hidden");
        statusElem.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> AI 判讀拆分中...`;
    }
    if (parseBtn) parseBtn.disabled = true;

    try {
        const parsed = await parseCalendarTextAPI(text);
        const eventsList = parsed.events || [parsed];
        const firstEv = eventsList[0];

        document.getElementById("event-summary").value = firstEv.summary || "";
        if (firstEv.description) {
            document.getElementById("event-description").value = firstEv.description;
        }
        if (firstEv.start_time) {
            document.getElementById("event-start").value = firstEv.start_time.substring(0, 16);
        }
        if (firstEv.end_time) {
            document.getElementById("event-end").value = firstEv.end_time.substring(0, 16);
        }

        if (statusElem) {
            if (eventsList.length > 1) {
                statusElem.innerHTML = `
                    <div class="ai-parse-success-badge">
                        <i class="fa-solid fa-circle-check"></i>
                        <span>已自動拆分為 <strong>${eventsList.length} 筆行程</strong>！點擊儲存將一次全數建立。</span>
                    </div>
                `;
            } else {
                const sDate = firstEv.start_time.split("T")[0];
                const sTime = firstEv.start_time.split("T")[1].substring(0, 5);
                const eTime = firstEv.end_time.split("T")[1].substring(0, 5);
                statusElem.innerHTML = `
                    <div class="ai-parse-success-badge">
                        <i class="fa-solid fa-circle-check"></i>
                        <span>已自動填入：<strong>${firstEv.summary}</strong> (${sDate} ${sTime} ~ ${eTime})</span>
                    </div>
                `;
            }
        }
        showToast(`AI 判讀成功！已解析 ${eventsList.length} 筆行程。`);
    } catch (err) {
        console.error("Modal AI parse error:", err);
        showToast("AI 解析失敗，請確認輸入內容。");
        if (statusElem) {
            statusElem.innerHTML = `<span style="color:#ef4444;"><i class="fa-solid fa-circle-xmark"></i> 解析失敗</span>`;
        }
    } finally {
        if (parseBtn) parseBtn.disabled = false;
    }
}

function openAddEventModalWithParsed(parsed) {
    openAddEventModal();
    if (parsed) {
        const eventsList = parsed.events || [parsed];
        const firstEv = eventsList[0];
        if (firstEv.summary) document.getElementById("event-summary").value = firstEv.summary;
        if (firstEv.description) document.getElementById("event-description").value = firstEv.description;
        if (firstEv.start_time) document.getElementById("event-start").value = firstEv.start_time.substring(0, 16);
        if (firstEv.end_time) document.getElementById("event-end").value = firstEv.end_time.substring(0, 16);
        
        const statusElem = document.getElementById("modal-ai-status");
        if (statusElem && parsed.summary) {
            statusElem.classList.remove("hidden");
            const sDate = parsed.start_time.split("T")[0];
            const sTime = parsed.start_time.split("T")[1].substring(0, 5);
            const eTime = parsed.end_time.split("T")[1].substring(0, 5);
            statusElem.innerHTML = `
                <div class="ai-parse-success-badge">
                    <i class="fa-solid fa-circle-check"></i>
                    <span>已自動填入：<strong>${parsed.summary}</strong> (${sDate} ${sTime} ~ ${eTime})</span>
                </div>
            `;
        }
    }
}

function applyTimeChip(chipType) {
    const startDt = new Date();
    const endDt = new Date();

    if (chipType === 'today-pm') {
        startDt.setHours(14, 0, 0, 0);
        endDt.setHours(15, 0, 0, 0);
    } else if (chipType === 'tomorrow-am') {
        startDt.setDate(startDt.getDate() + 1);
        startDt.setHours(9, 0, 0, 0);
        endDt.setDate(endDt.getDate() + 1);
        endDt.setHours(10, 0, 0, 0);
    } else if (chipType === 'tomorrow-pm') {
        startDt.setDate(startDt.getDate() + 1);
        startDt.setHours(14, 0, 0, 0);
        endDt.setDate(endDt.getDate() + 1);
        endDt.setHours(15, 0, 0, 0);
    } else if (chipType === 'next-mon-am') {
        const day = startDt.getDay();
        const diff = (day === 0 ? 1 : 8 - day);
        startDt.setDate(startDt.getDate() + diff);
        startDt.setHours(9, 0, 0, 0);
        endDt.setDate(endDt.getDate() + diff);
        endDt.setHours(10, 0, 0, 0);
    }

    const formatISO = (dt) => {
        const y = dt.getFullYear();
        const m = String(dt.getMonth() + 1).padStart(2, '0');
        const d = String(dt.getDate()).padStart(2, '0');
        const h = String(dt.getHours()).padStart(2, '0');
        const min = String(dt.getMinutes()).padStart(2, '0');
        return `${y}-${m}-${d}T${h}:${min}`;
    };

    document.getElementById("event-start").value = formatISO(startDt);
    document.getElementById("event-end").value = formatISO(endDt);
    showToast("已帶入快捷時間");
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
        if (response.status === 401) {
            checkAuthStatus();
            return;
        }
        if (response.ok) {
            const data = await response.json();
            state.settings = data;
            
            // Populating Google Settings Form & Status
            const gClientId = document.getElementById("google-client-id");
            if (gClientId) gClientId.value = data.google.client_id || "";
            const gCalId = document.getElementById("google-calendar-id");
            if (gCalId) gCalId.value = data.google.calendar_id || "primary";
            const gDriveId = document.getElementById("google-drive-folder-id");
            if (gDriveId) gDriveId.value = data.google.drive_folder_id || "";
            const gSaJson = document.getElementById("google-service-account-json");
            if (gSaJson) gSaJson.value = data.google.service_account_json || "";
            const gStartAddr = document.getElementById("google-starting-address");
            if (gStartAddr) gStartAddr.value = data.google.starting_address || "";
            const gConnectedEl = document.getElementById("google-status-connected");
            const gDisconnectedEl = document.getElementById("google-status-disconnected");
            
            if (data.google.connected) {
                if (gConnectedEl) gConnectedEl.classList.remove("hidden");
                if (gDisconnectedEl) gDisconnectedEl.classList.add("hidden");
                const emailEl = document.getElementById("google-user-email");
                if (emailEl) emailEl.textContent = data.google.email || "已連結帳號";
                updateGoogleBadge(true);
            } else {
                if (gConnectedEl) gConnectedEl.classList.add("hidden");
                if (gDisconnectedEl) gDisconnectedEl.classList.remove("hidden");
                updateGoogleBadge(false);
            }
            
            // Populating Line Webhook & Settings Form & Status
            const lineWebhookEl = document.getElementById("line-webhook-url");
            if (lineWebhookEl) lineWebhookEl.value = data.line.webhook_url;
            const lineUserIdEl = document.getElementById("line-user-id");
            if (lineUserIdEl) lineUserIdEl.value = data.line.authorized_user_id || "";
            
            const geminiInput = document.getElementById("gemini-api-key");
            const geminiHint = document.getElementById("gemini-key-hint");
            if (geminiInput) {
                geminiInput.value = data.line.gemini_api_key || "";
            }
            if (geminiHint) {
                const currentKey = (data.line.gemini_api_key || "").trim();
                if (currentKey) {
                    const masked = currentKey.length > 10 ? (currentKey.substring(0, 6) + "..." + currentKey.substring(currentKey.length - 4)) : "已設定";
                    geminiHint.textContent = `目前金鑰：${masked} (支援個案自然語言建檔、行程排定與照護計畫分析)`;
                } else {
                    geminiHint.textContent = "尚未設定 API 金鑰，請貼上以啟用 AI 智能解析模組";
                }
            }
            
            const lConnectedEl = document.getElementById("line-status-connected");
            const lDisconnectedEl = document.getElementById("line-status-disconnected");
            const lineBadge = document.getElementById("status-line");
            
            if (data.line.token_configured && data.line.secret_configured) {
                if (lConnectedEl) lConnectedEl.classList.remove("hidden");
                if (lDisconnectedEl) lDisconnectedEl.classList.add("hidden");
                if (lineBadge) {
                    lineBadge.className = "status-badge connected";
                    lineBadge.querySelector("span").textContent = "Line 遠端已啟用";
                }
            } else {
                if (lConnectedEl) lConnectedEl.classList.add("hidden");
                if (lDisconnectedEl) lDisconnectedEl.classList.remove("hidden");
                if (lineBadge) {
                    lineBadge.className = "status-badge disconnected";
                    lineBadge.querySelector("span").textContent = "Line 遠端未啟用";
                }
            }
            
            // Dynamic Webhook details for setup instruction page
            const localIpEl = document.getElementById("local-ip-address");
            if (localIpEl) localIpEl.textContent = window.location.origin;
            const redirectUriEl = document.getElementById("google-redirect-uri-display");
            if (redirectUriEl) redirectUriEl.textContent = `${window.location.origin}/oauth2callback`;
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
    const serviceAccountJson = document.getElementById("google-service-account-json").value.trim();
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
                starting_address: startingAddress,
                service_account_json: serviceAccountJson
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
        } else {
            showToast("儲存 Line 設定失敗。");
        }
    } catch (error) {
        showToast("網路錯誤。");
    }
}

async function handleSaveGeminiKey(event) {
    event.preventDefault();
    const geminiKey = document.getElementById("gemini-api-key").value.trim();
    if (!geminiKey) {
        showToast("請輸入 Gemini API 金鑰！");
        return;
    }
    
    // Check if key is a valid format (Google now supports both new AQ. and legacy AIza keys)
    const isNewFormat = geminiKey.startsWith("AQ.");
    const isLegacyFormat = geminiKey.startsWith("AIza");
    if (!isNewFormat && !isLegacyFormat && !geminiKey.includes(",")) {
        if (!confirm("⚠️ 偵測到此金鑰格式通常不是 Google 官方 API Key (標準格式以 'AQ.' 或 'AIza' 開頭)。\n\n您確定要儲存此金鑰嗎？")) {
            return;
        }
    }
    
    try {
        const response = await fetch("/api/settings/gemini", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ gemini_api_key: geminiKey })
        });
        if (response.ok) {
            showToast("✨ Gemini API 金鑰已成功儲存並生效！");
            loadSettings();
        } else {
            showToast("儲存 Gemini API 金鑰失敗。");
        }
    } catch (error) {
        showToast("網路連線錯誤。");
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
    const btnInline = document.getElementById("fullscreen-btn-inline");
    if (document.fullscreenElement) {
        if (btn) btn.innerHTML = '<i class="fa-solid fa-compress"></i> <span>視窗模式</span>';
        if (btnInline) btnInline.innerHTML = '<i class="fa-solid fa-compress"></i> <span>視窗模式</span>';
    } else {
        if (btn) btn.innerHTML = '<i class="fa-solid fa-expand"></i> <span>全螢幕</span>';
        if (btnInline) btnInline.innerHTML = '<i class="fa-solid fa-expand"></i> <span>全螢幕</span>';
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
    // Force reset any collapse states so the header clock is always visible
    localStorage.removeItem("clock_collapsed");
    const header = document.querySelector(".dashboard-header");
    if (header) header.classList.remove("header-collapsed");
    const miniClock = document.getElementById("mini-calendar-clock");
    if (miniClock) miniClock.classList.add("hidden");
}

// ==========================================
// Standalone Software & AI Chatbot Logic
// ==========================================

let currentActiveState = null;

function initChatbotApp() {
    initSidebarCaseSearch();
    fetchChatSession();
}

function switchWorktab(tabName) {
    const btnBuilder = document.getElementById("tab-btn-builder");
    const btnAgenda = document.getElementById("tab-btn-agenda");
    const paneBuilder = document.getElementById("pane-case-builder");
    const paneAgenda = document.getElementById("pane-agenda");
    
    if (tabName === "builder") {
        if (btnBuilder) btnBuilder.classList.add("active");
        if (btnAgenda) btnAgenda.classList.remove("active");
        if (paneBuilder) paneBuilder.classList.remove("hidden");
        if (paneAgenda) paneAgenda.classList.add("hidden");
    } else {
        if (btnAgenda) btnAgenda.classList.add("active");
        if (btnBuilder) btnBuilder.classList.remove("active");
        if (paneAgenda) paneAgenda.classList.remove("hidden");
        if (paneBuilder) paneBuilder.classList.add("hidden");
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme") || (document.body && document.body.getAttribute("data-theme")) || "light";
    const themeIcon = document.getElementById("theme-icon");
    if (currentTheme === "dark") {
        document.documentElement.setAttribute("data-theme", "light");
        if (document.body) document.body.setAttribute("data-theme", "light");
        if (themeIcon) themeIcon.className = "fa-solid fa-moon";
        localStorage.setItem("app_theme", "light");
    } else {
        document.documentElement.setAttribute("data-theme", "dark");
        if (document.body) document.body.setAttribute("data-theme", "dark");
        if (themeIcon) themeIcon.className = "fa-solid fa-sun";
        localStorage.setItem("app_theme", "dark");
    }
}

// Restore saved theme on page load (Default to Light theme)
const savedTheme = localStorage.getItem("app_theme") || "light";
document.documentElement.setAttribute("data-theme", savedTheme);
document.addEventListener("DOMContentLoaded", () => {
    if (document.body) document.body.setAttribute("data-theme", savedTheme);
    const themeIcon = document.getElementById("theme-icon");
    if (themeIcon) themeIcon.className = savedTheme === "dark" ? "fa-solid fa-sun" : "fa-solid fa-moon";
    
    // Restore saved workstation sidebar collapse states
    const wsContainer = document.querySelector(".workstation-container");
    if (wsContainer) {
        if (localStorage.getItem("ws_left_collapsed") === "1") {
            wsContainer.classList.add("left-collapsed");
        }
        if (localStorage.getItem("ws_right_collapsed") === "1") {
            wsContainer.classList.add("right-collapsed");
            const headerBtn = document.getElementById("btn-toggle-ai-header");
            if (headerBtn) {
                const textSpan = headerBtn.querySelector(".ai-toggle-text");
                if (textSpan) textSpan.textContent = "展開 AI";
            }
        }
    }
});

async function fetchChatSession() {
    try {
        const res = await fetch(getApiUrl("/api/chat/session"));
        if (res.ok) {
            const data = await res.json();
            if (data.state) {
                updateFormFromState(data.state, true);
                if (data.state._history && Array.isArray(data.state._history) && data.state._history.length > 0) {
                    renderChatHistory(data.state._history);
                }
            }
            loadSidebarResidentCards();
        }
    } catch (e) {
        console.error("Failed to fetch chat session:", e);
    }
}

function updateFormFromState(st, force = false) {
    if (!st) return;
    if (force || !currentActiveState) {
        currentActiveState = st;
    }
    
    // Update Badge & Top Metric Cards
    const badgeText = document.getElementById("case-badge-text");
    if (badgeText) {
        const cName = st.name || "未提供資料";
        const cmsLvl = st.cmsLvl ? ` | CMS ${st.cmsLvl}級` : "";
        badgeText.textContent = `目前個案：${cName}${cmsLvl}`;
    }
    
    const metricName = document.getElementById("metric-case-name");
    const metricCms = document.getElementById("metric-cms-level");
    const metricTraf = document.getElementById("metric-fee-estimate");
    const metricDate = document.getElementById("metric-visit-date");
    
    if (metricName) metricName.textContent = st.name || "未加載個案";
    if (metricCms) metricCms.textContent = st.cmsLvl ? `第 ${st.cmsLvl} 級` : "未設定";
    if (metricTraf) metricTraf.textContent = (st.address && st.address.includes("中壢")) || String(st.trafLvl) === "2" ? "特定區 (2區)" : "一般區 (1區)";
    if (metricDate) metricDate.textContent = st.visitDate || "未排定";
    
    // Helper to safely set value and trigger pulse glow
    function setFieldVal(id, val) {
        const el = document.getElementById(id);
        if (!el) return;
        // DO NOT overwrite if user has already typed a value locally, unless forced
        if (!force && el.value && el.value.trim() !== "") return;
        
        let newVal = (val !== null && val !== undefined && val !== "未提供資料") ? String(val).trim() : "";
        
        // Auto-convert 4-digit western year (e.g. 1948) to ROC year (e.g. 37)
        if (id === "cb-birthYear" && newVal && !isNaN(newVal) && parseInt(newVal) > 1900) {
            newVal = String(parseInt(newVal) - 1911);
        }
        
        // Normalize for select dropdowns
        if (el.tagName === "SELECT") {
            if (id === "cb-planType") {
                const map = { "複評": "ReEval", "AA01": "AA01", "出準": "ChuZhun", "新案": "NewCase", "共訪": "CoVisit", "異動": "PlanChange", "私人": "Private" };
                for (let k in map) {
                    if (newVal.includes(k) || newVal === map[k]) {
                        newVal = map[k];
                        break;
                    }
                }
            } else if (id === "cb-statusVal") {
                if (newVal.includes("一般") || newVal === "1" || newVal.includes("3")) newVal = "1";
                else if (newVal.includes("中低") || newVal === "2") newVal = "2";
                else if (newVal.includes("低收") || newVal === "3") newVal = "3";
            } else if (id === "cb-hasF") {
                newVal = (val === true || val === "true" || String(val).includes("是") || String(val).includes("有")) ? "true" : "false";
            } else if (id === "cb-cmsLvl") {
                const m = newVal.match(/\d/);
                if (m) newVal = m[0];
            } else if (id === "cb-trafLvl") {
                const m = newVal.match(/\d/);
                if (m) newVal = m[0];
                else if (st.address && st.address.includes("中壢")) newVal = "2";
            } else if (id === "cb-gender") {
                newVal = newVal.includes("女") ? "女" : "男";
            }
            
            // Check if newVal matches an option value; if not, try text matching
            let matched = false;
            for (let opt of el.options) {
                if (opt.value === newVal) {
                    el.value = newVal;
                    matched = true;
                    break;
                }
            }
            if (!matched && newVal) {
                for (let opt of el.options) {
                    if (opt.textContent.includes(newVal) || newVal.includes(opt.value)) {
                        el.value = opt.value;
                        matched = true;
                        break;
                    }
                }
            }
        } else {
            el.value = newVal;
        }
        
        el.classList.remove("field-highlight-glow");
        void el.offsetWidth; // trigger reflow
        el.classList.add("field-highlight-glow");
    }
    
    setFieldVal("cb-name", st.name);
    setFieldVal("cb-birthYear", st.birthYear);
    setFieldVal("cb-gender", st.gender);
    setFieldVal("cb-statusVal", st.statusVal);
    setFieldVal("cb-visitDate", st.visitDate);
    setFieldVal("cb-visitTime", st.visitTime);
    setFieldVal("cb-address", st.address);
    setFieldVal("cb-planType", st.planType);
    setFieldVal("cb-cmsLvl", st.cmsLvl);
    setFieldVal("cb-trafLvl", st.trafLvl);
    setFieldVal("cb-hasF", String(st.hasF));
    setFieldVal("cb-livingStr", st.livingStr);
    setFieldVal("cb-burdenStr", st.burdenStr);
    setFieldVal("cb-specialistName", st.specialistName);
    
    // Render modern interactive services & calculate real-time quotas
    renderInteractiveServices();
    updateQuotaDisplay();
}

// --- INTERACTIVE SERVICE CODES & REAL-TIME QUOTA CALCULATOR ---

const LTC_SERVICES_DICT = {
    "BA01": { desc: "基本身體清潔", price: 260, type: "BC" },
    "BA02": { desc: "基本日常照顧", price: 195, type: "BC" },
    "BA03": { desc: "測量生命徵象", price: 35, type: "BC" },
    "BA04": { desc: "協助進食或管灌", price: 130, type: "BC" },
    "BA05": { desc: "餐食照顧", price: 310, type: "BC" },
    "BA07": { desc: "協助沐浴及洗頭", price: 325, type: "BC" },
    "BA08": { desc: "足部照護", price: 500, type: "BC" },
    "BA09": { desc: "到宅沐浴車第一型", price: 2200, type: "BC" },
    "BA09a": { desc: "到宅沐浴車第二型", price: 2500, type: "BC" },
    "BA10": { desc: "翻身拍背", price: 155, type: "BC" },
    "BA11": { desc: "肢體關節活動", price: 195, type: "BC" },
    "BA12": { desc: "協助上下樓梯", price: 130, type: "BC" },
    "BA13": { desc: "陪同外出(每30分)", price: 195, type: "BC" },
    "BA14": { desc: "陪同就醫(每趟)", price: 685, type: "BC" },
    "BA15": { desc: "家務服務(每30分)", price: 195, type: "BC" },
    "BA16": { desc: "代購代領代送", price: 130, type: "BC" },
    "BA18": { desc: "安全看視(每30分)", price: 200, type: "BC" },
    "BA20": { desc: "陪伴服務(每30分)", price: 175, type: "BC" },
    "BA22": { desc: "巡視服務", price: 130, type: "BC" },
    "BA23": { desc: "協助洗頭", price: 200, type: "BC" },
    "BA24": { desc: "協助排泄", price: 220, type: "BC" },
    "CA08": { desc: "個別化服務計畫", price: 1500, type: "BC" },
    "CB01": { desc: "營養照護", price: 1500, type: "BC" },
    "CB02": { desc: "進食與吞嚥照護", price: 1500, type: "BC" },
    "CB03": { desc: "困擾行為照護", price: 1500, type: "BC" },
    "CB04": { desc: "臥床受限照護", price: 1500, type: "BC" },
    "CD02": { desc: "居家護理指導", price: 1500, type: "BC" },
    "GA09": { desc: "居家喘息服務2小時", price: 770, type: "G" },
    "GA03": { desc: "日照中心喘息全日", price: 1250, type: "G" },
    "GA04": { desc: "日照中心喘息半日", price: 625, type: "G" },
    "GA05": { desc: "機構住宿喘息全日", price: 2310, type: "G" }
};

const CMS_QUOTA_MAP = {
    2: 10020, 3: 15460, 4: 18580, 5: 24100, 6: 28070, 7: 32090, 8: 36180
};

function updateQuotaDisplay() {
    const st = currentActiveState || {};
    const cmsLvl = parseInt(st.cmsLvl) || 0;
    let maxBC = CMS_QUOTA_MAP[cmsLvl] || 0;
    if (st.hasF) {
        maxBC = Math.round(maxBC * 0.3);
    }
    
    const activeSvcs = st.activeServices || [];
    const serviceTimes = st.serviceTimes || {};
    
    let usedBC = 0;
    for (const code of activeSvcs) {
        const item = LTC_SERVICES_DICT[code];
        if (item && item.type === "BC") {
            const times = parseInt(serviceTimes[code]) || 1;
            usedBC += item.price * times;
        }
    }
    
    const remainBC = maxBC - usedBC;
    const statusVal = String(st.statusVal || "1");
    let copayRate = 0.16;
    if (statusVal === "2") copayRate = 0.05;
    else if (statusVal === "3") copayRate = 0.00;
    
    const copayEst = Math.round(usedBC * copayRate);
    
    const elMax = document.getElementById("quota-max-bc");
    const elUsed = document.getElementById("quota-used-bc");
    const elRemain = document.getElementById("quota-remain-bc");
    const elCopay = document.getElementById("quota-copay-est");
    const elFill = document.getElementById("quota-progress-fill");
    
    if (elMax) elMax.textContent = `$${maxBC.toLocaleString()}`;
    if (elUsed) elUsed.textContent = `$${usedBC.toLocaleString()}`;
    if (elRemain) {
        elRemain.textContent = `$${remainBC.toLocaleString()}`;
        if (remainBC < 0) {
            elRemain.className = "quota-stat-val danger";
        } else {
            elRemain.className = "quota-stat-val success";
        }
    }
    if (elCopay) {
        const ratePct = Math.round(copayRate * 100);
        elCopay.textContent = `$${copayEst.toLocaleString()} (${ratePct}%)`;
    }
    
    if (elFill) {
        if (maxBC > 0) {
            const pct = Math.min(100, Math.round((usedBC / maxBC) * 100));
            elFill.style.width = `${pct}%`;
            if (usedBC > maxBC) {
                elFill.classList.add("over-budget");
            } else {
                elFill.classList.remove("over-budget");
            }
        } else {
            elFill.style.width = "0%";
        }
    }
    
    // Also update Primary Action Dock
    updatePrimaryActionDock(remainBC);
}

function renderInteractiveServices() {
    const servicesContainer = document.getElementById("active-services-container");
    if (!servicesContainer) return;
    
    const st = currentActiveState || {};
    const activeSvcs = st.activeServices || [];
    const serviceTimes = st.serviceTimes || {};
    
    if (activeSvcs.length === 0) {
        servicesContainer.innerHTML = `
            <span class="service-code-tag" style="background: rgba(148, 163, 184, 0.1); color: var(--text-muted); border-color: rgba(148, 163, 184, 0.2);">
                <i class="fa-solid fa-circle-info"></i> 尚無配置服務代碼（可由右上方選單快速加入）
            </span>
        `;
        return;
    }
    
    servicesContainer.innerHTML = activeSvcs.map(code => {
        const item = LTC_SERVICES_DICT[code] || { desc: "長照服務", price: 200 };
        const times = serviceTimes[code] ? ` (${serviceTimes[code]}次)` : "";
        return `
            <span class="service-code-tag">
                <i class="fa-solid fa-check"></i>
                <span>${code} ${item.desc}${times}</span>
                <button type="button" class="btn-tag-remove" onclick="removeServiceCode('${code}')" title="移除 ${code}">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </span>
        `;
    }).join("");
}

function removeServiceCode(code) {
    if (!currentActiveState) return;
    if (!currentActiveState.activeServices) currentActiveState.activeServices = [];
    currentActiveState.activeServices = currentActiveState.activeServices.filter(c => c !== code);
    if (currentActiveState.serviceTimes) {
        delete currentActiveState.serviceTimes[code];
    }
    renderInteractiveServices();
    updateQuotaDisplay();
    showToast(`已移除服務代碼：${code}`);
    syncStateToServerImmediate();
}

function handleAddServiceFromSelect(code) {
    if (!code) return;
    if (!currentActiveState) currentActiveState = {};
    if (!currentActiveState.activeServices) currentActiveState.activeServices = [];
    if (!currentActiveState.serviceTimes) currentActiveState.serviceTimes = {};
    
    if (currentActiveState.activeServices.includes(code)) {
        showToast(`服務代碼 ${code} 已經在配置清單中！`);
        return;
    }
    
    currentActiveState.activeServices.push(code);
    let defaultTimes = 12;
    if (code === "BA14") defaultTimes = 2;
    else if (code.startsWith("CA") || code.startsWith("CB") || code.startsWith("CD")) defaultTimes = 1;
    else if (code.startsWith("GA")) defaultTimes = 2;
    
    currentActiveState.serviceTimes[code] = defaultTimes;
    renderInteractiveServices();
    updateQuotaDisplay();
    showToast(`已成功新增服務代碼：${code}`);
    syncStateToServerImmediate();
}

function adjustServiceTimes(code, delta) {
    if (!currentActiveState) return;
    if (!currentActiveState.serviceTimes) currentActiveState.serviceTimes = {};
    const curr = parseInt(currentActiveState.serviceTimes[code]) || 12;
    const next = Math.max(1, curr + delta);
    currentActiveState.serviceTimes[code] = next;
    renderInteractiveServices();
    updateQuotaDisplay();
    syncStateToServerImmediate();
}

function setServiceTimes(code, val) {
    if (!currentActiveState) return;
    if (!currentActiveState.serviceTimes) currentActiveState.serviceTimes = {};
    const num = Math.max(1, parseInt(val) || 1);
    currentActiveState.serviceTimes[code] = num;
    renderInteractiveServices();
    updateQuotaDisplay();
    syncStateToServerImmediate();
}

function syncStateToServerImmediate() {
    if (syncFormTimeout) clearTimeout(syncFormTimeout);
    syncFormTimeout = setTimeout(async () => {
        try {
            await fetch("/api/chat/state", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ state: currentActiveState })
            });
        } catch (e) {
            console.error("Failed to sync state to server:", e);
        }
    }, 200);
}

// --- SMART IMPORT, SIDEBAR TOGGLES & ACTION DOCK ---

function toggleSmartImport() {
    const body = document.getElementById("smart-import-body");
    const icon = document.getElementById("btn-toggle-import")?.querySelector("i");
    if (!body) return;
    const isHidden = body.classList.contains("hidden");
    if (isHidden) {
        body.classList.remove("hidden");
        if (icon) icon.className = "fa-solid fa-chevron-up";
        const textarea = document.getElementById("smart-import-text");
        if (textarea) textarea.focus();
    } else {
        body.classList.add("hidden");
        if (icon) icon.className = "fa-solid fa-chevron-down";
    }
}

function clearSmartImport() {
    const textarea = document.getElementById("smart-import-text");
    if (textarea) {
        textarea.value = "";
        textarea.focus();
    }
}

async function handleSmartImportParse() {
    const textarea = document.getElementById("smart-import-text");
    if (!textarea || !textarea.value.trim()) {
        showToast("請先貼上長照訪視評估紀錄長文！");
        return;
    }
    
    const text = textarea.value.trim();
    const btn = document.getElementById("btn-smart-parse");
    const origBtnHtml = btn ? btn.innerHTML : "";
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>正在深度解析個案資料...</span>`;
    }
    
    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        });
        
        if (res.ok) {
            const data = await res.json();
            if (data.state) {
                currentActiveState = data.state;
                syncFormFromState(data.state, true);
                showToast(`✅ 已成功解析！個案「${data.state.name || '已填入'}」資料已完整更新至表單。`);
                
                // Add message to chat view
                if (data.reply_text) {
                    addChatMessage(data.reply_text, "assistant");
                }
                
                // Close smart import box after successful parsing
                const body = document.getElementById("smart-import-body");
                if (body) body.classList.add("hidden");
                const icon = document.getElementById("btn-toggle-import")?.querySelector("i");
                if (icon) icon.className = "fa-solid fa-chevron-down";
            }
        } else {
            showToast("⚠️ 解析失敗，請檢查網路連線或金鑰設定。");
        }
    } catch (e) {
        console.error("Smart import parsing error:", e);
        showToast(`⚠️ 解析時發生錯誤：${e.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = origBtnHtml;
        }
    }
}

function toggleLeftSidebar() {
    const container = document.querySelector(".workstation-container");
    if (!container) return;
    container.classList.toggle("left-collapsed");
    const isCollapsed = container.classList.contains("left-collapsed");
    localStorage.setItem("ws_left_collapsed", isCollapsed ? "1" : "0");
}

function toggleRightSidebar() {
    const container = document.querySelector(".workstation-container");
    if (!container) return;
    container.classList.toggle("right-collapsed");
    const isCollapsed = container.classList.contains("right-collapsed");
    localStorage.setItem("ws_right_collapsed", isCollapsed ? "1" : "0");
    
    // Update button text and icon state if present
    const headerBtn = document.getElementById("btn-toggle-ai-header");
    if (headerBtn) {
        const textSpan = headerBtn.querySelector(".ai-toggle-text");
        if (textSpan) {
            textSpan.textContent = isCollapsed ? "展開 AI" : "AI 助理";
        }
    }
}

function updatePrimaryActionDock(remainBC) {
    const dockName = document.getElementById("dock-name");
    const dockBadge = document.getElementById("dock-cms-badge");
    const dockMeta = document.getElementById("dock-meta");
    const dockAvatar = document.getElementById("dock-avatar");
    
    const st = currentActiveState || {};
    const name = st.name || "未加載個案";
    const cms = st.cmsLvl ? `CMS ${st.cmsLvl}級` : "CMS --";
    const vDate = st.visitDate || "未排定訪視";
    const vTime = st.visitTime ? ` ${st.visitTime}` : "";
    const remStr = (remainBC !== undefined) ? ` ｜ 剩餘額度: $${remainBC.toLocaleString()}` : "";
    
    if (dockName) dockName.textContent = name;
    if (dockBadge) dockBadge.textContent = cms;
    if (dockMeta) dockMeta.textContent = `${vDate}${vTime}${remStr}`;
    if (dockAvatar) dockAvatar.textContent = (name && name !== "未提供資料") ? name.charAt(0) : "個";
}

let syncFormTimeout = null;

function updateStateFromForm() {
    if (!currentActiveState) currentActiveState = {};
    
    function getVal(id) {
        const el = document.getElementById(id);
        return el ? el.value : "";
    }
    
    currentActiveState.name = getVal("cb-name");
    
    let bYear = getVal("cb-birthYear");
    // Convert 4-digit western year to ROC year if entered
    if (bYear && !isNaN(bYear) && parseInt(bYear) > 1900) {
        bYear = String(parseInt(bYear) - 1911);
        const bEl = document.getElementById("cb-birthYear");
        if (bEl) bEl.value = bYear;
    }
    currentActiveState.birthYear = bYear;
    
    currentActiveState.gender = getVal("cb-gender");
    currentActiveState.statusVal = getVal("cb-statusVal");
    currentActiveState.visitDate = getVal("cb-visitDate");
    currentActiveState.visitTime = getVal("cb-visitTime");
    currentActiveState.address = getVal("cb-address");
    currentActiveState.planType = getVal("cb-planType");
    currentActiveState.cmsLvl = getVal("cb-cmsLvl");
    currentActiveState.trafLvl = getVal("cb-trafLvl");
    currentActiveState.hasF = getVal("cb-hasF") === "true";
    currentActiveState.livingStr = getVal("cb-livingStr");
    currentActiveState.burdenStr = getVal("cb-burdenStr");
    currentActiveState.specialistName = getVal("cb-specialistName");
    
    // Update Badge Text immediately
    const badgeText = document.getElementById("case-badge-text");
    if (badgeText) {
        const cName = currentActiveState.name || "未提供資料";
        const cmsLvl = currentActiveState.cmsLvl ? ` | CMS ${currentActiveState.cmsLvl}級` : "";
        badgeText.textContent = `目前個案：${cName}${cmsLvl}`;
    }
    
    // Debounce & Immediately sync state to backend database
    if (syncFormTimeout) clearTimeout(syncFormTimeout);
    syncFormTimeout = setTimeout(async () => {
        try {
            await fetch("/api/chat/state", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ state: currentActiveState })
            });
        } catch (e) {
            console.error("Failed to sync state from form:", e);
        }
    }, 400);
}

async function fetchWithRetryAndTimeout(url, options = {}, retries = 2, timeoutMs = 30000) {
    for (let attempt = 0; attempt <= retries; attempt++) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        const fetchOptions = { ...options, signal: controller.signal };
        
        try {
            const res = await fetch(url, fetchOptions);
            clearTimeout(timer);
            return res;
        } catch (err) {
            clearTimeout(timer);
            if (attempt === retries) throw err;
            await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
        }
    }
}

async function handleSendChat(e) {
    if (e) e.preventDefault();
    const input = document.getElementById("ai-chat-input");
    if (!input || !input.value.trim()) return;
    
    const msg = input.value.trim();
    input.value = "";
    
    appendChatMessage(msg, "user");
    
    try {
        const res = await fetchWithRetryAndTimeout(getApiUrl("/api/chat"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg })
        }, 1, 45000);
        
        if (res.ok) {
            const data = await res.json();
            // Instantly render chat bubble with zero perceived UI lag
            appendChatMessage(data.reply_text || "已收到指示。", "assistant");
            // Defer 50+ DOM form updates to background event loop
            if (data.state) {
                requestAnimationFrame(() => {
                    setTimeout(() => {
                        updateFormFromState(data.state, true);
                    }, 0);
                });
            }
        } else {
            let errText = "通訊出現錯誤，請再試一次。";
            try {
                const errJson = await res.json();
                if (errJson && errJson.detail) errText = `系統提示：${errJson.detail}`;
            } catch (e) {}
            appendChatMessage(errText, "assistant");
        }
    } catch (err) {
        console.error("Error sending chat:", err);
        if (err.name === 'AbortError') {
            appendChatMessage("⏱️ AI 運算回應超時（已嘗試連線35秒）。請再發送一次訊息即可！", "assistant");
        } else {
            appendChatMessage("🔌 本地連線短暫波動，背景伺服器已自動完成重新連線，請再次點擊發送！", "assistant");
        }
    }
}

function sendQuickChat(text) {
    const input = document.getElementById("ai-chat-input");
    if (input) {
        input.value = text;
        handleSendChat();
    }
}

function formatChatText(text) {
    if (!text) return "";
    let html = text.replace(/(https?:\/\/[^\s<]+|\/download\/[a-zA-Z0-9_-]+)/g, (url) => {
        let label = "🔗 點此開啟連結";
        let btnClass = "btn-secondary";
        if (url.includes("/download/")) {
            label = "⬇️ 點此下載 Word 檔 (.doc)";
            btnClass = "btn-primary";
        } else if (url.includes("google.com") || url.includes("drive") || url.includes("docs")) {
            label = "☁️ 點此開啟 Google 雲端硬碟 (線上直接修改內容)";
            btnClass = "btn-success";
        }
        return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="btn ${btnClass}" style="display: inline-flex; align-items: center; gap: 6px; margin: 6px 0; text-decoration: none; padding: 8px 14px; font-size: 13px; border-radius: 8px;">${label}</a>`;
    });
    return html.replace(/\n/g, "<br>");
}

function renderChatHistory(history) {
    const container = document.getElementById("ai-messages-container");
    if (!container) return;
    if (!history || !Array.isArray(history) || history.length === 0) {
        container.innerHTML = `<div class="chat-bubble assistant">👋 您好！我是您的長照 AI 助理。請將個案訪視評估內容貼在這裡，系統將自動解析並為您更新表單！</div>`;
        return;
    }
    
    container.innerHTML = "";
    history.forEach(msg => {
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${msg.role === "user" ? "user" : "assistant"}`;
        bubble.innerHTML = formatChatText(msg.content || "");
        container.appendChild(bubble);
    });
    container.scrollTop = container.scrollHeight;
}

function sendQuickChatMessage(txt) {
    const input = document.getElementById("ai-chat-input");
    if (input) {
        input.value = txt;
        const form = document.getElementById("ai-chat-form");
        if (form) {
            handleSendChat();
        }
    }
}

function appendChatMessage(text, role) {
    const container = document.getElementById("ai-messages-container");
    if (!container) return;
    
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;
    bubble.innerHTML = formatChatText(text || "");

    if (role === "assistant" && text && text.includes("【行事曆建立前確認】")) {
        const cardDiv = document.createElement("div");
        cardDiv.className = "chat-confirmation-card";
        cardDiv.innerHTML = `
            <div class="chat-card-title"><i class="fa-solid fa-calendar-check"></i> 請點擊下方按鈕一鍵正式寫入日曆：</div>
            <div class="chat-card-actions">
                <button type="button" class="btn-chat-action btn-chat-confirm" onclick="sendQuickChatMessage('確認建立')">
                    <i class="fa-solid fa-circle-check"></i> ✅ 確認建立至日曆
                </button>
            </div>
        `;
        bubble.appendChild(cardDiv);
    }
    
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

function openPlanResultModal(downloadUrl, driveUrl) {
    const modal = document.getElementById("plan-result-modal");
    const wordBtn = document.getElementById("modal-download-word-btn");
    const driveBtn = document.getElementById("modal-open-drive-btn");
    
    if (wordBtn) {
        wordBtn.href = downloadUrl || "#";
    }
    if (driveBtn) {
        if (driveUrl) {
            driveBtn.href = driveUrl;
            driveBtn.style.display = "inline-flex";
            driveBtn.innerHTML = `<i class="fa-brands fa-google-drive"></i> ☁️ 開啟 Google 雲端硬碟 (線上直接修改內容)`;
            driveBtn.className = "btn btn-success btn-block";
        } else {
            driveBtn.href = "https://drive.google.com";
            driveBtn.style.display = "inline-flex";
            driveBtn.innerHTML = `<i class="fa-brands fa-google-drive"></i> ☁️ 開啟 Google 雲端硬碟`;
        }
    }
    if (modal) modal.classList.remove("hidden");
}

function closePlanResultModal() {
    const modal = document.getElementById("plan-result-modal");
    if (modal) modal.classList.add("hidden");
}

async function resetChatSession() {
    if (!confirm("確定要清除目前的個案紀錄並重新開始嗎？")) return;
    try {
        const input = document.getElementById("ai-chat-input");
        if (input) input.value = "";
        
        const res = await fetch("/api/chat/reset", { method: "POST" });
        if (res.ok) {
            const data = await res.json();
            showToast("已成功清除目前個案紀錄！");
            const container = document.getElementById("ai-messages-container");
            if (container) {
                container.innerHTML = `<div class="chat-bubble assistant">👋 已成功清空目前紀錄。請輸入新個案的訪視資料或語音內容開始處理！</div>`;
            }
            if (data.state) {
                currentActiveState = data.state;
                updateFormFromState(data.state, true);
            }
        }
    } catch (e) {
        showToast("清空紀錄失敗：" + e.message);
    }
}

async function openCaseSelectorModal() {
    const modal = document.getElementById("case-selector-modal");
    const list = document.getElementById("case-selector-list");
    if (!modal || !list) return;
    
    list.innerHTML = `<div style="padding:10px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> 載入個案清單中...</div>`;
    modal.classList.remove("hidden");
    
    try {
        const res = await fetch(getApiUrl("/api/cases"));
        if (res.ok) {
            const data = await res.json();
            const cases = data.cases || [];
            if (cases.length > 0) {
                list.innerHTML = cases.map(c => `
                    <button class="chip-btn" onclick="loadCaseByName(decodeURIComponent('${encodeURIComponent(c)}'))" style="font-size:0.9rem; padding:8px 16px;">
                        <i class="fa-solid fa-user-check"></i> ${escapeHTML(c)}
                    </button>
                `).join("");
            } else {
                list.innerHTML = `<div style="padding:10px; color:var(--text-muted);">尚無保存的個案紀錄</div>`;
            }
        }
    } catch (e) {
        list.innerHTML = `<div style="color:#ef4444; padding:10px;">載入失敗：${e.message}</div>`;
    }
}

let allSidebarCases = [];

function renderSidebarCaseCards(casesToRender) {
    const list = document.getElementById("sidebar-resident-list");
    if (!list) return;
    
    const searchInput = document.getElementById("sidebar-case-search");
    const query = (searchInput ? searchInput.value : "").trim().toLowerCase();
    
    const cases = casesToRender !== undefined ? casesToRender : allSidebarCases;
    
    if (cases && cases.length > 0) {
        list.innerHTML = cases.map((cName) => {
            const avatarChar = cName.charAt(0);
            const isActive = (currentActiveState && currentActiveState.name === cName);
            const enc = encodeURIComponent(cName);
            return `
                <div class="resident-profile-card ${isActive ? 'active' : ''}" onclick="loadCaseByName(decodeURIComponent('${enc}'))">
                    <div class="resident-card-header">
                        <div class="resident-avatar-name">
                            <div class="resident-avatar">${escapeHTML(avatarChar)}</div>
                            <span class="resident-name">${escapeHTML(cName)}</span>
                        </div>
                        <span class="resident-tag">已留存</span>
                    </div>
                    <div class="resident-details">
                        <span>點擊載入個案資料</span>
                    </div>
                </div>
            `;
        }).join("");
    } else {
        if (query) {
            list.innerHTML = `
                <div style="padding: 24px 10px; text-align: center; color: var(--text-muted); font-size: 0.82rem;">
                    <i class="fa-solid fa-magnifying-glass" style="margin-bottom: 8px; font-size: 1.2rem; display: block; opacity: 0.6;"></i>
                    未找到相符個案<br>
                    <span style="font-size: 0.75rem; opacity: 0.8;">搜尋關鍵字「${escapeHTML(query)}」無結果</span>
                </div>
            `;
        } else {
            list.innerHTML = `
                <div style="padding: 20px 10px; text-align: center; color: var(--text-muted); font-size: 0.8rem;">
                    <i class="fa-solid fa-folder-open" style="margin-bottom: 8px; font-size: 1.3rem; display: block; opacity: 0.6;"></i>
                    尚無個案資料<br>
                    <span style="font-size: 0.75rem; opacity: 0.8;">點擊「個案清單」或透過 AI 建立</span>
                </div>
            `;
        }
    }
}

function handleSidebarCaseSearch(query) {
    const q = (query || "").trim().toLowerCase();
    if (!q) {
        renderSidebarCaseCards(allSidebarCases);
        return;
    }
    const filtered = allSidebarCases.filter(cName => cName.toLowerCase().includes(q));
    renderSidebarCaseCards(filtered);
}

function initSidebarCaseSearch() {
    const searchInput = document.getElementById("sidebar-case-search");
    if (searchInput && !searchInput.dataset.hasSearchListener) {
        searchInput.dataset.hasSearchListener = "true";
        searchInput.addEventListener("input", (e) => {
            handleSidebarCaseSearch(e.target.value);
        });
    }
}

async function loadSidebarResidentCards() {
    initSidebarCaseSearch();
    const list = document.getElementById("sidebar-resident-list");
    if (!list) return;
    try {
        const res = await fetch(getApiUrl("/api/cases"));
        if (res.ok) {
            const data = await res.json();
            allSidebarCases = data.cases || [];
            const searchInput = document.getElementById("sidebar-case-search");
            const currentQuery = searchInput ? searchInput.value : "";
            handleSidebarCaseSearch(currentQuery);
        }
    } catch (e) {
        console.warn("Sidebar cases fetch warning:", e);
    }
}

function closeCaseSelectorModal() {
    const modal = document.getElementById("case-selector-modal");
    if (modal) modal.classList.add("hidden");
}

function closeCaseSelectorModalOnOverlay(e) {
    if (e.target && e.target.id === "case-selector-modal") {
        closeCaseSelectorModal();
    }
}

async function loadCaseByName(name) {
    if (!name) return;
    try {
        const res = await fetch(getApiUrl("/api/cases/load"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name })
        });
        if (res.ok) {
            const data = await res.json();
            if (data.success && data.state) {
                showToast(`已成功載入個案「${name}」！`);
                currentActiveState = data.state;
                // 自動切換至工作站中間「個案填報與即時評估表」面板
                switchWorktab('builder');
                updateFormFromState(data.state, true);
                loadSidebarResidentCards();
                if (data.state._history && Array.isArray(data.state._history) && data.state._history.length > 0) {
                    renderChatHistory(data.state._history);
                } else {
                    appendChatMessage(`已為您載入個案「${name}」的紀錄！`, "assistant");
                }
                closeCaseSelectorModal();
            } else {
                showToast(data.error || "載入失敗");
            }
        } else {
            showToast("載入個案伺服器回應異常");
        }
    } catch (e) {
        showToast("載入個案發生錯誤：" + e.message);
    }
}

async function generateCarePlan() {
    showToast("⏳ 正在產出照顧計畫書與同步至 Google Drive...");
    try {
        const res = await fetch("/debug-drive");
        if (res.ok) {
            const data = await res.json();
            const userId = data.user_id || "default_user";
            const downloadUrl = `/download/${userId}`;
            let driveUrl = null;
            
            if (data.upload_result && data.upload_result.success) {
                driveUrl = data.upload_result.link;
                showToast("✅ 照顧計畫書產出成功！已同步上傳至 Google Drive。");
            } else {
                showToast("✅ 照顧計畫書產出成功！");
            }
            
            // Pop up Modal with Action Buttons!
            openPlanResultModal(downloadUrl, driveUrl);
            
            // Append result and links into the AI Chat window
            let chatMsg = `🎉 **照顧計畫書已成功產出！**\n\n`;
            chatMsg += `⬇️ 點此下載 Word 檔：\n${window.location.origin}${downloadUrl}\n\n`;
            if (driveUrl) {
                chatMsg += `☁️ 點此開啟 Google 雲端硬碟線上版：\n${driveUrl}`;
            }
            appendChatMessage(chatMsg, "assistant");
        } else {
            showToast("產出計畫書失敗，請再試一次。");
        }
    } catch (e) {
        showToast("產出計畫書時發生錯誤：" + e.message);
    }
}

function syncCalendarFromWeb() {
    sendQuickChat("建立行事曆");
}

// Voice Speech Recognition Input
let speechRecognizer = null;
let isRecording = false;

function toggleVoiceInput() {
    const voiceBtn = document.getElementById("btn-voice-chat");
    const input = document.getElementById("ai-chat-input");
    
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showToast("您的瀏覽器不支援語音辨識，請使用 Chrome 或 Edge。");
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (isRecording) {
        if (speechRecognizer) speechRecognizer.stop();
        isRecording = false;
        if (voiceBtn) voiceBtn.classList.remove("recording");
        return;
    }
    
    speechRecognizer = new SpeechRecognition();
    speechRecognizer.lang = 'zh-TW';
    speechRecognizer.continuous = false;
    speechRecognizer.interimResults = false;
    
    speechRecognizer.onstart = () => {
        isRecording = true;
        if (voiceBtn) voiceBtn.classList.add("recording");
        showToast("🎙️ 請開始對話，系統正在聆聽中...");
    };
    
    speechRecognizer.onresult = (event) => {
        const text = event.results[0][0].transcript;
        if (input) input.value = text;
        showToast("已辨識語音：" + text);
        handleSendChat();
    };
    
    speechRecognizer.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        showToast("語音辨識發生錯誤：" + event.error);
        isRecording = false;
        if (voiceBtn) voiceBtn.classList.remove("recording");
    };
    
    speechRecognizer.onend = () => {
        isRecording = false;
        if (voiceBtn) voiceBtn.classList.remove("recording");
    };
    
    speechRecognizer.start();
}

// --- AUTO UPDATER UI ---
function openUpdateModal() {
    const modal = document.getElementById("update-modal");
    if (modal) modal.classList.remove("hidden");
    checkSystemUpdateUI();
}

function closeUpdateModal() {
    const modal = document.getElementById("update-modal");
    if (modal) modal.classList.add("hidden");
}

async function checkSystemUpdateUI() {
    openUpdateModal();
    const content = document.getElementById("update-status-content");
    const footer = document.getElementById("update-modal-footer");
    
    if (content) {
        content.innerHTML = `<p><i class="fa-solid fa-spinner fa-spin icon-accent-calendar"></i> 正在連線至雲端檢查最新版本...</p>`;
    }
    
    try {
        const res = await fetch("/api/system/check-update");
        if (res.ok) {
            const data = await res.json();
            if (data.has_update) {
                if (content) {
                    content.innerHTML = `
                        <div class="update-found-box" style="padding: 15px; background: rgba(59, 130, 246, 0.1); border-radius: 12px; border: 1px solid var(--accent-blue);">
                            <h3 style="color: var(--accent-blue); margin-bottom: 8px;"><i class="fa-solid fa-sparkles"></i> 發現新版本：v${data.latest_version}</h3>
                            <p style="font-size: 0.9rem; margin-bottom: 6px;">目前版本：v${data.current_version} (${data.release_date || ""})</p>
                            <p style="font-size: 0.95rem; line-height: 1.5; color: var(--text-primary);"><strong>更新日誌：</strong> ${data.changelog}</p>
                        </div>
                    `;
                }
                if (footer) {
                    footer.innerHTML = `
                        <button type="button" class="btn btn-secondary" onclick="closeUpdateModal()">暫不更新</button>
                        <button type="button" class="btn btn-primary" onclick="applySystemUpdateUI('${data.download_url}')"><i class="fa-solid fa-cloud-arrow-down"></i> 一鍵下載並更新</button>
                    `;
                }
            } else {
                if (content) {
                    content.innerHTML = `
                        <div style="text-align: center; padding: 20px 0;">
                            <i class="fa-solid fa-circle-check" style="font-size: 2.5rem; color: var(--accent-green); margin-bottom: 10px;"></i>
                            <h3>您目前使用的是最新版本！(v${data.current_version})</h3>
                            <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 6px;">無需更新，系統運作一切正常。</p>
                        </div>
                    `;
                }
                if (footer) {
                    footer.innerHTML = `<button type="button" class="btn btn-secondary" onclick="closeUpdateModal()">關閉</button>`;
                }
            }
        } else {
            throw new Error("HTTP " + res.status);
        }
    } catch (e) {
        if (content) {
            content.innerHTML = `<p style="color: #ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> 檢查更新失敗：${e.message}</p>`;
        }
        if (footer) {
            footer.innerHTML = `<button type="button" class="btn btn-secondary" onclick="closeUpdateModal()">關閉</button>`;
        }
    }
}

async function applySystemUpdateUI(url) {
    const content = document.getElementById("update-status-content");
    const footer = document.getElementById("update-modal-footer");
    
    if (content) {
        content.innerHTML = `<p><i class="fa-solid fa-spinner fa-spin"></i> 正在線上下載更新套件並安裝中，請稍候...</p>`;
    }
    if (footer) footer.innerHTML = "";
    
    try {
        const res = await fetch("/api/system/apply-update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ download_url: url })
        });
        if (res.ok) {
            const data = await res.json();
            if (data.success) {
                showToast("✅ 軟體已成功更新！即將重新載入...");
                setTimeout(() => { window.location.reload(); }, 2000);
            } else {
                showToast("❌ 更新失敗：" + data.error);
            }
        }
    } catch (e) {
        showToast("更新過程發生錯誤：" + e.message);
    }
}
