// 注入脚本：导航条、品牌、思考档位限制（xhigh/max 置灰）
(function () {
  "use strict";

  // ---- 顶部导航条 ----
  function buildNav() {
    if (document.getElementById("cctm-nav")) return;
    var name = window.CCTM_USER || "";
    var color = window.CCTM_COLOR || "#2563eb";
    var nav = document.createElement("div");
    nav.id = "cctm-nav";
    nav.innerHTML =
      '<span class="cctm-brand">CCTM AI 平台</span>' +
      '<div class="cctm-tabs">' +
      '<a class="cctm-tab active" href="/">CCTM AGENT</a>' +
      '<a class="cctm-tab" href="/stats/">agent 统计</a>' +
      '<a class="cctm-tab" href="/files/">文件管理</a>' +
      (window.CCTM_STAFF === "1" ? '<a class="cctm-tab" href="/users/">用户管理</a>' : "") +
      "</div>" +
      '<div class="cctm-user">' +
      '<span class="cctm-avatar" style="background:' + color + '">' +
      ((name[0] || "?").toUpperCase()) + "</span>" +
      '<span class="cctm-name">' + name + "</span>" +
      '<a class="cctm-link" href="/change-password/">修改密码</a>' +
      '<a class="cctm-link" href="/logout/">退出</a>' +
      "</div>";
    (document.body || document.documentElement).appendChild(nav);
  }

  // ---- 品牌 ----
  function brand() {
    document.title = "CCTM AGENT";
    var link = document.querySelector('link[rel="icon"]');
    if (link) {
      link.href =
        "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32'%3E%3Crect width='32' height='32' rx='7' fill='%232563eb'/%3E%3Ctext x='16' y='23' font-family='Arial' font-size='19' font-weight='bold' fill='white' text-anchor='middle'%3EC%3C/text%3E%3C/svg%3E";
    }
  }

  // ---- 思考档位：xhigh / max 置灰禁选（UI 标签为 Extra High / Max） ----
  var BAD = /^\s*(xhigh|x-high|extra\s*high|max)\s*$/i;

  function blockEvt(e) {
    e.stopPropagation();
    e.preventDefault();
  }

  function clampOne(el) {
    if (el.tagName === "SELECT") return; // select 单独处理
    var t = (el.textContent || "").trim();
    if (!BAD.test(t)) return;
    // 叶子或选项容器都处理：向上找最近的交互式祖先一并禁用
    var target = el.closest('[role="option"],[role="menuitem"],[role="menuitemradio"],button,li') || el;
    [el, target].forEach(function (node) {
      if (!node || !node.setAttribute) return;
      node.setAttribute("disabled", "disabled");
      node.setAttribute("aria-disabled", "true");
      node.classList.add("cctm-disabled-opt");
      node.addEventListener("click", blockEvt, true);
      node.addEventListener("pointerdown", blockEvt, true);
      node.addEventListener("keydown", blockEvt, true);
    });
  }

  function clamp(root) {
    var scope = root || document;
    var els = scope.querySelectorAll(
      'button, [role="option"], [role="menuitem"], [role="menuitemradio"], li, div, span, option'
    );
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      // 叶子判断：没有子元素节点（或子元素文本合计等于自身文本）
      if (el.childElementCount === 0) clampOne(el);
    }
    var selects = scope.querySelectorAll("select");
    for (var s = 0; s < selects.length; s++) {
      var opts = selects[s].options || [];
      for (var o = 0; o < opts.length; o++) {
        if (BAD.test((opts[o].textContent || "").trim())) opts[o].disabled = true;
      }
    }
  }

  // ---- 文案替换（沿用旧版 bundle 补丁改过的字，DOM 层实现，升级不丢） ----
  function rebrand(root) {
    var scope = root || document;
    var nodes = scope.querySelectorAll("span,div,h1,h2");
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (el.childElementCount !== 0) continue;
      var t = (el.textContent || "").trim();
      var cn = String(el.className || "");
      if (t === "Qwen Code" && /brand|title/i.test(cn)) {
        el.textContent = "CCTM AGENT";
      } else if (/^(What would you like to do\?|你想构建什么？)$/.test(t) && /subtitle/i.test(cn)) {
        el.textContent = "你专属的临床试验全能专家";
      }
    }
  }

  function init() {
    buildNav();
    brand();
    clamp();
    rebrand();
    var mo = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var added = muts[i].addedNodes;
        for (var j = 0; j < added.length; j++) {
          var n = added[j];
          if (n.nodeType === 1) {
            if (document.getElementById("cctm-nav") !== n && !document.getElementById("cctm-nav")) {
              buildNav();
            }
            clamp(n);
            rebrand(n);
          }
        }
      }
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
