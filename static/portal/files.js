// 文件管理页：浏览 / 下载 / 上传（含文件夹）/ 删除 / 同名冲突处理
(function () {
  "use strict";
  var HAS_MINE = window.FM_HAS_MINE === 1;
  var state = { area: HAS_MINE ? "mine" : "shared", path: "" };
  var listEl = document.getElementById("fm-list");
  var crumbEl = document.getElementById("fm-crumb");
  var statusEl = document.getElementById("fm-status");
  var inputFile = document.getElementById("fm-input-file");
  var inputDir = document.getElementById("fm-input-dir");
  var modal = document.getElementById("fm-modal");
  var modalBody = document.getElementById("fm-modal-body");
  var checkAll = document.getElementById("fm-conf-all");

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmtSize(n) {
    if (n >= 1073741824) return (n / 1073741824).toFixed(1) + " GB";
    if (n >= 1048576) return (n / 1048576).toFixed(1) + " MB";
    if (n >= 1024) return (n / 1024).toFixed(1) + " KB";
    return n + " B";
  }
  function fmtTime(t) {
    var d = new Date(t * 1000);
    function p(x) { return x < 10 ? "0" + x : x; }
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) +
      " " + p(d.getHours()) + ":" + p(d.getMinutes());
  }
  function getCookie(name) {
    var m = document.cookie.match(new RegExp("(^|;\\s*)" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[2]) : "";
  }
  function rel(name) { return state.path ? state.path + "/" + name : name; }
  function api(path, params) {
    var q = new URLSearchParams(params || {}).toString();
    return fetch("/files/api/" + path + (q ? "?" + q : ""), {
      headers: { "X-CSRFToken": getCookie("csrftoken") },
    });
  }
  function apiPost(path, fd) {
    return fetch("/files/api/" + path, {
      method: "POST", body: fd,
      headers: { "X-CSRFToken": getCookie("csrftoken") },
    });
  }

  // ---- 列表 ----
  var dirCache = {};
  function fetchList(dir) {
    return api("list", { area: state.area, path: dir })
      .then(function (r) { return r.json(); })
      .then(function (d) { return d.entries || []; });
  }
  function load() {
    dirCache = {};
    renderCrumb();
    listEl.innerHTML = '<tr><td colspan="4" class="muted">加载中…</td></tr>';
    fetchList(state.path)
      .then(function (entries) {
        dirCache[state.path] = entries.map(function (e) { return e.name; });
        render(entries);
      })
      .catch(function () {
        listEl.innerHTML = '<tr><td colspan="4" class="muted">加载失败</td></tr>';
      });
  }

  function renderCrumb() {
    var parts = state.path ? state.path.split("/") : [];
    var html = '<a href="#" data-path="">' +
      (state.area === "mine" ? "我的文件" : "公共区") + "</a>";
    var acc = "";
    parts.forEach(function (p) {
      acc = acc ? acc + "/" + p : p;
      html += ' <span class="fm-sep">/</span> <a href="#" data-path="' + esc(acc) + '">' + esc(p) + "</a>";
    });
    crumbEl.innerHTML = html;
  }

  function render(entries) {
    var html = "";
    if (state.path) {
      html += '<tr class="fm-row fm-dir" data-up="1"><td class="fm-name">📁 ..</td>' +
        '<td></td><td></td><td></td></tr>';
    }
    if (!entries.length) {
      html += '<tr><td colspan="4" class="muted">（空文件夹）</td></tr>';
    }
    entries.forEach(function (e) {
      var ops = "";
      if (!e.is_dir && state.area === "mine") {
        ops += '<button class="fm-btn fm-dl" data-name="' + esc(e.name) + '">下载</button>';
      }
      ops += '<button class="fm-btn fm-btn-danger fm-del" data-name="' + esc(e.name) +
        '" data-dir="' + (e.is_dir ? 1 : 0) + '">删除</button>';
      html += '<tr class="fm-row' + (e.is_dir ? " fm-dir" : "") +
        '" data-name="' + esc(e.name) + '">' +
        '<td class="fm-name">' + (e.is_dir ? "📁 " : "📄 ") + esc(e.name) + "</td>" +
        '<td class="fm-col-size">' + (e.is_dir ? "" : fmtSize(e.size)) + "</td>" +
        '<td class="fm-col-time">' + fmtTime(e.mtime) + "</td>" +
        '<td class="fm-col-op">' + ops + "</td>" +
        "</tr>";
    });
    listEl.innerHTML = html;
  }

  listEl.addEventListener("click", function (ev) {
    var row = ev.target.closest("tr.fm-row");
    if (!row) return;
    if (ev.target.classList.contains("fm-dl")) {
      location.href = "/files/api/download?area=" + encodeURIComponent(state.area) +
        "&path=" + encodeURIComponent(rel(ev.target.getAttribute("data-name")));
      return;
    }
    if (ev.target.classList.contains("fm-del")) {
      var name = ev.target.getAttribute("data-name");
      var isDir = ev.target.getAttribute("data-dir") === "1";
      if (!confirm('确定删除 "' + name + '"？' +
        (isDir ? "文件夹将连同里面所有内容一起删除，" : "") + "不可恢复。")) return;
      var fd = new FormData();
      fd.append("area", state.area);
      fd.append("path", rel(name));
      apiPost("delete", fd).then(function (r) { return r.json(); }).then(function (d) {
        statusEl.textContent = d.error ? "删除失败：" + d.error : "已删除 " + name;
        load();
      });
      return;
    }
    if (!row.classList.contains("fm-dir")) return;
    if (row.hasAttribute("data-up")) {
      var parts = state.path.split("/");
      parts.pop();
      state.path = parts.join("/");
    } else {
      state.path = rel(row.getAttribute("data-name"));
    }
    load();
  });

  crumbEl.addEventListener("click", function (ev) {
    if (ev.target.tagName !== "A") return;
    ev.preventDefault();
    state.path = ev.target.getAttribute("data-path") || "";
    load();
  });

  Array.prototype.forEach.call(document.querySelectorAll(".fm-area"), function (b) {
    b.addEventListener("click", function () {
      Array.prototype.forEach.call(document.querySelectorAll(".fm-area"), function (x) {
        x.classList.remove("active");
      });
      b.classList.add("active");
      state.area = b.getAttribute("data-area");
      state.path = "";
      load();
    });
  });

  // ---- 同名冲突 ----
  function windowsName(base, used) {
    var dot = base.lastIndexOf(".");
    var stem = dot > 0 ? base.slice(0, dot) : base;
    var ext = dot > 0 ? base.slice(dot) : "";
    for (var i = 1; ; i++) {
      var cand = stem + " (" + i + ")" + ext;
      if (used.indexOf(cand) < 0) return cand;
    }
  }
  function askConflict(name) {
    return new Promise(function (resolve) {
      modalBody.textContent = "「" + name + "」在目标文件夹中已存在。";
      modal.hidden = false;
      checkAll.checked = false;
      function off() {
        document.getElementById("fm-conf-over").onclick = null;
        document.getElementById("fm-conf-keep").onclick = null;
        document.getElementById("fm-conf-skip").onclick = null;
      }
      function done(choice) {
        modal.hidden = true;
        off();
        resolve({ choice: choice, all: checkAll.checked });
      }
      document.getElementById("fm-conf-over").onclick = function () { done("over"); };
      document.getElementById("fm-conf-keep").onclick = function () { done("keep"); };
      document.getElementById("fm-conf-skip").onclick = function () { done("skip"); };
    });
  }

  // ---- 上传 ----
  function uploadFiles(files, withRel) {
    var arr = Array.prototype.slice.call(files);
    if (!arr.length) return;
    var used = (dirCache[state.path] || []).slice();
    var batchChoice = null; // over / keep / skip（勾选"后续都按此"后对本批次生效）
    var i = 0;

    function next() {
      if (i >= arr.length) {
        statusEl.textContent = "上传完成（共 " + arr.length + " 个）";
        load();
        return;
      }
      var f = arr[i];
      var rawRel = withRel && f.webkitRelativePath ? f.webkitRelativePath : f.name;
      var baseName = rawRel.split("/").pop();
      var conflict = used.indexOf(rawRel) >= 0;
      Promise.resolve()
        .then(function () {
          if (!conflict) return { choice: "ok", all: false };
          if (batchChoice) return { choice: batchChoice, all: false };
          return askConflict(baseName);
        })
        .then(function (dec) {
          if (dec.all) batchChoice = dec.choice;
          if (dec.choice === "skip") {
            statusEl.textContent = "已跳过 " + baseName;
            i += 1;
            next();
            return;
          }
          var finalRel = rawRel;
          if (dec.choice === "keep") {
            baseName = windowsName(baseName, used);
            var seg = rawRel.split("/");
            seg[seg.length - 1] = baseName;
            finalRel = seg.join("/");
          }
          used.push(finalRel);
          var fd = new FormData();
          fd.append("area", state.area);
          fd.append("path", state.path);
          fd.append("relpath", finalRel);
          fd.append("file", f);
          statusEl.textContent = "上传中 " + (i + 1) + "/" + arr.length + "：" + baseName;
          apiPost("upload", fd).then(function (r) { return r.json(); }).then(function (d) {
            if (d.error) {
              statusEl.textContent = "上传失败：" + d.error;
              return;
            }
            i += 1;
            next();
          });
        });
    }
    next();
  }

  document.getElementById("fm-upload-file").addEventListener("click", function () {
    inputFile.click();
  });
  document.getElementById("fm-upload-dir").addEventListener("click", function () {
    inputDir.click();
  });
  inputFile.addEventListener("change", function () {
    uploadFiles(inputFile.files, false);
    inputFile.value = "";
  });
  inputDir.addEventListener("change", function () {
    uploadFiles(inputDir.files, true);
    inputDir.value = "";
  });

  load();
})();
