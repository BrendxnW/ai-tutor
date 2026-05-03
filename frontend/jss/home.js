async function loadStreak() {
  const currentStreak = document.getElementById("current-streak");
  const currentCoins = document.getElementById("current-coins");

  if (!currentStreak && !currentCoins) {
    return;
  }

  try {
    const [streakResponse, coinsResponse] = await Promise.all([
      fetch("/api/streak"),
      fetch("/api/coins"),
    ]);
    const streak = await streakResponse.json();
    const coins = await coinsResponse.json();

    if (!streakResponse.ok) {
      if (currentStreak) currentStreak.textContent = "0";
      if (currentCoins) currentCoins.textContent = "0";
      return;
    }

    if (currentStreak) {
      currentStreak.textContent = streak.current_streak || 0;
    }
    if (currentCoins) {
      currentCoins.textContent = coinsResponse.ok ? coins.balance || 0 : "0";
    }
  } catch (error) {
    if (currentStreak) currentStreak.textContent = "0";
    if (currentCoins) currentCoins.textContent = "0";
    console.error("Could not load streak:", error);
  }
}

function renderCourse(course) {
  const item = document.createElement("a");
  item.className = "course-item";
  item.href = `/tutor/${encodeURIComponent(course.id)}`;

  const name = document.createElement("h3");
  name.textContent = course.name || `Course ${course.id}`;

  const details = document.createElement("p");
  details.textContent = course.course_code || "Canvas course";

  const action = document.createElement("span");
  action.className = "course-action";
  action.textContent = "Start";

  item.append(name, details, action);
  return item;
}

async function loadCanvasCourses() {
  const status = document.getElementById("canvas-courses-status");
  const list = document.getElementById("canvas-courses-list");

  if (!status || !list) {
    return;
  }

  status.textContent = "Loading Canvas courses...";
  status.className = "courses-status";
  list.innerHTML = "";

  try {
    const response = await fetch("/api/canvas/courses");
    if (response.status === 401) {
      window.location.href = "/";
      return;
    }

    const data = await response.json();
    if (!response.ok || !data.connected) {
      status.textContent = data.message || "Could not load Canvas courses.";
      status.className = "courses-status disconnected";
      return;
    }

    const courses = Array.isArray(data.courses) ? data.courses : [];
    if (courses.length === 0) {
      status.textContent = "No active Canvas courses found.";
      status.className = "courses-status empty";
      return;
    }

    status.textContent = `${courses.length} active course${courses.length === 1 ? "" : "s"}`;
    status.className = "courses-status connected";
    list.replaceChildren(...courses.map(renderCourse));
  } catch (error) {
    status.textContent = "Could not load Canvas courses.";
    status.className = "courses-status disconnected";
    console.error("Could not load Canvas courses:", error);
  }
}

loadStreak();
loadCanvasCourses();
