// 统计页渲染
(function () {
  "use strict";
  var el = document.getElementById("stats-data");
  if (!el) return;
  var D = JSON.parse(el.textContent);

  function fmt(n) {
    n = Number(n) || 0;
    if (n >= 1e8) return (n / 1e8).toFixed(2) + " 亿";
    if (n >= 1e4) return (n / 1e4).toFixed(1) + " 万";
    return String(n);
  }

  // 累计总量（含输入/输出拆分与缓存命中率）
  document.getElementById("total-num").textContent = fmt(D.total_all_time);
  document.getElementById("total-sub").textContent =
    "输入 " + fmt(D.total_in || 0) + " · 输出 " + fmt(D.total_out || 0) +
    " · 缓存命中率 " + (D.hit_pct || 0) + "%";

  // 饱和告警：当前在用 ≥3 人
  var warn = document.getElementById("sat-warn");
  if (warn) warn.hidden = (D.active_count || 0) < 3;

  // 排名
  var ul = document.getElementById("rank-list");
  if (!D.ranking.length) {
    ul.innerHTML = '<li class="muted">最近 7 天还没有用量记录</li>';
  }
  D.ranking.forEach(function (r) {
    var li = document.createElement("li");
    li.className = "rank-item";
    li.innerHTML =
      '<span class="rank-medal">' + (r.medal || "") + "</span>" +
      '<span class="cctm-avatar" style="background:' + r.color + '">' +
      (r.name[0] || "?").toUpperCase() + "</span>" +
      '<span class="rank-name">' + r.name + "</span>" +
      '<span class="rank-num">' + fmt(r.total) + "</span>";
    ul.appendChild(li);
  });

  // 当前在用
  document.getElementById("active-num").textContent = D.active_count;
  document.getElementById("active-cap").textContent = " / " + D.cap;
  var alist = document.getElementById("active-list");
  if (!D.active_users.length) {
    alist.innerHTML = '<li class="muted">当前没有人在使用</li>';
  }
  D.active_users.forEach(function (u) {
    var li = document.createElement("li");
    li.className = "active-item";
    li.innerHTML =
      '<span class="green-dot"></span>' +
      '<span class="cctm-avatar" style="background:' + u.color + '">' +
      (u.name[0] || "?").toUpperCase() + "</span>" +
      "<span>" + u.name + "</span>";
    alist.appendChild(li);
  });

  // 曲线（每小时，最近 7 天）
  var canvas = document.getElementById("trend-chart");
  if (window.Chart) {
    new Chart(canvas, {
      type: "line",
      data: {
        labels: D.series.map(function (p) { return p.t; }),
        datasets: [{
          data: D.series.map(function (p) { return p.n; }),
          borderColor: "#2563eb",
          backgroundColor: "rgba(37, 99, 235, .15)",
          fill: true,
          tension: 0.25,
          pointRadius: 0,
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: function (c) { return fmt(c.parsed.y) + " tokens"; } },
          },
        },
        scales: {
          x: { ticks: { maxTicksLimit: 12, color: "#9ca3af" }, grid: { color: "rgba(55,65,81,.4)" } },
          y: { beginAtZero: true, ticks: { color: "#9ca3af", callback: function (v) { return fmt(v); } }, grid: { color: "rgba(55,65,81,.4)" } },
        },
      },
    });
  } else {
    // Chart.js 缺失时的降级：文本表格
    var div = document.createElement("div");
    div.className = "chart-fallback";
    div.textContent = D.series
      .filter(function (p) { return p.n > 0; })
      .map(function (p) { return p.t + "  " + fmt(p.n); })
      .join("\n");
    canvas.replaceWith(div);
  }
})();
